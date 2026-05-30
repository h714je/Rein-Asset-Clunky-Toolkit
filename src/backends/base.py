from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PackContext:
    input_dir: Path
    output_dir: Path
    miss_dir: Path
    scan_path: str
    copy_unmodified_to_output: bool = False
    force_save: bool = False
    allow_raw_fallback_repack: bool = False


@dataclass
class PackResult:
    status: str
    rel_path: str
    replacements: int = 0
    error: Optional[str] = None


class PackerBackend:
    name = "base"

    def prepare(self) -> None:
        pass

    def pack_file(self, src: Path, semantic_path: str, store, ctx: PackContext) -> PackResult:
        raise NotImplementedError