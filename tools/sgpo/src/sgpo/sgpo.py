from __future__ import annotations

import os
import re
from collections import namedtuple
from typing import Callable, Iterator, Optional, Protocol

import rspolib
from sgpo_common import META_DATA_BASE_DICT as COMMON_METADATA_BASE_DICT

Key_tuple = namedtuple('Key_tuple', ['msgctxt', 'msgid'])


class PoBackend(Protocol):
    def load_file(
        self,
        filename: str,
        *,
        wrapwidth: int,
    ) -> rspolib.POFile:
        ...

    def load_text(
        self,
        text: str,
        *,
        wrapwidth: int,
    ) -> rspolib.POFile:
        ...


class RspolibBackend:
    """Default backend that loads PO data via rspolib."""
    def load_file(
        self,
        filename: str,
        *,
        wrapwidth: int,
    ) -> rspolib.POFile:
        """Load a PO/POT file from disk via rspolib."""
        return rspolib.pofile(filename, wrapwidth=wrapwidth)

    def load_text(
        self,
        text: str,
        *,
        wrapwidth: int,
    ) -> rspolib.POFile:
        """Load PO content from an in-memory string via rspolib."""
        return rspolib.pofile(text, wrapwidth=wrapwidth)


def pofile(filename: str, *, backend: Optional[PoBackend] = None) -> SGPoFile:
    """Return an SGPoFile loaded from a PO/POT path with validation."""
    SGPoFile._validate_filename(filename)
    backend = backend or RspolibBackend()
    po = backend.load_file(filename, wrapwidth=9999)
    return SGPoFile(po, backend=backend)


def pofile_from_text(text: str, *, backend: Optional[PoBackend] = None) -> SGPoFile:
    """Return an SGPoFile loaded from raw PO text."""
    backend = backend or RspolibBackend()
    po = backend.load_text(text, wrapwidth=9999)
    return SGPoFile(po, backend=backend)


