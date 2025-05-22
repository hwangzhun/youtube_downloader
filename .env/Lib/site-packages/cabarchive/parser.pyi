from cabarchive.archive import CabArchive as CabArchive
from cabarchive.errors import CorruptionError as CorruptionError, NotSupportedError as NotSupportedError
from cabarchive.file import CabFile as CabFile
from cabarchive.utils import FMT_CFFOLDER as FMT_CFFOLDER, FMT_CFHEADER_RESERVE as FMT_CFHEADER_RESERVE
from typing import Any

COMPRESSION_MASK_TYPE: int
COMPRESSION_TYPE_NONE: int
COMPRESSION_TYPE_MSZIP: int
COMPRESSION_TYPE_QUANTUM: int
COMPRESSION_TYPE_LZX: int

class CabArchiveParser:
    cfarchive: Any
    flattern: Any
    def __init__(self, cfarchive: CabArchive, flattern: bool = ...) -> None: ...
    def parse_cffile(self, offset: int) -> int: ...
    def parse_cffolder(self, idx: int, offset: int) -> None: ...
    def parse_cfdata(self, idx: int, offset: int, compression: int) -> int: ...
    def parse(self, buf: bytes) -> None: ...
