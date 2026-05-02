import os
import json
import UnityPy
from shared_utils import EXTRACT_IN_FOLDER, ALL_JSON, extract_text

def extract_to_json():
    print(f"🔍 Сканируем папку: {EXTRACT_IN_FOLDER}...")
    if not os.path.exists(EXTRACT_IN_FOLDER):
        print("❌ Ошибка: Папка не найдена!")
        return

    extracted_data = {}
    extracted_count = 0

    for root, dirs, files in os.walk(EXTRACT_IN_FOLDER):
        for filename in files:
            file_path = os.path.join(root, filename)
            # Надежное построение относительного пути
            rel_path = os.path.relpath(file_path, "0-decrypted").replace("\\", "/")

            try:
                env = UnityPy.load(file_path)
                if not env.objects: continue

                for obj in env.objects:
                    if obj.type.name == "TextAsset":
                        raw_text, _, _, _ = extract_text(obj)
                        
                        if raw_text:
                            for line in raw_text.splitlines():
                                if not line.strip() or line.startswith("//"):
                                    continue
                                
                                if ":" in line:
                                    key, text_val = line.split(":", 1)
                                    super_key = f"{rel_path}|||{obj.path_id}|||{key}"
                                    extracted_data[super_key] = text_val
                                    extracted_count += 1
                                    
            except Exception as e:
                print(f"  [!] Ошибка с файлом {filename}: {e}")

    with open(ALL_JSON, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)

    print(f"\n🎉 Готово! Извлечено строк: {extracted_count}")
    print(f"Файл сохранен как {ALL_JSON}")

if __name__ == "__main__":
    extract_to_json()