class SGPoFile:
    """Domain wrapper around rspolib that adds SmartGit-specific behaviors."""

    META_DATA_BASE_DICT = COMMON_METADATA_BASE_DICT

    def __init__(
        self,
        po: Optional[rspolib.POFile] = None,
        *,
        backend: Optional[PoBackend] = None,
    ) -> None:
        """Create a new SGPoFile wrapping an existing or fresh rspolib.POFile."""
        self._backend = backend or RspolibBackend()
        self._po = po or rspolib.POFile("", wrapwidth=9999)
        self._wrapwidth = getattr(self._po, "wrapwidth", 9999)

    def __iter__(self) -> Iterator[rspolib.POEntry]:
        """Iterate over contained PO entries."""
        return iter(self._po)

    def __len__(self) -> int:
        """Return the number of PO entries."""
        return len(self._po)

    def __getitem__(self, index: int) -> rspolib.POEntry:
        """Return entry at *index*."""
        return self._po[index]

    def append(self, entry: rspolib.POEntry) -> None:
        """Append an entry to the underlying PO file."""
        self._po.append(entry)

    def replace_entries(self, entries: list[rspolib.POEntry]) -> None:
        """Replace the PO file entries wholesale."""
        self.replace_entries(entries)

    def __unicode__(self) -> str:
        """Return the PO file text the way rspolib renders it."""
        return str(self._po)

    def __str__(self) -> str:
        return self.__unicode__()

    @property
    def metadata(self) -> dict:
        """Return the PO metadata dictionary."""
        if hasattr(self._po, "get_metadata"):
            return self._po.get_metadata()
        return self._po.metadata

    @metadata.setter
    def metadata(self, value: dict) -> None:
        """Replace the PO metadata dictionary."""
        self._po.metadata = value

    @property
    def wrapwidth(self) -> int:
        """Return the wrap width used by rspolib when rendering."""
        return self._wrapwidth

    @wrapwidth.setter
    def wrapwidth(self, value: int) -> None:
        """Set the wrap width used by rspolib."""
        self._wrapwidth = value
        if hasattr(self._po, "wrapwidth"):
            self._po.wrapwidth = value

    def import_unknown(self, unknown: 'SGPoFile') -> dict[str, int]:
        """Merge entries from *unknown* while tracking the number added."""
        added = 0
        for unknown_entry in unknown:
            my_entry = self.find_by_key(unknown_entry.msgctxt, unknown_entry.msgid)
            if my_entry is None:
                self.append(unknown_entry)
                added += 1
        return {'added': added}

    def import_mismatch(self, mismatch: 'SGPoFile') -> dict[str, int]:
        """Merge mismatch data, counting new entries and msgid updates."""
        added = 0
        modified = 0

        for mismatch_entry in mismatch:
            my_entry = self.find_by_key(mismatch_entry.msgctxt, mismatch_entry.msgid)

            if my_entry is None:
                self.append(mismatch_entry)
                added += 1
                continue

            if my_entry.msgid != mismatch_entry.msgid:
                my_entry.previous_msgid = my_entry.msgid
                my_entry.msgid = mismatch_entry.msgid
                self._ensure_flag(my_entry, 'fuzzy')
                modified += 1

        return {'added': added, 'modified': modified}

    def import_pot(self, pot: 'SGPoFile') -> dict[str, int]:
        """Sync this file with *pot*, returning counts for reporting."""
        new_entry_count = 0
        modified_entry_count = 0

        po_key_set = set(self.get_key_list())
        pot_key_set = set(pot.get_key_list())

        diff_pot_only_key = pot_key_set - po_key_set
        diff_po_only_key = po_key_set - pot_key_set
        obsolete_count = 0

        for key in diff_pot_only_key:
            entry = pot.find_by_key(key.msgctxt, key.msgid)
            if entry is None:
                continue
            self.append(entry)
            new_entry_count += 1

        # Remove obsolete entry
        for key in diff_po_only_key:
            entry = self.find_by_key(key.msgctxt, key.msgid)
            if entry is None:
                continue
            entry.obsolete = True
            obsolete_count += 1

        for my_entry in self:
            entry_msgctxt = my_entry.msgctxt or ""
            if entry_msgctxt.endswith(':'):
                continue
            pot_entry = pot.find_by_key(entry_msgctxt, None)
            if pot_entry and (my_entry.msgid != pot_entry.msgid):
                my_entry.previous_msgid = my_entry.msgid
                my_entry.msgid = pot_entry.msgid
                self._ensure_flag(my_entry, 'fuzzy')
                modified_entry_count += 1

        return {
            'added': new_entry_count,
            'modified': modified_entry_count,
            'obsolete': obsolete_count,
        }

    def delete_extracted_comments(self) -> int:
        """Remove extracted comments originating from unknown/mismatch logs."""
        removed = 0
        for entry in self:
            if getattr(entry, 'comment', None):
                entry.comment = None
                removed += 1
        return removed

    def find_by_key(
        self, msgctxt: str, msgid: Optional[str]
    ) -> Optional[rspolib.POEntry]:
        for entry in self:
            # If the msgctxt ends with ':', the combination of msgid and
            # msgctxt becomes the key that identifies the entry.
            # Otherwise, only msgctxt is the key to identify the entry.
            entry_msgctxt = entry.msgctxt or ""
            if entry_msgctxt.endswith(':'):
                if entry_msgctxt == msgctxt and entry.msgid == msgid:
                    return entry
            else:
                if entry_msgctxt == msgctxt:
                    return entry

        return None

    def sort(
        self,
        *,
        key: Optional[Callable[[rspolib.POEntry], str]] = None,
        reverse: bool = False,
    ) -> None:
        """Sort entries with SmartGit's special key ordering."""
        entries = list(self._po)
        sort_key = key or (lambda entry: self._po_entry_to_sort_key(entry))
        entries.sort(key=sort_key, reverse=reverse)
        self._po.entries = entries

    def format(self) -> None:
        """Normalize metadata ordering/values and sort entries."""
        self.metadata = self._filter_po_metadata(self.metadata)
        self.sort()

    def save(
        self,
        fpath: Optional[str] = None,
        repr_method: str = '__unicode__',
        newline: str = '\n',
    ) -> None:
        """Persist the PO file using rspolib's saver."""
        if not fpath:
            raise ValueError("fpath is required to save a PO file")
        self._po.save(fpath)

    def get_key_list(self) -> list[Key_tuple]:
        """Return SmartGit key tuples for all entries."""
        return [self._po_entry_to_key_tuple(entry) for entry in self]

    @staticmethod
    def _filter_po_metadata(meta_dict: dict) -> dict:
        """Filter metadata down to the allowed SmartGit keys."""
        new_meta_dict = {}
        for meta_key, meta_value in SGPoFile.META_DATA_BASE_DICT.items():
            if meta_value == '':
                new_meta_dict[meta_key] = meta_dict.get(meta_key, '')
            else:
                new_meta_dict[meta_key] = meta_value
        return new_meta_dict

    def _po_entry_to_sort_key(self, po_entry: rspolib.POEntry) -> str:
        """Return the sortable key string for the given entry."""
        msgctxt = po_entry.msgctxt or ""
        if msgctxt.startswith('*'):
            # Add a character with an ASCII code of 1 at the beginning to make the sort order come first.
            return chr(1) + self._po_entry_to_legacy_key(po_entry)
        return self._multi_keys_filter(self._po_entry_to_legacy_key(po_entry))

    @staticmethod
    def _po_entry_to_legacy_key(po_entry: rspolib.POEntry) -> str:
        """Return the legacy string key used for ordering."""
        msgctxt = po_entry.msgctxt or ""
        if msgctxt.endswith(':'):
            return msgctxt.rstrip(':') + '"' + po_entry.msgid + '"'
        return msgctxt

    @staticmethod
    def _po_entry_to_key_tuple(po_entry: rspolib.POEntry) -> Key_tuple:
        """Return the SmartGit key tuple for this entry."""
        msgctxt = po_entry.msgctxt or ""
        if msgctxt.endswith(':'):
            return Key_tuple(msgctxt=msgctxt, msgid=po_entry.msgid)
        return Key_tuple(msgctxt=msgctxt, msgid=None)

    @staticmethod
    def _multi_keys_filter(text: str) -> str:
        """Normalize multi-key markers so they sort deterministically."""
        pattern = r"(?<!\\\\)\(([^)]+)\)(?!\\\\)"
        return re.sub(pattern, r'ZZZ\1', text)

    @staticmethod
    def _ensure_flag(entry: rspolib.POEntry, flag: str) -> None:
        """Ensure *flag* is present on the entry without clobbering others."""
        if hasattr(entry, "get_flags"):
            flags = list(entry.get_flags())
        else:
            flags = list(getattr(entry, 'flags', []) or [])
        if flag not in flags:
            flags.append(flag)
        entry.flags = flags

    @staticmethod
    def _validate_filename(filename: str) -> bool:
        """Ensure the filename exists and has a supported extension."""
        if not filename:
            raise ValueError("File path cannot be None")
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        pattern = r".*\d+_\d+$"
        if not (
            filename.endswith('.po')
            or filename.endswith('.pot')
            or re.match(pattern, filename)
        ):
            raise ValueError("File type not supported")
        return True


SgPo = SGPoFile
