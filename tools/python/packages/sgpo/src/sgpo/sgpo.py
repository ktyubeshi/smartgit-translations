from __future__ import annotations

import os
import re
from collections import namedtuple
from typing import Optional, Protocol

import polib

Key_tuple = namedtuple('Key_tuple', ['msgctxt', 'msgid'])


class PoBackend(Protocol):
    def load_file(
        self,
        filename: str,
        *,
        wrapwidth: int,
        chraset: str,
        check_for_duplicates: bool,
    ) -> polib.POFile:
        ...

    def load_text(
        self,
        text: str,
        *,
        wrapwidth: int,
        chraset: str,
        check_for_duplicates: bool,
    ) -> polib.POFile:
        ...


class PolibBackend:
    """Default backend that loads PO data via polib."""

    def load_file(
        self,
        filename: str,
        *,
        wrapwidth: int,
        chraset: str,
        check_for_duplicates: bool,
    ) -> polib.POFile:
        return polib.pofile(
            filename,
            wrapwidth=wrapwidth,
            chraset=chraset,
            check_for_duplicates=check_for_duplicates,
        )

    def load_text(
        self,
        text: str,
        *,
        wrapwidth: int,
        chraset: str,
        check_for_duplicates: bool,
    ) -> polib.POFile:
        return polib.pofile(
            text,
            wrapwidth=wrapwidth,
            chraset=chraset,
            check_for_duplicates=check_for_duplicates,
        )


def pofile(filename: str, *, backend: Optional[PoBackend] = None) -> SgPo:
    return SgPo._from_file(filename, backend=backend)


def pofile_from_text(text: str, *, backend: Optional[PoBackend] = None) -> SgPo:
    return SgPo._from_text(text, backend=backend)


