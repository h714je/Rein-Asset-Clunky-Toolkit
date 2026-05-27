from typing import Any, Tuple, Optional

def extract_text(obj: Any) -> Tuple[str, Optional[str], Any, Any]:
    data = obj.read()
    raw_text = ""
    text_source = None
    tree = None
    
    if hasattr(data, "text") and data.text:
        raw_text = data.text
        text_source = "text"
    elif hasattr(data, "script") and data.script:
        if isinstance(data.script, bytes):
            if b'\x00' in data.script:
                return "", None, data, tree
            raw_text = data.script.decode('utf-8', errors='ignore')
        else:
            raw_text = str(data.script)
        
        if raw_text:
            text_source = "script"
    else:
        try:
            tree = obj.read_typetree()
            m_script = tree.get("m_Script", "")
            
            if isinstance(m_script, bytes):
                if b'\x00' in m_script:
                    return "", None, data, tree
                raw_text = m_script.decode('utf-8', errors='ignore')
            else:
                raw_text = str(m_script)
                
            if raw_text:
                text_source = "typetree"
        except Exception:
            pass
            
    return raw_text, text_source, data, tree

def save_text(obj: Any, new_text: str, text_source: str, data: Any, tree: Any) -> None:
    if text_source == "text":
        data.text = new_text
        data.save()
    elif text_source == "script":
        data.script = new_text.encode('utf-8') if isinstance(data.script, bytes) else new_text
        data.save()
    elif text_source == "typetree" and tree is not None:
        tree["m_Script"] = new_text
        obj.save_typetree(tree)