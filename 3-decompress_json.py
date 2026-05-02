import json
import os
from shared_utils import VALUES_JSON, KEYS_JSON, RESTORED_JSON

def decompress_from_two_files(values_path, keys_path, output_path):
    print(f"Восстанавливаем из {values_path} и {keys_path}...")
    if not os.path.exists(values_path) or not os.path.exists(keys_path):
        print("❌ Ошибка: Файлы для восстановления не найдены.")
        return
    
    # Читаем values_path с object_pairs_hook, чтобы сохранить дубликаты переводов!
    # Он вернет не словарь, а список пар [("Текст", "ID"), ("Текст", "ID2")]
    with open(values_path, 'r', encoding='utf-8') as f:
        values_pairs = json.load(f, object_pairs_hook=lambda pairs: pairs)
        
    with open(keys_path, 'r', encoding='utf-8') as f:
        id_to_keys = json.load(f)

    # Собираем словарь ID -> Текст, теперь ничего не потеряется
    id_to_value = {}
    for k, v in values_pairs:
        # Если v - это ID (формат "Текст": "ID")
        if isinstance(v, str) and v.isdigit():
            id_to_value[v] = k
        # На случай, если вы перевернули формат в ("ID": "Текст")
        elif isinstance(k, str) and k.isdigit():
            id_to_value[k] = v
        else:
            id_to_value[str(v)] = k

    decompressed_data = {}
    missing_ids = 0

    for id_val, keys in id_to_keys.items():
        if id_val in id_to_value:
            text_value = id_to_value[id_val]
            for key in keys:
                decompressed_data[key] = text_value
        else:
            print(f"  [!] Ошибка: ID '{id_val}' не найден в переводах!")
            missing_ids += 1

    if missing_ids == 0:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(decompressed_data, f, ensure_ascii=False, indent=4)
        print(f"🎉 Файл успешно восстановлен и сохранен в: {output_path}")
    else:
        print(f"❌ Восстановление прервано: не найдено {missing_ids} ID.")

if __name__ == "__main__":
    decompress_from_two_files(VALUES_JSON, KEYS_JSON, RESTORED_JSON)