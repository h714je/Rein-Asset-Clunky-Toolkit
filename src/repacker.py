from pathlib import Path

from .translation_store import TranslationStore
from .backends import BACKENDS
from .backends.base import PackContext


def _make_pack_context(config: dict, input_dir: Path, output_dir: Path, miss_dir: Path, scan_path: str) -> PackContext:
    """Create PackContext with compatibility for older/newer base.py."""
    kwargs = dict(
        input_dir=input_dir,
        output_dir=output_dir,
        miss_dir=miss_dir,
        scan_path=scan_path,
        copy_unmodified_to_output=bool(config.get("copy_unmodified_to_output", False)),
        force_save=bool(config.get("force_save", False)),
    )

    # New field used by Help backend. If user's base.py is older, fall back safely.
    try:
        return PackContext(
            **kwargs,
            allow_raw_fallback_repack=bool(config.get("allow_raw_fallback_repack", False)),
        )
    except TypeError:
        ctx = PackContext(**kwargs)
        setattr(ctx, "allow_raw_fallback_repack", bool(config.get("allow_raw_fallback_repack", False)))
        return ctx


def step_repack(config: dict) -> None:
    input_dir = Path(config["input_dir"])
    output_dir = Path(config["output_dir"])
    miss_dir = Path(config["miss_dir"])
    scan_path = config["scan_path"]
    scan_dir = input_dir / scan_path
    lang = config["target_language"]

    tr_values_json = Path(config.get("translation_values_file", f"0-{lang}-values.json"))
    keys_json = Path(config.get("keys_file", "0-en-keys.json"))

    if not tr_values_json.exists() or not keys_json.exists():
        print("  Repack canceled: Translation map files or Key configurations are missing.")
        print(f"  keys: {keys_json}")
        print(f"  values: {tr_values_json}")
        return

    backend_name = config.get("packer_backend", "original")
    backend_cls = BACKENDS.get(backend_name)

    if backend_cls is None:
        print(f"  [!] Unknown packer_backend: {backend_name}")
        print(f"      Available: {', '.join(sorted(BACKENDS.keys()))}")
        return

    backend = backend_cls()
    backend.prepare()

    normalize_mode = config.get("normalize_newlines")
    if normalize_mode is None:
        normalize_mode = "literal" if backend_name == "help_unitypy_lz4_66" else "preserve"

    store = TranslationStore.from_legacy(
        keys_json,
        tr_values_json,
        newline_mode=normalize_mode,
    )

    ctx = _make_pack_context(config, input_dir, output_dir, miss_dir, scan_path)

    if not scan_dir.exists():
        print(f"  Error: Target scan folder does not exist: {scan_dir}")
        return

    stats = {}
    replacements = 0

    for file_path in scan_dir.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.name == "credit.assetbundle":
            continue

        semantic_path = file_path.relative_to(scan_dir).as_posix()

        result = backend.pack_file(
            src=file_path,
            semantic_path=semantic_path,
            store=store,
            ctx=ctx,
        )

        stats[result.status] = stats.get(result.status, 0) + 1
        replacements += result.replacements

        print(f"  [{result.status}] {semantic_path} repl={result.replacements}")

        if result.error:
            print(f"      {result.error}")

    print("  Repack Summary Complete")
    print(f"  Backend: {backend.name}")
    print(f"  Replacements: {replacements}")

    for status in sorted(stats):
        print(f"  {status}: {stats[status]}")
