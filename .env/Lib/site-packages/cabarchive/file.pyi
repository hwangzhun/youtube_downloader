import datetime
from typing import Any, Optional

class CabFile:
    buf: Any
    date: Any
    time: Any
    is_readonly: bool
    is_hidden: bool
    is_system: bool
    is_arch: bool
    is_exec: bool
    def __init__(self, buf: Optional[bytes] = ..., filename: Optional[str] = ..., mtime: Optional[datetime.datetime] = ...) -> None: ...
    def __len__(self) -> int: ...
    @property
    def filename(self) -> Optional[str]: ...
    is_name_utf8: Any
    @filename.setter
    def filename(self, filename: str) -> None: ...
