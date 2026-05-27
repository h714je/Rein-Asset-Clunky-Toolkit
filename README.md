# Rein-Asset-Clunky-Toolkit

A straightforward and slightly rough-around-the-edges set of Python scripts for extracting and repacking text assets (TextAsset and MonoBehaviour) from Unity asset bundles. 

## ⚠️ Important Limitation (Known Issues)
This tool was built for a very specific task and has its quirks (hence the name). 
Currently, the parsing logic and key structure only work reliably with the **English localization**. 
The toolkit expects the base files to be located at the following path:
`revisions/0/assetbundle/text/en`

Attempting to extract Japanese (`ja`) or Korean (`ko`) assets will likely result in MonoBehaviour parsing errors or skipped strings due to structural differences. If you plan to translate the game into your native language, please use the English bundles as your base source.

---

## 📂 Project Structure

```text
Rein-Asset-Clunky-Toolkit/
├── config.json             # Paths and language settings (edit this!)
├── main.py                 # Main entry point for the toolkit
├── requirements.txt        # Python dependencies
└── src/                    # Source code logic
    ├── extractor.py        
    ├── repacker.py         
    ├── credits.py          
    └── utils.py            

```

Data directories (create these or they will be generated automatically):

* `0-decrypted/` — Place your original (decrypted) game bundles here.
* `1-repack/` — The final repacked files with your injected translations will appear here.
* `99-miss_folder/` — Files that did not contain any text to translate will be safely copied here.

## 🚀 Installation

1. Ensure you have **Python** installed (version 3.11 or higher is recommended).
2. Download or clone this repository.
3. Open a terminal in the project folder and install the `UnityPy` dependency:
```bash
pip install -r requirements.txt

```



## ⚙️ Configuration (`config.json`)

Before starting, open `config.json` in any text editor.

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

* **`target_language`**: The language code you are translating *into* (e.g., `ru`, `es`, `fr`). This determines the names of the generated JSON files.
* **`scan_path`**: Do not change this unless you are absolutely sure of what you are doing.
* **`need_credits`**: Set to `true` if you need to extract and translate the ending credits (`credit.assetbundle`), or `false` if you want to skip them.

## 📝 How to Use

### Step 1: Extraction (Extract)

Place your original English bundles into the `0-decrypted` folder, preserving the original folder structure (e.g., `0-decrypted/revisions/0/assetbundle/text/en/...`).

Run the following command:

```bash
python main.py --extract

```

**What happens:**
The script will scan the bundles and create the following files:

* `0-ru-values.json` (the actual text to be translated).
* `0-ru-keys.json` (a technical mapping file—do not touch this).
* `0-ru-credit.txt` (a simple text file with the credits, if enabled in the config).

### Step 2: Translation

* Open `0-ru-values.json` and translate the values. This format is perfect for uploading to collaborative translation platforms like **Crowdin**, **Weblate**, or **Tolgee**.
* The `0-ru-credit.txt` file can be translated in any standard text editor like Notepad. Do not delete technical tags like `<h3>` or `<type1>`.

### Step 3: Repacking (Repack)

Ensure that your translated `0-ru-values.json` and `0-ru-credit.txt` files are located in the root folder, right next to `main.py`.

Run the following command:

```bash
python main.py --repack

```

**What happens:**
The script takes the original bundles, carefully replaces the English text with your translations, and saves the ready-to-use files into the `1-repack` folder. Unmodified files will be sent to `99-miss_folder`.

Grab the files from `1-repack`, put them back into the game, and test!


## ⚠️ Legal Disclaimer
This project is an unofficial, fan-made, open-source tool created for educational, research, archival, and personal localization workflow purposes.
This project is not affiliated with, sponsored, endorsed, approved, or maintained by any game publisher, developer, platform holder, or rights owner.
All trademarks, product names, copyrighted works, and proprietary assets belong to their respective owners.
This repository does not contain, distribute, or provide access to any original game files, copyrighted assets, encryption keys, decrypted data, or proprietary resources.
Users are responsible for ensuring that they have the legal right to process any files used with this toolkit.
The authors do not condone piracy, copyright infringement, unauthorized redistribution, or any illegal use of copyrighted content.
