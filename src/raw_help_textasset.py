from __future__ import annotations

import io
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import lz4.block


def _read_cstr(f: io.BytesIO) -> bytes:
    out = bytearray()
    while True:
        c = f.read(1)
        if not c or c == b"\x00":
            return bytes(out)
        out.extend(c)


def _align4(x: int) -> int:
    return (x + 3) & ~3


def _align8(x: int) -> int:
    return (x + 7) & ~7


def _decompress_block(data: bytes, usize: int, flags: int) -> bytes:
    method = flags & 0x3F
    if method == 0:
        return data
    if method in (2, 3):
        return lz4.block.decompress(data, uncompressed_size=usize)
    raise ValueError(f"unsupported compression method {method}")


def _compress_block(data: bytes, flags: int) -> bytes:
    method = flags & 0x3F
    if method == 0:
        return data
    if method == 2:
        return lz4.block.compress(data, mode="default", store_size=False)
    if method == 3:
        return lz4.block.compress(data, mode="high_compression", store_size=False)
    raise ValueError(f"unsupported compression method {method}")


@dataclass
class UnityFSHeader:
    signature: bytes
    format_version: int
    unity_version: bytes
    engine_version: bytes
    total_file_size: int
    comp_blocks_info_size: int
    uncomp_blocks_info_size: int
    flags: int

    @classmethod
    def read(cls, f: io.BytesIO) -> "UnityFSHeader":
        sig = _read_cstr(f)
        fmt = struct.unpack(">I", f.read(4))[0]
        unity = _read_cstr(f)
        engine = _read_cstr(f)
        total = struct.unpack(">q", f.read(8))[0]
        comp_info = struct.unpack(">I", f.read(4))[0]
        uncomp_info = struct.unpack(">I", f.read(4))[0]
        flags = struct.unpack(">I", f.read(4))[0]
        return cls(sig, fmt, unity, engine, total, comp_info, uncomp_info, flags)

    def write(self) -> bytes:
        out = io.BytesIO()
        out.write(self.signature + b"\x00")
        out.write(struct.pack(">I", self.format_version))
        out.write(self.unity_version + b"\x00")
        out.write(self.engine_version + b"\x00")
        out.write(struct.pack(">q", self.total_file_size))
        out.write(struct.pack(">I", self.comp_blocks_info_size))
        out.write(struct.pack(">I", self.uncomp_blocks_info_size))
        out.write(struct.pack(">I", self.flags))
        return out.getvalue()


@dataclass
class BlockInfo:
    uncompressed_size: int
    compressed_size: int
    flags: int


@dataclass
class NodeInfo:
    offset: int
    size: int
    status: int
    path: bytes


@dataclass
class BlocksInfo:
    hash16: bytes
    blocks: List[BlockInfo]
    nodes: List[NodeInfo]

    @classmethod
    def read(cls, raw: bytes) -> "BlocksInfo":
        s = io.BytesIO(raw)
        hash16 = s.read(16)
        block_count = struct.unpack(">I", s.read(4))[0]
        blocks: List[BlockInfo] = []
        for _ in range(block_count):
            usize, csize, flags = struct.unpack(">IIH", s.read(10))
            blocks.append(BlockInfo(usize, csize, flags))
        node_count = struct.unpack(">I", s.read(4))[0]
        nodes: List[NodeInfo] = []
        for _ in range(node_count):
            off, size, status = struct.unpack(">qqI", s.read(20))
            path = _read_cstr(s)
            nodes.append(NodeInfo(off, size, status, path))
        return cls(hash16, blocks, nodes)

    def write(self) -> bytes:
        out = io.BytesIO()
        out.write(self.hash16)
        out.write(struct.pack(">I", len(self.blocks)))
        for b in self.blocks:
            out.write(struct.pack(">IIH", b.uncompressed_size, b.compressed_size, b.flags))
        out.write(struct.pack(">I", len(self.nodes)))
        for n in self.nodes:
            out.write(struct.pack(">qqI", n.offset, n.size, n.status))
            out.write(n.path + b"\x00")
        return out.getvalue()


@dataclass
class ObjectEntry:
    path_id: int
    offset: int
    size: int
    type_id: int
    entry_pos: int


@dataclass
class TextAssetRecord:
    path_id: int
    name: str
    text: str
    object_entry: ObjectEntry


@dataclass
class ParsedBundle:
    header: UnityFSHeader
    info: BlocksInfo
    data_stream: bytes
    tail: bytes


