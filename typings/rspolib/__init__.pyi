from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Any, Optional


class POEntry:
    msgctxt: Optional[str]
    msgid: str
    msgstr: str
    msgstr_plural: Sequence[str] | dict[int, str]
    obsolete: bool
    flags: list[str]
    comment: str
    previous_msgid: str

    def get_flags(self) -> Sequence[str]: ...
    def get_msgstr_plural(self) -> Sequence[str]: ...


class POFile(Iterable[POEntry]):
    metadata: dict[str, str]
    wrapwidth: int
    entries: list[POEntry]

    def __iter__(self) -> Iterator[POEntry]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> POEntry: ...
    def append(self, entry: POEntry) -> None: ...
    def sort(
        self,
        *,
        key: Optional[Callable[[POEntry], Any]] = ...,
        reverse: bool = ...,
    ) -> None: ...
    def save(
        self,
        fpath: Optional[str] = ...,
        repr_method: str = ...,
        newline: str = ...,
    ) -> None: ...
    def get_metadata(self) -> dict[str, str]: ...


def pofile(
    pofile: str,
    *,
    wrapwidth: int = ...,
    **kwargs: Any,
) -> POFile: ...
