import json
import argparse
import sys
# Добавили credits в импорт
from src import extractor, repacker, credits

def load_config() -> dict:
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Ошибка: Файл config.json не найден. Создайте его рядом с main.py.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unity Localization Extract & Repack Script Framework")
    parser.add_argument('--extract', action='store_true', help="Извлечь текст в JSON")
    parser.add_argument('--repack', action='store_true', help="Запаковать переведенный текст обратно")
    args = parser.parse_args()

    if not args.extract and not args.repack:
        parser.print_help()
        sys.exit(0)

    config = load_config()

    if args.extract: 
        extractor.step_extract(config)
        credits.extract_credits(config) # <--- Запуск модуля титров
    if args.repack: 
        repacker.step_repack(config)
        credits.repack_credits(config)  # <--- Запуск модуля титров