class SgPo:
    META_DATA_BASE_DICT = {
        'Project-Id-Version': 'SmartGit',
        'Report-Msgid-Bugs-To': 'https://github.com/syntevo/smartgit-translations',
        'POT-Creation-Date': '',
        'PO-Revision-Date': '',
        'Last-Translator': '',
        'Language-Team': '',
        'Language': '',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
        'Plural-Forms': 'nplurals=1; plural=0;',
    }

    def __init__(self, po: Optional[polib.POFile] = None) -> None:
        self._po = po or polib.POFile(wrapwidth=9999, check_for_duplicates=True)
        if po is None:
            self.wrapwidth = 9999
            self.charset = 'utf-8'
            self.check_for_duplicates = True
        else:
            self.charset = getattr(po, "encoding", "utf-8")

    def __iter__(self):
        return iter(self._po)

    def __len__(self) -> int:
        return len(self._po)

    def __getitem__(self, index: int):
        return self._po[index]

    def __unicode__(self) -> str:
        if hasattr(self._po, "__unicode__"):
            return self._po.__unicode__()
        return str(self._po)

    def __str__(self) -> str:
        return self.__unicode__()

    def __getattr__(self, name: str):
        return getattr(self._po, name)

    @property
    def metadata(self) -> dict:
        return self._po.metadata

    @metadata.setter
    def metadata(self, value: dict) -> None:
        self._po.metadata = value

    @property
    def wrapwidth(self) -> int:
        return self._po.wrapwidth

    @wrapwidth.setter
    def wrapwidth(self, value: int) -> None:
        self._po.wrapwidth = value

    @property
    def check_for_duplicates(self) -> bool:
        return self._po.check_for_duplicates

    @check_for_duplicates.setter
    def check_for_duplicates(self, value: bool) -> None:
        self._po.check_for_duplicates = value

    @classmethod
    def _from_file(cls, filename: str, *, backend: Optional[PoBackend] = None):
        cls._validate_filename(filename)
        return cls._create_instance_from_file(filename, backend=backend)

    @classmethod
    def _from_text(cls, text: str, *, backend: Optional[PoBackend] = None):
        return cls._create_instance_from_text(text, backend=backend)

    @classmethod
    def _create_instance_from_file(
        cls, filename: str, *, backend: Optional[PoBackend] = None
    ) -> SgPo:
        backend = backend or PolibBackend()
        po = backend.load_file(
            filename,
            wrapwidth=9999,
            chraset='utf-8',
            check_for_duplicates=True,
        )
        return cls._create_instance(po)

    @classmethod
    def _create_instance_from_text(
        cls, text: str, *, backend: Optional[PoBackend] = None
    ) -> SgPo:
        backend = backend or PolibBackend()
        po = backend.load_text(
            text,
            wrapwidth=9999,
            chraset='utf-8',
            check_for_duplicates=True,
        )
        return cls._create_instance(po)

    @classmethod
    def _create_instance(cls, po: polib.POFile) -> SgPo:
        return cls(po)

    def import_unknown(self, unknown: SgPo) -> dict:
        success_count = 0
        for unknown_entry in unknown:
            # unknown_entry.flags = ['New']  # For debugging.
            my_entry = self.find_by_key(unknown_entry.msgctxt, unknown_entry.msgid)

            if my_entry is None:
                self.append(unknown_entry)
                success_count += 1

        return {'added': success_count}

    def import_mismatch(self, mismatch: SgPo) -> dict:
        new_entry_count = 0
        modified_entry_count = 0

        for mismatch_entry in mismatch:
            # mismatch_entry.flags = ['Modified']  # For debugging.
            my_entry = self.find_by_key(mismatch_entry.msgctxt, mismatch_entry.msgid)

            if my_entry is not None:
                if my_entry.msgid != mismatch_entry.msgid:
                    my_entry.previous_msgid = my_entry.msgid
                    my_entry.msgid = mismatch_entry.msgid
                    modified_entry_count += 1
            else:
                self.append(mismatch_entry)
                new_entry_count += 1

        return {'added': new_entry_count, 'modified': modified_entry_count}

    def import_pot(self, pot: SgPo) -> dict:
        new_entry_count = 0
        modified_entry_count = 0
        po_key_set = set(self.get_key_list())
        pot_key_set = set(pot.get_key_list())

        diff_pot_only_key = pot_key_set - po_key_set
        diff_po_only_key = po_key_set - pot_key_set
        obsolete_entry_count = 0

        # Add new my_entry
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
            obsolete_entry_count += 1

        # Modified entry
        for my_entry in self:
            if not my_entry.msgctxt.endswith(':'):
                pot_entry = pot.find_by_key(my_entry.msgctxt, None)

                if pot_entry and (my_entry.msgid != pot_entry.msgid):
                    my_entry.previous_msgid = my_entry.msgid
                    my_entry.msgid = pot_entry.msgid
                    my_entry.flags = ['fuzzy']
                    modified_entry_count += 1

        return {
            'added': new_entry_count,
            'modified': modified_entry_count,
            'obsolete': obsolete_entry_count,
        }

    def delete_extracted_comments(self):
        """
        Deletes the extracted comments that originate from unknown or mismatch files.
        In the case of SmartGit, this is where the activity log is output.
        """
        for entry in self:
            if entry.comment:
                entry.comment = ""

    def find_by_key(self, msgctxt: str, msgid: Optional[str]) -> Optional[polib.POEntry]:
        for entry in self:
            # If the msgctxt ends with ':', the combination of msgid and
            # msgctxt becomes the key that identifies the entry.
            # Otherwise, only msgctxt is the key to identify the entry.
            if entry.msgctxt.endswith(':'):
                if entry.msgctxt == msgctxt and entry.msgid == msgid:
                    return entry
            else:
                if entry.msgctxt == msgctxt:
                    return entry

        return None

    def sort(self, *, key=None, reverse=False):
        if key is None:
            self._po.sort(key=lambda entry: (self._po_entry_to_sort_key(entry)), reverse=reverse)
        else:
            self._po.sort(key=key, reverse=reverse)

    def format(self):
        self.metadata = self._filter_po_metadata(self.metadata)
        self.sort()

    def save(self, fpath=None, repr_method='__unicode__', newline='\n') -> None:
        # Change the default value of newline to \n (LF).
        self._po.save(fpath=fpath, repr_method=repr_method, newline=newline)

    def get_key_list(self) -> list:
        return [self._po_entry_to_key_tuple(entry) for entry in self]

    # ======= Private methods =======
    @staticmethod
    def _filter_po_metadata(meta_dict: dict) -> dict:
        """
        By reconstructing the metadata, only the predefined metadata is preserved.
        """
        new_meta_dict = {}
        for meta_key, meta_value in SgPo.META_DATA_BASE_DICT.items():
            if meta_value == '':
                new_meta_dict[meta_key] = meta_dict.get(meta_key, '')
            else:
                new_meta_dict[meta_key] = meta_value
        return new_meta_dict

    def _po_entry_to_sort_key(self, po_entry: polib.POEntry) -> str:
        """
        Reorders the sort results by rewriting the sort key as intended.
        Entries starting with a '*' are greeted with a character of ASCII code 1 at the beginning to be placed at the start of the file.
        Keys other than these are further rewritten through a key filter.
        """
        if po_entry.msgctxt.startswith('*'):
            # Add a character with an ASCII code of 1 at the beginning to make the sort order come first.
            return chr(1) + self._po_entry_to_legacy_key(po_entry)
        else:
            return self._multi_keys_filter(self._po_entry_to_legacy_key(po_entry))

    @staticmethod
    def _po_entry_to_legacy_key(po_entry: polib.POEntry) -> str:
        if po_entry.msgctxt.endswith(':'):
            return po_entry.msgctxt.rstrip(':') + '"' + po_entry.msgid + '"'
        else:
            return po_entry.msgctxt

    @staticmethod
    def _po_entry_to_key_tuple(po_entry: polib.POEntry) -> Key_tuple:
        if po_entry.msgctxt.endswith(':'):
            return Key_tuple(msgctxt=po_entry.msgctxt, msgid=po_entry.msgid)
        else:
            return Key_tuple(msgctxt=po_entry.msgctxt, msgid=None)

    @staticmethod
    def _multi_keys_filter(text):
        """
        Rewrite the string to be sorted to group the multi keys entries together in the appropriate position in the locale file.
        """

        pattern = r"(?<!\\\\)\(([^)]+)\)(?!\\\\)"  # Matches everything inside parentheses that are NOT escaped

        # Use re.sub to add 'ZZZ' and remove parentheses from any matched pattern
        modified_text = re.sub(pattern, 'ZZZ\\1', text)

        return modified_text

    @staticmethod
    def _validate_filename(filename: str) -> bool:

        if not filename:
            raise ValueError("File path cannot be None")

        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")

        pattern = r".*\d+_\d+$"
        if not (filename.endswith('.po') or filename.endswith('pot') or re.match(pattern, filename)):
            raise ValueError("File type not supported")

        return True