def parse_bundle(path: Path) -> ParsedBundle:
    blob = path.read_bytes()
    f = io.BytesIO(blob)
    header = UnityFSHeader.read(f)
    if header.signature != b"UnityFS":
        raise ValueError("not UnityFS")

    comp_info = f.read(header.comp_blocks_info_size)
    info_raw = _decompress_block(comp_info, header.uncomp_blocks_info_size, header.flags)
    info = BlocksInfo.read(info_raw)

    data = bytearray()
    for b in info.blocks:
        comp = f.read(b.compressed_size)
        data.extend(_decompress_block(comp, b.uncompressed_size, b.flags))

    tail = f.read()
    return ParsedBundle(header, info, bytes(data), tail)


def _find_object_table(cab: bytes) -> Tuple[Optional[int], List[ObjectEntry]]:
    if len(cab) < 20:
        return None, []
    meta_size = struct.unpack_from(">I", cab, 0)[0]
    data_offset = struct.unpack_from(">I", cab, 12)[0]
    meta_end = 20 + meta_size
    if meta_end > len(cab) or data_offset > len(cab):
        return None, []

    candidates: List[Tuple[int, int, int, List[ObjectEntry]]] = []
    for pos in range(20, meta_end - 4):
        count = struct.unpack_from("<I", cab, pos)[0]
        if not (1 <= count <= 100000):
            continue
        start = pos + 4
        end = start + count * 20
        if end > meta_end:
            continue
        entries: List[ObjectEntry] = []
        ok = True
        for i in range(count):
            p = start + i * 20
            pid = struct.unpack_from("<q", cab, p)[0]
            off = struct.unpack_from("<I", cab, p + 8)[0]
            size = struct.unpack_from("<I", cab, p + 12)[0]
            tid = struct.unpack_from("<i", cab, p + 16)[0]
            if size == 0 or off + size > len(cab) - data_offset or off % 4:
                ok = False
                break
            entries.append(ObjectEntry(pid, off, size, tid, p))
        if ok:
            candidates.append((count, -pos, pos, entries))

    if not candidates:
        return None, []
    candidates.sort(reverse=True)
    return candidates[0][2], candidates[0][3]


def _read_textasset_from_object(obj: bytes) -> Optional[Tuple[str, str, int, int, int]]:
    if len(obj) < 12:
        return None
    name_len = struct.unpack_from("<I", obj, 0)[0]
    name_start = 4
    name_end = name_start + name_len
    p = _align4(name_end)
    if name_end > len(obj) or p + 4 > len(obj):
        return None
    try:
        name = obj[name_start:name_end].decode("utf-8", "surrogateescape")
    except Exception:
        return None
    script_len = struct.unpack_from("<I", obj, p)[0]
    script_start = p + 4
    script_end = script_start + script_len
    if script_end > len(obj):
        return None
    try:
        text = obj[script_start:script_end].decode("utf-8", "surrogateescape")
    except Exception:
        return None
    if not ("title:" in text or "text." in text or "sub.title" in text or "image_" in text):
        return None
    return name, text, p, script_start, script_end


def extract_textassets_from_bundle(path: Path) -> List[TextAssetRecord]:
    parsed = parse_bundle(path)
    records: List[TextAssetRecord] = []
    for node in parsed.info.nodes:
        cab = parsed.data_stream[node.offset:node.offset + node.size]
        if len(cab) < 20:
            continue
        data_offset = struct.unpack_from(">I", cab, 12)[0]
        _, entries = _find_object_table(cab)
        for entry in entries:
            obj = cab[data_offset + entry.offset:data_offset + entry.offset + entry.size]
            got = _read_textasset_from_object(obj)
            if got is None:
                continue
            name, text, _, _, _ = got
            records.append(TextAssetRecord(entry.path_id, name, text, entry))
    return records


def _patch_text(raw: str, object_map: Dict[str, str]) -> Tuple[str, int]:
    lines = raw.split("\n")
    out: List[str] = []
    changed = 0
    for line in lines:
        if ":" not in line or line.strip().startswith("//"):
            out.append(line)
            continue
        key, value = line.split(":", 1)
        if "image_" in key.lower() or "image." in key.lower():
            out.append(line)
            continue
        translated = object_map.get(key)
        if translated is None:
            translated = object_map.get(key.strip())
        if translated is None:
            out.append(line)
            continue
        end = "\r" if value.endswith("\r") else ""
        out.append(f"{key}:{translated}{end}")
        changed += 1
    return "\n".join(out), changed


