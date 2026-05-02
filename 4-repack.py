import os
import json
import UnityPy
from shared_utils import (
    RESTORED_JSON, REPACK_IN_FOLDER, REPACK_OUT_FOLDER, 
    extract_text, save_text
)

def pack_translations():
    print(f"📦 Читаем переводы из {RESTORED_JSON}...")
    
    if not os.path.exists(RESTORED_JSON):
        print("❌ Ошибка: Файл с переводом не найден!")
        return

    with open(RESTORED_JSON, "r", encoding="utf-8") as f:
        translated_data = json.load(f)

    translations = {}
    valid_translations_count = 0
    
    for super_key, ru_text in translated_data.items():
        if not ru_text.strip():
            continue
        
        parts = super_key.split("|||")
        if len(parts) >= 3:
            rel_path, obj_id = parts[0], parts[1]
            text_key = "|||".join(parts[2:]) 
            
            if rel_path not in translations:
                translations[rel_path] = {}
            if obj_id not in translations[rel_path]:
                translations[rel_path][obj_id] = {}
                
            translations[rel_path][obj_id][text_key] = ru_text
            valid_translations_count += 1

    print(f"📊 Готовых переводов в памяти: {valid_translations_count}")
    print("\n🔄 Начинаем внедрение текста (LZ4)...")
    modified_files_count = 0

    for rel_path, file_data in translations.items():
        safe_rel_path = rel_path.replace("/", os.sep)
        original_file_path = os.path.join(REPACK_IN_FOLDER, safe_rel_path)
        output_file_path = os.path.join(REPACK_OUT_FOLDER, safe_rel_path)
        
        if not os.path.exists(original_file_path):
            continue

        try:
            env = UnityPy.load(original_file_path)
            is_modified = False
            replaced_strings = 0

            for obj in env.objects:
                obj_id_str = str(obj.path_id)
                if obj_id_str in file_data:
                    
                    # Магия импортирована из shared_utils!
                    raw_text, text_source, data, tree = extract_text(obj)

                    if raw_text:
                        new_lines = []
                        sample_key_in_file = None
                        
                        for line in raw_text.splitlines():
                            if ":" in line and not line.strip().startswith("//"):
                                k, v = line.split(":", 1)
                                if not sample_key_in_file:
                                    sample_key_in_file = k
                                    
                                if k in file_data[obj_id_str]:
                                    line = f"{k}:{file_data[obj_id_str][k]}"
                                    replaced_strings += 1
                                elif k.strip() in file_data[obj_id_str]:
                                    line = f"{k}:{file_data[obj_id_str][k.strip()]}"
                                    replaced_strings += 1
                            new_lines.append(line)

                        new_text = "\n".join(new_lines)

                        if replaced_strings > 0:
                            save_text(obj, new_text, text_source, data, tree)
                            is_modified = True
                        else:
                            expected_key = list(file_data[obj_id_str].keys())[0]
                            print(f"  [!] Ключи не совпали! Ожидался: '{expected_key}', Найден: '{sample_key_in_file}'")

            if replaced_strings > 0:
                print(f"  ✅ Файл: {rel_path} | Заменено строк: {replaced_strings}")

            if is_modified:
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                with open(output_file_path, "wb") as f:
                    f.write(env.file.save(packer="lz4"))
                modified_files_count += 1

        except Exception as e:
            print(f"  [!] Ошибка при запаковке {rel_path}: {e}")

    print(f"\n🎉 Все готово! Успешно перепаковано файлов: {modified_files_count}")

if __name__ == "__main__":
    pack_translations()