from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Tuple

from .base import PackerBackend, PackContext, PackResult
from ..unitypy_help_runtime import prepare_help_unitypy_runtime
from ..raw_help_textasset import patch_bundle_raw_textassets
from ..unitypy_textasset_io import (
    load_env_from_bytes,
    read_textasset,
    save_env_lz4_66,
    type_name,
    write_textasset,
)

IGNORE_NAME_PARTS = ("image", "_img", "bg_", "icon", "texture", "audio", "sound", "font")


class HelpUnityPyLz466Backend(PackerBackend):
    name = "help_unitypy_lz4_66"

    def prepare(self) -> None:
        prepare_help_unitypy_runtime()

    def pack_file(self, src: Path, semantic_path: str, store: Any, ctx: PackContext) -> PackResult:
        dst = ctx.output_dir / src.relative_to(ctx.input_dir)
        full_rel_path = src.relative_to(ctx.input_dir).as_posix()

        if self._is_ignored(src):
            self._copy(src, dst)
            return PackResult("copied_ignored", full_rel_path)

        try:
            env = load_env_from_bytes(src)
        except Exception as exc:
            # The 7 cursed UI/Help bundles can be read/patched by the raw fallback,
            # but the game crashes on those raw-repacked files. Keep raw fallback
            # disabled for shipping builds unless explicitly enabled in config.
            if getattr(ctx, "allow_raw_fallback_repack", False):
                raw_result = self._try_raw_fallback(src, semantic_path, full_rel_path, store, ctx, dst, str(exc))
                if raw_result is not None:
                    return raw_result

            self._copy(src, dst)
            return PackResult("copied_load_fail_kept_original", full_rel_path, 0, str(exc))

        touched = False
        replacements = 0

        for obj in getattr(env, "objects", []):
            try:
                if type_name(obj) != "TextAsset":
                    continue

                oid = str(getattr(obj, "path_id", ""))
                object_map = self._get_object_map(store, semantic_path, full_rel_path, oid)

                if not object_map:
                    continue

                got = read_textasset(obj)
                if got is None:
                    continue

                data_obj, attr, raw = got
                new_text, n = self._patch_help_text(raw, object_map)

                if n and new_text != raw:
                    write_textasset(obj, data_obj, attr, new_text)
                    replacements += n
                    touched = True

            except Exception:
                continue

        if not touched and not ctx.force_save:
            self._copy(src, dst)
            return PackResult("copied_no_change", full_rel_path)

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(save_env_lz4_66(env))
            status = "repacked" if touched else "rewrapped_force"
            return PackResult(status, full_rel_path, replacements)
        except Exception as exc:
            self._copy(src, dst)
            return PackResult("copied_save_fail", full_rel_path, replacements, str(exc))

    def _get_file_map_variants(self, store: Any, semantic_path: str, full_rel_path: str) -> Dict[str, Dict[str, str]]:
        for path in (semantic_path, full_rel_path):
            file_map = store.file_map.get(path.replace("\\", "/"), {})
            if file_map:
                return file_map
        return {}

    def _try_raw_fallback(
        self,
        src: Path,
        semantic_path: str,
        full_rel_path: str,
        store: Any,
        ctx: PackContext,
        dst: Path,
        original_error: str,
    ) -> PackResult | None:
        file_map = self._get_file_map_variants(store, semantic_path, full_rel_path)
        if not file_map:
            return None
        try:
            out_bytes, replacements = patch_bundle_raw_textassets(src, file_map)
            if replacements <= 0:
                return None
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(out_bytes)
            # Raw fallback succeeded. Do not propagate the UnityPy load error
            # into PackResult.error, otherwise the logger prints a scary
            # "String not terminated" line under a successful status.
            return PackResult("repacked_raw_fallback", full_rel_path, replacements)
        except Exception as raw_exc:
            return PackResult(
                "copied_raw_fallback_fail",
                full_rel_path,
                0,
                f"load={original_error}; raw_fallback={raw_exc}",
            )


    def _get_object_map(self, store: Any, semantic_path: str, full_rel_path: str, oid: str) -> Dict[str, str]:
        # Supports two key formats:
        # 1. category_01/item_01/page_01.assetbundle
        # 2. revisions/0/assetbundle/ui/help/en/category_01/item_01/page_01.assetbundle
        for path in (semantic_path, full_rel_path):
            file_map = store.file_map.get(path.replace("\\", "/"), {})
            obj_map = file_map.get(str(oid), {})
            if obj_map:
                return obj_map

        return {}

    def _patch_help_text(self, raw: str, object_map: Dict[str, str]) -> Tuple[str, int]:
        lines = raw.split("\n")
        out = []
        changed = 0

        for line in lines:
            if ":" not in line or line.strip().startswith("//"):
                out.append(line)
                continue

            key, value = line.split(":", 1)

            if "image_" in key.lower() or "image." in key.lower():
                out.append(line)
                continue

            end = "\r" if value.endswith("\r") else ""

            translated = None
            if key in object_map:
                translated = object_map[key]
            elif key.strip() in object_map:
                translated = object_map[key.strip()]

            if translated is None:
                out.append(line)
                continue

            out.append(f"{key}:{translated}{end}")
            changed += 1

        return "\n".join(out), changed

    def _is_ignored(self, path: Path) -> bool:
        name = path.name.lower()
        if not name.endswith(".assetbundle"):
            return True
        return any(part in name for part in IGNORE_NAME_PARTS)

    def _copy(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)