import json
from pathlib import Path
from typing import Any, Dict, Set
import UnityPy

from .utils import extract_text
from .raw_help_textasset import extract_textassets_from_bundle


def get_live_objects(env: UnityPy.Environment) -> Set[int]:
    live_ids: Set[int] = set()

    if hasattr(env, "container"):
        for _, obj in env.container.items():
            live_ids.add(obj.path_id)

    for obj in env.objects:
        if obj.type.name == "AssetBundle":
            ab_data = obj.read()
            if hasattr(ab_data, "m_PreloadTable"):
                for ptr in ab_data.m_PreloadTable:
                    live_ids.add(ptr.path_id)

        elif obj.type.name == "GameObject":
            go_data = obj.read()
            if hasattr(go_data, "m_Components"):
                for comp in go_data.m_Components:
                    if hasattr(comp, "path_id"):
                        live_ids.add(comp.path_id)

    return live_ids


def _maybe_prepare_unitypy_runtime(config: dict) -> None:
    if config.get("unitypy_runtime") == "help":
        try:
            from .unitypy_help_runtime import prepare_help_unitypy_runtime
            prepare_help_unitypy_runtime()
        except Exception as e:
            print(f"  [WARN] Help UnityPy runtime patch failed during extract: {e}")


def _add_line_value(
    semantic_path: str,
    path_id: Any,
    key: str,
    text_val: str,
    value_to_id: Dict[str, str],
    id_to_keys: Dict[str, list],
    state: Dict[str, int],
) -> None:
    super_key = f"{semantic_path}|||{path_id}|||{key}"

    if text_val not in value_to_id:
        sid = str(state["current_id"])
        value_to_id[text_val] = sid
        id_to_keys[sid] = []
        state["current_id"] += 1
    else:
        sid = value_to_id[text_val]

    id_to_keys[sid].append(super_key)
    state["total_count"] += 1


def _extract_help_lines_from_text(
    raw_text: str,
    semantic_path: str,
    path_id: Any,
    value_to_id: Dict[str, str],
    id_to_keys: Dict[str, list],
    state: Dict[str, int],
    skip_image_keys: bool = False,
) -> None:
    if not raw_text:
        return

    for line in raw_text.splitlines():
        if ":" not in line or line.strip().startswith("//"):
            continue

        key, text_val = line.split(":", 1)

        if skip_image_keys:
            lk = key.lower()
            if "image_" in lk or "image." in lk:
                continue

        _add_line_value(semantic_path, path_id, key, text_val, value_to_id, id_to_keys, state)


def _try_raw_help_extract(
    file_path: Path,
    semantic_path: str,
    value_to_id: Dict[str, str],
    id_to_keys: Dict[str, list],
    state: Dict[str, int],
    skip_image_keys: bool,
) -> bool:
    try:
        records = extract_textassets_from_bundle(file_path)
        if not records:
            return False
        for rec in records:
            _extract_help_lines_from_text(
                rec.text,
                semantic_path,
                rec.path_id,
                value_to_id,
                id_to_keys,
                state,
                skip_image_keys=skip_image_keys,
            )
        print(f"  [RAW-FALLBACK] Extracted TextAsset from: {semantic_path}")
        return True
    except Exception as e:
        print(f"  [RAW-FALLBACK-FAIL] {semantic_path}: {e}")
        return False


def _extract_text_asset(
    obj: Any,
    semantic_path: str,
    value_to_id: Dict[str, str],
    id_to_keys: Dict[str, list],
    state: Dict[str, int],
    skip_image_keys: bool = False,
) -> None:
    raw_text, _, _, _ = extract_text(obj)
    _extract_help_lines_from_text(
        raw_text,
        semantic_path,
        obj.path_id,
        value_to_id,
        id_to_keys,
        state,
        skip_image_keys=skip_image_keys,
    )


