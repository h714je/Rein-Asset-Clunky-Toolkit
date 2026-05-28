# Rein-Asset-Clunky-Toolkit

A straightforward and slightly rough-around-the-edges set of Python scripts for extracting and repacking text assets from Unity AssetBundles.

The toolkit is designed for personal localization workflows, research, archival work, and experiments with user-provided Unity files. It focuses on making extracted text easier to edit by converting supported Unity objects into JSON and plain text files.

> This tool does not provide, download, decrypt, or distribute any third-party assets.

---

## ⚠️ Important Limitation

This tool was built for a very specific localization workflow and has its quirks, hence the name.

Currently, the parsing logic and generated key structure only work reliably with the **English localization files**.

The toolkit expects the source bundles to be located at:

```text
revisions/0/assetbundle/text/en
```

Attempting to extract Japanese (`ja`) or Korean (`ko`) assets may result in `MonoBehaviour` parsing errors, skipped strings, or incomplete extraction because of structural differences.

If you plan to translate into another language, use the English localization bundles as the base source.

---

## 📂 Project Structure

```text
Rein-Asset-Clunky-Toolkit/
├── config.json             # Paths and language settings
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
└── src/                    # Source code logic
    ├── extractor.py
    ├── repacker.py
    ├── credits.py
    └── utils.py
```

---

## 📁 Working Directories

These directories can be created manually, or they will be generated automatically when needed.

```text
0-decrypted/
```

Place your own user-provided, already accessible Unity AssetBundle files here.

```text
1-repack/
```

Repacked files with injected translations will be written here.

```text
99-miss_folder/
```

Files that did not contain supported editable text will be copied here for review, so they are not silently ignored.

---

## 🚀 Installation

### Requirements

- Python 3.11 or newer is recommended
- pip
- UnityPy

### Setup

Clone or download this repository, then open a terminal inside the project folder.

Install dependencies:

```bash
pip install -r requirements.txt
```

The dependency list is intentionally small. At the moment, the toolkit mainly relies on:

```text
UnityPy
```

---

## ⚙️ Configuration

Before using the toolkit, open:

```text
config.json
```

Example configuration:

```json
{
    "input_dir": "0-decrypted",
    "output_dir": "1-repack",
    "miss_dir": "99-miss_folder",
    "target_language": "ru",
    "scan_path": "revisions/0/assetbundle/text/en",
    "need_credits": true
}
```

### Options

#### `input_dir`

Directory containing the source Unity AssetBundle files.

Default:

```text
0-decrypted
```

#### `output_dir`

Directory where repacked files will be written.

Default:

```text
1-repack
```

#### `miss_dir`

Directory where files without supported editable text will be copied.

Default:

```text
99-miss_folder
```

#### `target_language`

The language code you are translating into.

Examples:

```text
ru
es
fr
de
it
```

This value controls the names of the generated translation files.

For example, with:

```json
"target_language": "ru"
```

the toolkit will generate:

```text
0-en-values.json
0-en-keys.json
0-en-credit.txt
```

#### `scan_path`

Internal path to the source localization bundles.

Default:

```text
revisions/0/assetbundle/text/en
```

Do not change this unless you know exactly how your source files are structured.

#### `need_credits`

Controls whether the toolkit should process the credits file.

```json
"need_credits": true
```

Set to `true` to extract and repack credits.

```json
"need_credits": false
```

Set to `false` to skip credits processing.

---

## 📝 How to Use

---

## Step 1: Prepare Source Files

Place your source Unity AssetBundle files into:

```text
0-decrypted/
```

Preserve the original folder structure expected by the config.

Example:

```text
0-decrypted/revisions/0/assetbundle/text/en/...
```

The toolkit does not download, decrypt, or provide these files.  
You must supply your own files and make sure you have the right to use them.

---

## Step 2: Extract Text

Run:

```bash
python main.py --extract
```

The toolkit will scan the configured source path and generate translation files in the project root.

For example, if `target_language` is set to `ru`, the generated files will be:

```text
0-ru-values.json
```

If credits processing is enabled, this file will also be generated:

```text
0-ru-credit.txt
```

### Generated Files

#### `0-ru-values.json`

This is the main translation file.

Edit this file.

#### `0-ru-keys.json`

This is a technical mapping file used during repacking.

Do not edit this file manually.

#### `0-ru-credit.txt`

This is a plain text credits file.

Edit this file only if credits extraction is enabled.

---

## Step 3: Translate

Open:

```text
0-ru-values.json
```

Translate only the values.

Example:

```json
{
    "1": "Start",
    "2": "Options"
}
```

The keys must stay unchanged.

Good:

```json
{
    "1": "Начать"
}
```

The JSON format works well with translation platforms such as:

- Crowdin
- Weblate
- Tolgee
- Lokalise
- POEditor

---

## Step 4: Translate Credits

If credits processing is enabled, edit:

```text
0-ru-credit.txt
```

You can use any standard text editor.

Do not remove technical tags such as:

```text
<h3>
<type1>
```

These tags are required for rebuilding the credits structure.

---

## Step 5: Repack

Make sure the translated files are located in the project root, next to:

```text
main.py
```

Then run:

```bash
python main.py --repack
```

The toolkit will:

1. Read the original source bundles
2. Load the translated JSON/text files
3. Replace supported text entries
4. Rebuild the modified bundles
5. Write the processed files into the output directory

Repacked files will be written to:

```text
1-repack/
```

Files without supported editable text will be copied to:

```text
99-miss_folder/
```

---

## Step 6: Review Output

Check the files generated in:

```text
1-repack/
```

Use them only in your own local project, research setup, archival workflow, or personal localization environment.

---

## 🧠 Notes for Translators

- Edit only values, not keys
- Keep JSON syntax valid
- Do not delete technical tags in credits files
- Keep backup copies of your translated files
- Test small batches first before translating everything

---

## 🛠️ Developer Notes

The toolkit supports a narrow Unity AssetBundle text extraction and repacking workflow.

It currently focuses on:

- `TextAsset`
- selected `MonoBehaviour` text structures
- JSON-based translation values
- technical key mapping for safe reinjection
- optional credits extraction and repacking

The generated key mapping uses a delimiter-based structure to reduce accidental string collisions during repacking.

Example:

```text
some/path/file.bundle|||12345|||Subtitle_0
```

The delimiter is intentional:

```text
|||
```

Do not modify generated key files unless you are debugging the toolkit itself.

Credits handling is isolated in:

```text
src/credits.py
```

because credits data may use a different internal structure from regular text assets.

---

## ⚠️ Legal Disclaimer

This project is an unofficial, fan-made, open-source tool created for educational, research, archival, and personal localization workflow purposes.

This project is not affiliated with, sponsored, endorsed, approved, or maintained by any game publisher, developer, platform holder, or rights owner.

All trademarks, product names, copyrighted works, and proprietary assets belong to their respective owners.

This repository does not contain, distribute, or provide access to any original game files, copyrighted assets, encryption keys, decrypted data, or proprietary resources.

Users are responsible for ensuring that they have the legal right to process any files used with this toolkit.

The authors do not condone piracy, copyright infringement, unauthorized redistribution, or any illegal use of copyrighted content.
