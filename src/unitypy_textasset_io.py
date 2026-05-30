from __future__ import annotations

from typing import Any, Optional, Tuple

import UnityPy  # type: ignore


def type_name(obj: Any) -> str:
    try:
        return obj.type.name
    except Exception:
        return str(getattr(obj, "type", ""))


def read_textasset(obj: Any) -> Optional[Tuple[Any, str, str]]:
    data = obj.read()

    for attr in ("text", "script", "m_Script"):
        if not hasattr(data, attr):
            continue

        val = getattr(data, attr)

        if isinstance(val, bytes):
            return data, attr, val.decode("utf-8", "surrogateescape")

        if isinstance(val, str):
            return data, attr, val

    try:
        tree = obj.read_typetree()
        val = tree.get("m_Script") or tree.get("text")
        if isinstance(val, str):
            return tree, "__typetree_m_Script__", val
    except Exception:
        pass

    return None


def write_textasset(obj: Any, data_obj: Any, attr: str, new_text: str) -> None:
    if attr == "__typetree_m_Script__":
        data_obj["m_Script"] = new_text
        obj.save_typetree(data_obj)
        return

    old = getattr(data_obj, attr)

    if isinstance(old, bytes):
        setattr(data_obj, attr, new_text.encode("utf-8", "surrogateescape"))
    else:
        setattr(data_obj, attr, new_text)

    data_obj.save()


def load_env_from_bytes(path) -> Any:
    return UnityPy.load(path.read_bytes())


def save_env_lz4_66(env: Any) -> bytes:
    return env.file.save(packer=(66, 2))