def _rebuild_textasset_object(old_obj: bytes, new_text: str) -> bytes:
    got = _read_textasset_from_object(old_obj)
    if got is None:
        raise ValueError("object is not a simple TextAsset")
    _name, _old_text, len_pos, _script_start, script_end = got
    prefix = old_obj[:len_pos]
    suffix = old_obj[script_end:]
    new_bytes = new_text.encode("utf-8", "surrogateescape")
    out = bytearray()
    out.extend(prefix)
    out.extend(struct.pack("<I", len(new_bytes)))
    out.extend(new_bytes)
    # TextAsset script is padded to 4 bytes inside the object.
    while len(out) % 4:
        out.append(0)
    # Preserve any non-padding suffix if a rare variant has fields after script.
    if suffix.strip(b"\x00"):
        out.extend(suffix)
    return bytes(out)


def _patch_cab(cab: bytes, file_object_map: Dict[str, Dict[str, str]]) -> Tuple[bytes, int]:
    if len(cab) < 20:
        return cab, 0
    data_offset = struct.unpack_from(">I", cab, 12)[0]
    _table_pos, entries = _find_object_table(cab)
    if not entries:
        return cab, 0

    metadata = bytearray(cab[:data_offset])
    data_sec = cab[data_offset:]
    replacements = 0
    patched_objects: Dict[int, bytes] = {}

    for entry in entries:
        object_map = file_object_map.get(str(entry.path_id))
        if not object_map:
            continue
        old_obj = data_sec[entry.offset:entry.offset + entry.size]
        got = _read_textasset_from_object(old_obj)
        if got is None:
            continue
        _name, raw, _len_pos, _script_start, _script_end = got
        new_text, n = _patch_text(raw, object_map)
        if n and new_text != raw:
            patched_objects[entry.path_id] = _rebuild_textasset_object(old_obj, new_text)
            replacements += n

    if not replacements:
        return cab, 0

    sorted_entries = sorted(entries, key=lambda e: e.offset)
    new_data = bytearray()
    for entry in sorted_entries:
        while len(new_data) % 8:
            new_data.append(0)
        new_off = len(new_data)
        obj_bytes = patched_objects.get(entry.path_id)
        if obj_bytes is None:
            obj_bytes = data_sec[entry.offset:entry.offset + entry.size]
        new_size = len(obj_bytes)
        new_data.extend(obj_bytes)
        # Patch object table entry: offset and size.
        struct.pack_into("<I", metadata, entry.entry_pos + 8, new_off)
        struct.pack_into("<I", metadata, entry.entry_pos + 12, new_size)

    new_file_size = data_offset + len(new_data)
    struct.pack_into(">I", metadata, 4, new_file_size)
    return bytes(metadata) + bytes(new_data), replacements


def patch_bundle_raw_textassets(path: Path, file_object_map: Dict[str, Dict[str, str]]) -> Tuple[bytes, int]:
    parsed = parse_bundle(path)
    data = bytearray(parsed.data_stream)
    total_replacements = 0

    cursor = 0
    for node in parsed.info.nodes:
        cab = bytes(data[node.offset:node.offset + node.size])
        new_cab, n = _patch_cab(cab, file_object_map)
        if n:
            total_replacements += n
            # Rebuild whole data stream from nodes below, easier than in-place variable size.
            break

    if not total_replacements:
        return path.read_bytes(), 0

    new_data_stream = bytearray()
    for node in parsed.info.nodes:
        cab = bytes(parsed.data_stream[node.offset:node.offset + node.size])
        new_cab, n = _patch_cab(cab, file_object_map)
        node.offset = len(new_data_stream)
        node.size = len(new_cab)
        new_data_stream.extend(new_cab)

    # Keep original block compression method/flags for these cursed files.
    block_flags = parsed.info.blocks[0].flags if parsed.info.blocks else (parsed.header.flags & 0x3F)
    comp_data = _compress_block(bytes(new_data_stream), block_flags)
    parsed.info.blocks = [BlockInfo(len(new_data_stream), len(comp_data), block_flags)]

    info_raw = parsed.info.write()
    comp_info = _compress_block(info_raw, parsed.header.flags)
    parsed.header.comp_blocks_info_size = len(comp_info)
    parsed.header.uncomp_blocks_info_size = len(info_raw)

    header_bytes_placeholder = parsed.header.write()
    parsed.header.total_file_size = len(header_bytes_placeholder) + len(comp_info) + len(comp_data) + len(parsed.tail)
    header_bytes = parsed.header.write()

    return header_bytes + comp_info + comp_data + parsed.tail, total_replacements
