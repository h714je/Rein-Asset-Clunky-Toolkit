import json
from pathlib import Path
from typing import Any, Dict, Set
import UnityPy

from .utils import extract_text

def get_live_objects(env: UnityPy.Environment) -> Set[int]:
    live_ids: Set[int] = set()
    if hasattr(env, 'container'):
        for _, obj in env.container.items():
            live_ids.add(obj.path_id)
            
    for obj in env.objects:
        if obj.type.name == "AssetBundle":
            ab_data = obj.read()
            if hasattr(ab_data, 'm_PreloadTable'):
                for ptr in ab_data.m_PreloadTable:
                    live_ids.add(ptr.path_id)
        elif obj.type.name == "GameObject":
            go_data = obj.read()
            if hasattr(go_data, 'm_Components'):
                for comp in go_data.m_Components:
                    if hasattr(comp, 'path_id'):
                        live_ids.add(comp.path_id)
    return live_ids

def _extract_text_asset(obj: Any, semantic_path: str, value_to_id: Dict[str, str], id_to_keys: Dict[str, list], state: Dict[str, int]) -> None:
    raw_text, _, _, _ = extract_text(obj) 
    if not raw_text: 
        return
        
    for line in raw_text.splitlines():
        if ":" not in line or line.strip().startswith("//"): 
            continue
            
        key, text_val = line.split(":", 1)
        super_key = f"{semantic_path}|||{obj.path_id}|||{key}"
        
        if text_val not in value_to_id:
            sid = str(state["current_id"])
            value_to_id[text_val] = sid
            id_to_keys[sid] = []
            state["current_id"] += 1
        else: 
            sid = value_to_id[text_val]
            
        id_to_keys[sid].append(super_key)
        state["total_count"] += 1

def _extract_monobehaviour(obj: Any, semantic_path: str, value_to_id: Dict[str, str], id_to_keys: Dict[str, list], state: Dict[str, int]) -> None:
    if not hasattr(obj, 'read_typetree'):
        return
    try:
        tree = obj.read_typetree()
        array_key = "DarkMoviesSubtitleArray" if "DarkMoviesSubtitleArray" in tree else "DarkMovieSubtitleArray" if "DarkMovieSubtitleArray" in tree else None
        
        if array_key:
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
    input_dir = Path(config["input_dir"])
    scan_dir = input_dir / config["scan_path"]
    lang = config["target_language"]
    
    values_json = Path("0-en-values.json")
    keys_json = Path("0-en-keys.json")

    print(f"  [EXTRACT] Scanning directory: {scan_dir}")

    value_to_id: Dict[str, str] = {}
    id_to_keys: Dict[str, list] = {}
    state = {"current_id": 1, "total_count": 0}

    if not scan_dir.exists():
        print(f"  Error: Target scan folder does not exist: {scan_dir}")
        return

    for file_path in scan_dir.rglob("*"):
        if not file_path.is_file():
            continue
            
        # Пропускаем титры, так как ими занимается отдельный модуль
        if file_path.name == "credit.assetbundle":
            continue
            
        semantic_path = file_path.relative_to(scan_dir).as_posix()

        try:
            env = UnityPy.load(str(file_path))
        except Exception as e:
            print(f"  [!] Failed to load file {semantic_path}: {e}")
            continue
            
        live_ids = get_live_objects(env)
        strict_mode = len(live_ids) > 0 
        
        for obj in env.objects:
            if strict_mode and obj.path_id not in live_ids:
                continue 

            if obj.type.name == "TextAsset":
                _extract_text_asset(obj, semantic_path, value_to_id, id_to_keys, state)
            elif obj.type.name == "MonoBehaviour":
                _extract_monobehaviour(obj, semantic_path, value_to_id, id_to_keys, state)

    export_values = {v: k for k, v in value_to_id.items()}
    
    with open(values_json, 'w', encoding='utf-8') as f:
        json.dump(export_values, f, ensure_ascii=False, indent=4)
    with open(keys_json, 'w', encoding='utf-8') as f:
        json.dump(id_to_keys, f, ensure_ascii=False, indent=4)
        
    print(f"  Success! Unique strings parsed: {len(export_values)} (Total mapping keys: {state['total_count']})")