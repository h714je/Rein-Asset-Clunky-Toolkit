import UnityPy
from pathlib import Path
from .utils import extract_text, save_text

def extract_credits(config: dict):
    if not config.get("need_credits", False):
        return

    input_dir = Path(config["input_dir"])
    scan_dir = input_dir / config["scan_path"]
    lang = config["target_language"]
    
    credit_file = scan_dir / "credit.assetbundle"
    out_txt = Path(f"0-en-credit.txt")
    
    if not credit_file.exists():
        print(f"  [!] Credits file not found: {credit_file}")
        return
        
    try:
        env = UnityPy.load(str(credit_file))
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                # The credits bundle contains only one TextAsset, so just extract it
                raw_text, _, _, _ = extract_text(obj)
                
                if raw_text:
                    with open(out_txt, "w", encoding="utf-8") as f:
                        f.write(raw_text)
                    print(f"  [CREDITS] Credits successfully extracted to: {out_txt}")
                return
                
    except Exception as e:
        print(f"  [!] Error while extracting credits: {e}")

def repack_credits(config: dict):
    if not config.get("need_credits", False):
        return

    input_dir = Path(config["input_dir"])
    output_dir = Path(config["output_dir"])
    scan_dir = input_dir / config["scan_path"]
    lang = config["target_language"]
    
    credit_file = scan_dir / "credit.assetbundle"
    in_txt = Path(f"0-{lang}-credit.txt")
    
    if not credit_file.exists():
        return
        
    if not in_txt.exists():
        print(f"  [!] Modified credits file {in_txt} not found. Skipping credits repacking.")
        return

    try:
        with open(in_txt, "r", encoding="utf-8") as f:
            new_text = f.read()

        env = UnityPy.load(str(credit_file))
        modified = False
        
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                # Directly repack the only TextAsset
                raw, src_type, d, tree = extract_text(obj)
                save_text(obj, new_text, src_type, d, tree)
                modified = True
                break

        if modified:
            dst = output_dir / config["scan_path"] / "credit.assetbundle"
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "wb") as f:
                f.write(env.file.save(packer="original"))
            print(f"  [CREDITS] Credits successfully repacked!")
            
    except Exception as e:
        print(f"  [!] Error while repacking credits: {e}")