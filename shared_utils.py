import os

# === НАСТРОЙКИ ПУТЕЙ ===
EXTRACT_IN_FOLDER = os.path.join("0-decrypted", "assetbundle", "text", "en")
REPACK_IN_FOLDER = "0-decrypted"
REPACK_OUT_FOLDER = "0-repacked"

ALL_JSON = "zz-all.json"
VALUES_JSON = "zzz-values.json"
KEYS_JSON = "zzz-keys.json"
RESTORED_JSON = "zzz-restored.json"

# === ОБЩАЯ ЛОГИКА UNITYPY ===
def extract_text(obj):
    """Извлекает текст из объекта UnityPy 3 разными способами."""
    data = obj.read()
    raw_text = ""
    text_source = None
    tree = None
    
    if hasattr(data, "text") and data.text:
        raw_text = data.text
        text_source = "text"
    elif hasattr(data, "script") and data.script:
        if isinstance(data.script, bytes):
            raw_text = data.script.decode('utf-8', errors='ignore')
        else:
            raw_text = str(data.script)
        text_source = "script"
    else:
        tree = obj.read_typetree()
        raw_text = tree.get("m_Script", "")
        text_source = "typetree"
        
    return raw_text, text_source, data, tree

def save_text(obj, new_text, text_source, data, tree):
    """Сохраняет измененный текст обратно в объект нужным методом."""
    if text_source == "text":
        data.text = new_text
        data.save()
    elif text_source == "script":
        if isinstance(data.script, bytes):
            data.script = new_text.encode('utf-8')
        else:
            data.script = new_text
        data.save()
    elif text_source == "typetree":
        tree["m_Script"] = new_text
        obj.save_typetree(tree)