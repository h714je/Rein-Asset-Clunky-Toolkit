from __future__ import annotations

import gc
import importlib
import inspect
import sys
from pathlib import Path
from typing import Any


def assert_unitypy_version() -> None:
    import UnityPy
    version = getattr(UnityPy, "__version__", "unknown")
    if version != "1.10.18":
        raise RuntimeError(
            f"Help backend requires UnityPy==1.10.18, got {version}. "
            "UnityPy 1.25 repacks but corrupts UI/Help CAB layout."
        )

def disable_native_unitypy_extensions() -> None:
    """Force UnityPy 1.10.x down the Python reader path for Help bundles."""
    for name in (
        "UnityPyExt",
        "UnityPy.UnityPyExt",
        "UnityPy.EndianBinaryReader",
        "UnityPy.EndianBinaryWriter",
    ):
        sys.modules[name] = None


def patch_safe_reader_writer() -> None:
    try:
        from UnityPy.streams.EndianBinaryReader import EndianBinaryReader  # type: ignore

        def safe_read_string_to_null(self: Any, max_length: int = 32767) -> str:
            data = bytearray()
            try:
                while len(data) < max_length:
                    if hasattr(self, "Position") and hasattr(self, "Length") and self.Position == self.Length:
                        break

                    c = self.read(1) if hasattr(self, "read") else self.read_bytes(1)
                    if not c:
                        break

                    if isinstance(c, int):
                        if c == 0:
                            break
                        data.append(c & 0xFF)
                        continue

                    if c == b"\x00":
                        break

                    data.extend(c[:1])
            except Exception:
                # Deliberately tolerate unterminated/broken strings in obfuscated
                # AssetBundle metadata. We only need to reach TextAsset objects.
                pass

            return bytes(data).decode("utf8", "surrogateescape")

        EndianBinaryReader.read_string_to_null = safe_read_string_to_null
        print("  [OK] UnityPy safe string reader patched")
    except Exception as e:
        print(f"  [WARN] Could not patch UnityPy safe reader: {e}")

    try:
        from UnityPy.streams.EndianBinaryWriter import EndianBinaryWriter  # type: ignore

        def safe_write_string_to_null(self: Any, val: str) -> None:
            self.write(str(val).encode("utf8", "surrogateescape"))
            self.write(b"\x00")

        EndianBinaryWriter.write_string_to_null = safe_write_string_to_null
    except Exception:
        pass


def patch_unitypy_container_helper() -> None:
    patched_any = False

    try:
        sf_mod = importlib.import_module("UnityPy.files.SerializedFile")
        ContainerHelper = getattr(sf_mod, "ContainerHelper", None)

        if ContainerHelper is not None:
            def patched_container_init(self: Any, container: Any = None, *args: Any, **kwargs: Any) -> None:
                self.container = container if container is not None else []
                self.path_dict = {}
                try:
                    for key, value in self.container:
                        asset = getattr(value, "asset", None)
                        pid = getattr(asset, "path_id", None)
                        if pid is not None:
                            self.path_dict[pid] = key
                except Exception:
                    pass

            ContainerHelper.__init__ = patched_container_init
            patched_any = True
    except Exception:
        pass

    try:
        for obj in gc.get_objects():
            try:
                if isinstance(obj, type) and obj.__name__ in {"NodeHelper", "UnknownObject"}:
                    if not hasattr(obj, "path_id"):
                        setattr(obj, "path_id", 0)
            except Exception:
                pass
    except Exception:
        pass

    if patched_any:
        print("  [OK] UnityPy ContainerHelper patched")
    else:
        print("  [WARN] Could not patch UnityPy ContainerHelper; load_fail may remain")

def check_lz4_patch() -> None:
    print("  [OK] UnityPy disk lz4 patch not required: toolkit uses packer=(66, 2)")


def prepare_help_unitypy_runtime() -> None:
    disable_native_unitypy_extensions()
    assert_unitypy_version()
    patch_safe_reader_writer()
    patch_unitypy_container_helper()
    check_lz4_patch()
