# Rein-Asset-Clunky-Toolkit

A small Python toolkit for extracting and repacking editable text from Unity AssetBundles.

It was built for a practical localization workflow where most text bundles can be handled by UnityPy, while some UI/help bundles need extra handling because their Unity metadata is a little cursed.

The toolkit does **not** provide, download, decrypt, or distribute any third-party assets. You must supply your own files.

---

## What this toolkit does

- Extracts supported Unity text objects into JSON files.
- Reinjects translated JSON values back into the original AssetBundles.
- Supports two repacking backends:
  - `original` for normal text bundles.
  - `help_unitypy_lz4_66` for the special Help/UI text bundles.
- Supports `TextAsset` and selected `MonoBehaviour` subtitle structures.
- Can extract credits text into a plain `.txt` file when enabled.

---

## Important limitations

This toolkit is intentionally narrow. It was built around a specific Unity AssetBundle layout and should be treated as a localization workbench, not a universal AssetBundle editor.

### Source language

The extraction/key-generation workflow is expected to use the **English source bundles** as the base source. Japanese (`ja`) and Korean (`ko`) bundles have structural differences that cause skipped strings, incomplete extraction, or `MonoBehaviour` parsing issues.

Recommended workflow:

```text
extract from English source -> translate JSON values -> repack into modified bundles
```

### Help/UI bundles

The Help/UI backend is pinned to:

```text
UnityPy==1.10.18
```

Do **not** upgrade UnityPy for the Help backend. UnityPy 1.25 can repack these bundles, but it corrupts the internal CAB/SerializedFile layout for this workflow.

The Help backend does **not** require patching UnityPy files in `site-packages`. It saves bundles through:

```python
env.file.save(packer=(66, 2))
```

This produces the required UnityFS profile:

```text
header_flags = 0x42
block flags  = 0x0002
```

### Known Help/UI read-only files

Some Help/UI bundles raise `String not terminated` when UnityPy tries to parse their TypeTree metadata. The toolkit can use a raw fallback to extract text from those bundles, but raw repacking is disabled by default because it can crash the game/runtime.

For shipping builds, keep:

```json
"allow_raw_fallback_repack": false
```

That means those problematic files are copied unchanged during repack. Their text may appear in extracted JSON, but changes will not be injected unless you explicitly enable raw fallback repacking, which is unsafe.

---

## Project structure

```text
Rein-Asset-Clunky-Toolkit/
├── main.py
├── requirements.txt
├── config-help.example.json
├── config-text.example.json
└── src/
    ├── __init__.py
    ├── credits.py
    ├── extractor.py
    ├── raw_help_textasset.py
    ├── repacker.py
    ├── translation_store.py
    ├── unitypy_help_runtime.py
    ├── unitypy_textasset_io.py
    ├── utils.py
    └── backends/
        ├── __init__.py
        ├── base.py
        ├── help_unitypy_lz4_66.py
        └── original_unitypy.py
```

---

## Installation

Python 3.11+ is recommended.

