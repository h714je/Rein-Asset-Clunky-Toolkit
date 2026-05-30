import shutil
from pathlib import Path
from typing import Any, Dict

import UnityPy

from .base import PackerBackend, PackContext, PackResult
from ..utils import extract_text, save_text


class OriginalUnityPyBackend(PackerBackend):
    name = "original"

    def pack_file(self, src: Path, semantic_path: str, store, ctx: PackContext) -> PackResult:
        objects_map = store.get_file_map(semantic_path)

        dst = ctx.output_dir / src.relative_to(ctx.input_dir)
        miss_dst = ctx.miss_dir / src.relative_to(ctx.input_dir)

        if not objects_map:
            return self._copy_unmodified(src, dst, miss_dst, semantic_path, ctx)

        try:
            env = UnityPy.load(str(src))
            file_modified = False
            replacements = 0

            for obj in env.objects:
                oid = str(obj.path_id)

                if oid not in objects_map:
                    continue

                if obj.type.name == "TextAsset":
                    if self._repack_text_asset(obj, objects_map[oid]):
                        file_modified = True
                        replacements += 1

                elif obj.type.name == "MonoBehaviour":
                    if self._repack_monobehaviour(obj, objects_map[oid]):
                        file_modified = True
                        replacements += 1

            if file_modified:
                dst.parent.mkdir(parents=True, exist_ok=True)
                with dst.open("wb") as f:
                    f.write(env.file.save(packer="original"))
                return PackResult("repacked", semantic_path, replacements)

            return self._copy_unmodified(src, dst, miss_dst, semantic_path, ctx)

        except Exception as e:
            return PackResult("repack_fail", semantic_path, 0, str(e))

    def _copy_unmodified(self, src: Path, dst: Path, miss_dst: Path, semantic_path: str, ctx: PackContext) -> PackResult:
        if ctx.copy_unmodified_to_output:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return PackResult("copied_no_change", semantic_path)

        miss_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, miss_dst)
        return PackResult("copied_to_miss", semantic_path)

    def _repack_text_asset(self, obj: Any, target_map: Dict[str, str]) -> bool:
        raw, src_type, data, tree = extract_text(obj)
        if not raw:
            return False

        lines = []
        is_modified = False

        for line in raw.splitlines():
            if ":" in line and not line.strip().startswith("//"):
                k, _ = line.split(":", 1)
                t_key = k if k in target_map else k.strip()
                if t_key in target_map:
                    line = f"{k}:{target_map[t_key]}"
                    is_modified = True

            lines.append(line)

        if is_modified:
            save_text(obj, "\n".join(lines), src_type, data, tree)
            return True

        return False

    def _repack_monobehaviour(self, obj: Any, target_map: Dict[str, str]) -> bool:
        if not hasattr(obj, "read_typetree"):
            return False

        try:
            tree = obj.read_typetree()
            array_key = (
                "DarkMoviesSubtitleArray"
                if "DarkMoviesSubtitleArray" in tree
                else "DarkMovieSubtitleArray"
                if "DarkMovieSubtitleArray" in tree
                else None
            )

            if not array_key:
                return False

            m_name = tree.get("m_Name", f"Mono_{obj.path_id}")
            local_modified = False

            for i, item in enumerate(tree[array_key]):
                key = f"{m_name}_Subtitle_{i}"

                if key not in target_map:
                    continue

                new_text = target_map[key]

                if "data" in item and "Text" in item["data"]:
                    item["data"]["Text"] = new_text
                    local_modified = True
                elif "Text" in item:
                    item["Text"] = new_text
                    local_modified = True

            if local_modified:
                obj.save_typetree(tree)
                return True

        except Exception:
            pass

        return False