import json
from pathlib import Path
from typing import Dict, Any


class TranslationStore:
    def __init__(self) -> None:
        self.file_map: Dict[str, Dict[str, Dict[str, str]]] = {}

    @classmethod
    def from_legacy(
        cls,
        keys_path: Path,
        values_path: Path,
        newline_mode: str = "literal",
    ) -> "TranslationStore":
        store = cls()

        with values_path.open("r", encoding="utf-8") as f:
            v_data = json.load(f)

        with keys_path.open("r", encoding="utf-8") as f:
            id_to_keys = json.load(f)

        id_to_value = {str(k): v for k, v in v_data.items() if str(k).isdigit()}
        if not id_to_value:
            id_to_value = {str(v): k for k, v in v_data.items() if str(v).isdigit()}

        for sid, keys in id_to_keys.items():
            if sid not in id_to_value:
                continue

            text = normalize_translation_value(id_to_value[sid], newline_mode=newline_mode)

            for skey in keys:
                try:
                    path, oid, key = skey.split("|||", 2)
                except ValueError:
                    continue

                path = path.replace("\\", "/")
                store.file_map.setdefault(path, {}).setdefault(str(oid), {})[key] = text

        return store

    def get_file_map(self, semantic_path: str) -> Dict[str, Dict[str, str]]:
        return self.file_map.get(semantic_path.replace("\\", "/"), {})


def normalize_translation_value(value: Any, newline_mode: str = "literal") -> str:
    text = str(value)

    if newline_mode == "preserve":
        return text

    if newline_mode == "literal":
        return text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")

    if newline_mode == "lf":
        return text.replace("\r\n", "\n").replace("\r", "\n")

    raise ValueError(f"Unknown newline_mode: {newline_mode!r}. Use literal, preserve, or lf.")