Install dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt` should pin UnityPy:

```text
UnityPy==1.10.18
lz4
```

The Help backend will refuse newer UnityPy versions because newer releases have been observed to produce invalid Help/UI bundle layouts for this workflow.

---

## Configuration files

The repository includes example configs:

```text
config-text.example.json
config-help.example.json
```

Copy one of them before use:

```bash
cp config-text.example.json config-text.json
cp config-help.example.json config-help.json
```

On PowerShell:

```powershell
Copy-Item config-text.example.json config-text.json
Copy-Item config-help.example.json config-help.json
```

---

## Normal text workflow

Use this for the regular text bundles.

Example config:

```json
{
    "input_dir": "0-decrypted",
    "output_dir": "1-repack",
    "miss_dir": "99-miss_folder",
    "target_language": "ru",
    "scan_path": "assetbundle/text/en",
    "need_credits": true,

    "packer_backend": "original",
    "normalize_newlines": "preserve",

    "keys_file": "0-en-keys.json",
    "source_values_file": "0-en-values.json",
    "translation_values_file": "0-ru-values.json",

    "use_live_filter": true,
    "extract_object_types": ["TextAsset", "MonoBehaviour"],
    "skip_image_keys": false,
    "load_from_bytes": false
}
```

If your extracted source tree includes `revisions/0`, use this instead:

```json
"scan_path": "revisions/0/assetbundle/text/en"
```

### Extract

```bash
python main.py --config config-text.json --extract
```

This generates files such as:

```text
0-en-keys.json
0-en-values.json
0-en-credit.txt
```

### Translate

Copy or rename the source values file into the target values file expected by your config, then translate only the JSON values.

Example:

```json
{
    "1": "Start",
    "2": "Options"
}
```

becomes:

```json
{
    "1": "Начать",
    "2": "Настройки"
}
```

Do not edit the generated key mapping file unless you are debugging the toolkit itself.

### Repack

```bash
python main.py --config config-text.json --repack
```

Modified files are written to the configured `output_dir`.

---

## Help/UI workflow

Use this for Help/UI bundles that need the special backend.

Example config:

```json
{
    "input_dir": "0-decrypted",
    "output_dir": "3-repacked-toolkit-help",
    "miss_dir": "99-miss_folder",
    "target_language": "ru",
    "scan_path": "assetbundle/ui/help/en",
    "need_credits": false,

    "packer_backend": "help_unitypy_lz4_66",
    "normalize_newlines": "literal",
    "force_save": true,
    "copy_unmodified_to_output": true,

    "keys_file": "help-en-keys.json",
    "source_values_file": "help-en-values.json",
    "translation_values_file": "help-ru-values.json",

    "unitypy_runtime": "help",
    "use_live_filter": false,
    "extract_object_types": ["TextAsset"],
    "skip_image_keys": true,
    "skip_file_name_parts": ["image"],
    "load_from_bytes": true,
    "allow_raw_fallback_repack": false
}
```

If your extracted source tree includes `revisions/0`, use this instead:

```json
"scan_path": "revisions/0/assetbundle/ui/help/en"
```

### Extract Help text

```bash
python main.py --config config-help.json --extract
```

For Help/UI, `normalize_newlines` should stay `literal`. This converts real newline characters in translations into literal `\\n`, which preserves the line-based `key:value` format used by these TextAssets.

### Repack Help text

```bash
python main.py --config config-help.json --repack
```

Expected stable behavior:

```text
repacked: many normal Help bundles
rewrapped_force: a small number of unchanged-but-rewrapped bundles
copied_ignored: image/font/audio/etc. files copied unchanged
copied_load_fail_kept_original: String-not-terminated bundles copied unchanged
```

The exact counts depend on your source tree.

---

## Generated files

The toolkit uses two JSON files for translation mapping.

### Keys file

Example:

```text
0-en-keys.json
help-en-keys.json
```

This is an internal mapping file. Do not translate it.

A mapping key looks like:

```text
some/path/file.assetbundle|||12345|||text.01
```

The `|||` delimiter is intentional.

### Values file

Example:

```text
0-ru-values.json
help-ru-values.json
```

This is the file you translate. Keep the numeric JSON keys unchanged and edit only the values.

---

## Credits handling

For normal text mode, credits can be extracted and repacked when:

```json
"need_credits": true
```

The toolkit reads/writes:

```text
0-en-credit.txt
0-ru-credit.txt
```

Do not remove technical tags in credits text, such as:

```text
<h3>
<type1>
```

---

## Backend notes

### `original`

Used for regular text bundles. It saves with:

```python
env.file.save(packer="original")
```

It supports `TextAsset` and selected `MonoBehaviour` subtitle arrays.

### `help_unitypy_lz4_66`

Used for Help/UI bundles. It:

- requires `UnityPy==1.10.18`;
- disables UnityPy native reader modules before import;
- monkey-patches UnityPy `ContainerHelper` to ignore broken `NodeHelper` / `UnknownObject` container entries;
- saves with `env.file.save(packer=(66, 2))`;
- does not patch UnityPy files on disk;
- uses raw fallback for extraction of some problematic bundles;
- keeps raw fallback repacking disabled by default.

---

## Safety notes

- Keep backups of your translation JSON files.
- Test small batches first.
- Do not upgrade UnityPy unless you are prepared to revalidate all outputs.
- Do not patch files inside `site-packages/UnityPy` for this toolkit.
- Keep `allow_raw_fallback_repack` disabled for shipping builds unless you are intentionally experimenting.

---

## Legal disclaimer

This project is an unofficial, fan-made, open-source tool created for educational, research, archival, and personal localization workflow purposes.

This project is not affiliated with, sponsored, endorsed, approved, or maintained by any game publisher, developer, platform holder, or rights owner.

All trademarks, product names, copyrighted works, and proprietary assets belong to their respective owners.

This repository does not contain, distribute, or provide access to any original game files, copyrighted assets, encryption keys, decrypted data, or proprietary resources.

Users are responsible for ensuring that they have the legal right to process any files used with this toolkit.

The authors do not condone piracy, copyright infringement, unauthorized redistribution, or any illegal use of copyrighted content.
