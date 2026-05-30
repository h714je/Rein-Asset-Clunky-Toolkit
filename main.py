import json
import argparse
import sys
from pathlib import Path


def load_config(path: str) -> dict:
    config_path = Path(path)

    try:
        with config_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Ошибка: файл конфига не найден: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка JSON в конфиге {config_path}: {e}")
        sys.exit(1)


def pre_bootstrap_unitypy(config: dict) -> None:
    """Run before importing modules that import UnityPy.

    Help bundles need Python-side readers so the safe string-reader patch can work.
    If UnityPy native extensions are imported first, the later monkey-patch may not
    catch the `String not terminated` cases.
    """
    if config.get("unitypy_runtime") != "help":
        return

    for name in (
        "UnityPyExt",
        "UnityPy.UnityPyExt",
        "UnityPy.EndianBinaryReader",
        "UnityPy.EndianBinaryWriter",
    ):
        sys.modules[name] = None

    print("  [BOOT] Help UnityPy native extensions disabled before UnityPy import")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unity Localization Extract & Repack Script Framework")
    parser.add_argument("--config", default="config.json", help="Путь к config.json")
    parser.add_argument("--extract", action="store_true", help="Извлечь текст в JSON")
    parser.add_argument("--repack", action="store_true", help="Запаковать переведенный текст обратно")
    args = parser.parse_args()

    if not args.extract and not args.repack:
        parser.print_help()
        sys.exit(0)

    config = load_config(args.config)
    pre_bootstrap_unitypy(config)

    # Import only after config/runtime bootstrap. Some src modules import UnityPy at
    # module import time, so top-level imports would make Help patches too late.
    from src import extractor, repacker, credits

    if args.extract:
        extractor.step_extract(config)
        credits.extract_credits(config)

    if args.repack:
        repacker.step_repack(config)
        credits.repack_credits(config)