def _extract_monobehaviour(
    obj: Any,
    semantic_path: str,
    value_to_id: Dict[str, str],
    id_to_keys: Dict[str, list],
    state: Dict[str, int],
) -> None:
    if not hasattr(obj, "read_typetree"):
        return

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
            return

        m_name = tree.get("m_Name", f"Mono_{obj.path_id}")

        for i, item in enumerate(tree[array_key]):
            text_val = item.get("data", {}).get("Text") or item.get("Text")

            if isinstance(text_val, str) and text_val.strip():
                super_key = f"{semantic_path}|||{obj.path_id}|||{m_name}_Subtitle_{i}"

                if text_val not in value_to_id:
                    sid = str(state["current_id"])
                    value_to_id[text_val] = sid
                    id_to_keys[sid] = []
                    state["current_id"] += 1
                else:
                    sid = value_to_id[text_val]

                id_to_keys[sid].append(super_key)
                state["total_count"] += 1

    except Exception:
        pass


def step_extract(config: dict) -> None:
    _maybe_prepare_unitypy_runtime(config)

    input_dir = Path(config["input_dir"])
    scan_dir = input_dir / config["scan_path"]

    values_json = Path(config.get("source_values_file", "0-en-values.json"))
    keys_json = Path(config.get("keys_file", "0-en-keys.json"))

    use_live_filter = bool(config.get("use_live_filter", True))
    extract_types = set(config.get("extract_object_types", ["TextAsset", "MonoBehaviour"]))
    skip_image_keys = bool(config.get("skip_image_keys", False))
    load_from_bytes = bool(config.get("load_from_bytes", False))

    print(f"  [EXTRACT] Scanning directory: {scan_dir}")
    print(f"  [EXTRACT] keys: {keys_json}")
    print(f"  [EXTRACT] values: {values_json}")

    value_to_id: Dict[str, str] = {}
    id_to_keys: Dict[str, list] = {}
    state = {"current_id": 1, "total_count": 0}

    if not scan_dir.exists():
        print(f"  Error: Target scan folder does not exist: {scan_dir}")
        return

    skip_file_name_parts = [
        str(x).lower()
        for x in config.get("skip_file_name_parts", [])
    ]

    for file_path in scan_dir.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.name == "credit.assetbundle":
            continue

        lower_name = file_path.name.lower()
        if any(part in lower_name for part in skip_file_name_parts):
            continue

        semantic_path = file_path.relative_to(scan_dir).as_posix()

        try:
            env = UnityPy.load(file_path.read_bytes()) if load_from_bytes else UnityPy.load(str(file_path))
        except Exception as e:
            if config.get("unitypy_runtime") == "help":
                if _try_raw_help_extract(
                    file_path,
                    semantic_path,
                    value_to_id,
                    id_to_keys,
                    state,
                    skip_image_keys,
                ):
                    continue
            print(f"  [!] Failed to load file {semantic_path}: {e}")
            continue

        live_ids = get_live_objects(env) if use_live_filter else set()
        strict_mode = use_live_filter and len(live_ids) > 0

        for obj in env.objects:
            if strict_mode and obj.path_id not in live_ids:
                continue

            if obj.type.name == "TextAsset" and "TextAsset" in extract_types:
                _extract_text_asset(
                    obj,
                    semantic_path,
                    value_to_id,
                    id_to_keys,
                    state,
                    skip_image_keys=skip_image_keys,
                )

            elif obj.type.name == "MonoBehaviour" and "MonoBehaviour" in extract_types:
                _extract_monobehaviour(obj, semantic_path, value_to_id, id_to_keys, state)

    export_values = {v: k for k, v in value_to_id.items()}

    with values_json.open("w", encoding="utf-8") as f:
        json.dump(export_values, f, ensure_ascii=False, indent=4)

    with keys_json.open("w", encoding="utf-8") as f:
        json.dump(id_to_keys, f, ensure_ascii=False, indent=4)

    print(f"  Success! Unique strings parsed: {len(export_values)} (Total mapping keys: {state['total_count']})")
