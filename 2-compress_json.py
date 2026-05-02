import json
import os
from shared_utils import ALL_JSON, VALUES_JSON, KEYS_JSON

def compress_to_two_files(input_path, values_path, keys_path):
    print(f"Читаем оригинальный файл: {input_path}")
    if not os.path.exists(input_path):
        print(f"❌ Ошибка: Файл '{input_path}' не найден. Сначала выполните извлечение.")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    value_to_id, id_to_keys = {}, {}
    current_id = 1

    for key, value in data.items():
        if value not in value_to_id:
            str_id = str(current_id)
            value_to_id[value] = str_id
            id_to_keys[str_id] = []
            current_id += 1
        else:
            str_id = value_to_id[value]
        
        id_to_keys[str_id].append(key)

    with open(values_path, 'w', encoding='utf-8') as f:
        json.dump(value_to_id, f, ensure_ascii=False, indent=4)

    with open(keys_path, 'w', encoding='utf-8') as f:
        f.write("{\n")
        items = list(id_to_keys.items())
        
        for i, (id_val, keys) in enumerate(items):
            id_str = json.dumps(id_val, ensure_ascii=False)
            keys_str = json.dumps(keys, ensure_ascii=False)
            comma = "," if i < len(items) - 1 else ""
            f.write(f"    {id_str}: {keys_str}{comma}\n")
            
        f.write("}")
    
    print(f"Файлы успешно созданы:\n - {values_path}\n - {keys_path}")

if __name__ == "__main__":
    compress_to_two_files(ALL_JSON, VALUES_JSON, KEYS_JSON)