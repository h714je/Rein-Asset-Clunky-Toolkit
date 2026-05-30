from .original_unitypy import OriginalUnityPyBackend
from .help_unitypy_lz4_66 import HelpUnityPyLz466Backend

BACKENDS = {
    "original": OriginalUnityPyBackend,
    "help_unitypy_lz4_66": HelpUnityPyLz466Backend,
}