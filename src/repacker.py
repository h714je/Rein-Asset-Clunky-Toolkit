import json
import shutil
from pathlib import Path
from typing import Any, Dict
import UnityPy

from .utils import extract_text, save_text

def _repack_text_asset(obj: Any, target_map: Dict[str, str]) -> bool:
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

def _repack_monobehaviour(obj: Any, target_map: Dict[str, str]) -> bool:
    if not hasattr(obj, 'read_typetree'):
        return False
    try:
        tree = obj.read_typetree()
        array_key = "DarkMoviesSubtitleArray" if "DarkMoviesSubtitleArray" in tree else "DarkMovieSubtitleArray" if "DarkMovieSubtitleArray" in tree else None
        
        if array_key:
            m_name = tree.get("m_Name", f"Mono_{obj.path_id}")
            local_modified = False
            
            for i, item in enumerate(tree[array_key]):
                key = f"{m_name}_Subtitle_{i}"
                if key in target_map:
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

def step_repack(config: dict) -> None:
    input_dir = Path(config["input_dir"])
    output_dir = Path(config["output_dir"])
    miss_dir = Path(config["miss_dir"])
    scan_dir = input_dir / config["scan_path"]
    lang = config["target_language"]
    
    tr_values_json = Path(f"0-{lang}-values.json")
    keys_json = Path("0-en-keys.json")

    if not tr_values_json.exists() or not keys_json.exists(): 
        print("  Repack canceled: Translation map files or Key configurations are missing.")
        return

    with open(tr_values_json, 'r', encoding='utf-8') as f: 
        v_data = json.load(f)
    with open(keys_json, 'r', encoding='utf-8') as f: 
        id_to_keys = json.load(f)

    id_to_value = {str(k): v for k, v in v_data.items() if str(k).isdigit()}
    if not id_to_value:
        id_to_value = {str(v): k for k, v in v_data.items() if str(v).isdigit()}

    file_map: Dict[str, Dict[str, Dict[str, str]]] = {}
    for sid, keys in id_to_keys.items():
        if sid in id_to_value:
            text = id_to_value[sid]
            for skey in keys:
                path, oid, k = skey.split("|||", 2)
                file_map.setdefault(path, {}).setdefault(oid, {})[k] = text

    count_mod = 0
    count_copy = 0

    if not scan_dir.exists():
        print(f"  Error: Target scan folder does not exist: {scan_dir}")
        return

    for file_path in scan_dir.rglob("*"):
        if not file_path.is_file():
            continue
            
        # Пропускаем титры, так как ими занимается отдельный модуль
        if file_path.name == "credit.assetbundle":
            continue

        dst = output_dir / file_path.relative_to(input_dir)
        miss_dst = miss_dir / file_path.relative_to(input_dir)
        semantic_path = file_path.relative_to(scan_dir).as_posix()

        if semantic_path in file_map:
            objects_map = file_map[semantic_path]
            try:
                env = UnityPy.load(str(file_path))
                file_modified = False
                
                for obj in env.objects:
                    oid = str(obj.path_id)
                    if oid in objects_map:
                        if obj.type.name == "TextAsset":
                            if _repack_text_asset(obj, objects_map[oid]):
                                file_modified = True
                        elif obj.type.name == "MonoBehaviour":
                            if _repack_monobehaviour(obj, objects_map[oid]):
                                file_modified = True

                if file_modified:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with open(dst, "wb") as f:
                        f.write(env.file.save(packer="original"))
                    count_mod += 1
                else:
                    miss_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, miss_dst)
                    count_copy += 1
                    
            except Exception as e:
                print(f"  [!] Repack engine failed processing for {semantic_path}: {e}")
        else:
            miss_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, miss_dst)
            count_copy += 1

    print(f"  Repack Summary Complete -> Patched Assets: {count_mod} | Unchanged/Copied to Fallback: {count_copy}")

