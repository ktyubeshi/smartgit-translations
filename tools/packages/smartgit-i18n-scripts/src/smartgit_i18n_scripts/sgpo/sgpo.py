from __future__ import annotations

import os
import re
from collections import namedtuple

import rspolib

Key_tuple = namedtuple('Key_tuple', ['msgctxt', 'msgid'])


def pofile(filename: str) -> SgPo:
    return SgPo._from_file(filename)


def pofile_from_text(text: str) -> SgPo:
    return SgPo._from_text(text)


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

    def __init__(self, po: rspolib.POFile | None = None) -> None:
        if po is None:
            self.entries = []
            self.metadata = {}
        else:
            self.entries = list(po.get_entries())
            self.metadata = dict(po.get_metadata())
        self.wrapwidth = 9999

    @classmethod
    def _from_file(cls, filename: str):
        cls._validate_filename(filename)
        return cls._create_instance(filename)

    @classmethod
    def _from_text(cls, text: str):
        return cls._create_instance(text)

    @classmethod
    def _create_instance(cls, path_or_content) -> SgPo:
        return cls(rspolib.pofile(path_or_content, wrapwidth=9999))

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return str(self._to_rspolib_file())

    def append(self, entry: rspolib.POEntry) -> None:
        self.entries.append(entry)

    def translated_entries(self) -> list:
        return [entry for entry in self.entries if entry.msgstr and not self._is_fuzzy(entry)]

    def untranslated_entries(self) -> list:
        return [entry for entry in self.entries if not entry.msgstr and not self._is_fuzzy(entry)]

    def fuzzy_entries(self) -> list:
        return [entry for entry in self.entries if self._is_fuzzy(entry)]

    def import_unknown(self, unknown: SgPo) -> None:
        success_count = 0
        print('\nImport unknown entry...')
        for unknown_entry in unknown:
            # unknown_entry.flags = ['New']  # For debugging.
            my_entry = self.find_by_key(unknown_entry.msgctxt, unknown_entry.msgid)

            if my_entry is not None:
                if my_entry.msgid == unknown_entry.msgid:
                    print(f'\nAlready exists.(Skipped)')
                    print(f'\t\tmsgctxt "{unknown_entry.msgctxt}"')
                    print(f'\t\tmsgid "{unknown_entry.msgid}"')
                else:
                    print(f'\nAlready exists. but,msgid has been changed.(Skipped)')
                    print(f'\t\t#| msgid "{my_entry.msgid}"')
                    print(f'\t\tmsgctxt "{unknown_entry.msgctxt}"')
                    print(f'\t\tmsgid "{unknown_entry.msgid}"')
            else:
                try:
                    self.append(unknown_entry)
                    print(f'\nNew entry added.')
                    print(f'\t\tmsgctxt "{unknown_entry.msgctxt}')
                    print(f'\t\tmsgid "{unknown_entry.msgid}')
                    success_count += 1
                except ValueError as e:
                    print(e)
                except IOError as e:
                    print(e)

        print(f'{success_count} entries added.')

    def import_mismatch(self, mismatch: SgPo) -> None:
        new_entry_count = 0
        modified_entry_count = 0

        print('\nImport unknown entry...')
        for mismatch_entry in mismatch:
            # mismatch_entry.flags = ['Modified']  # For debugging.
            my_entry = self.find_by_key(mismatch_entry.msgctxt, mismatch_entry.msgid)

            if my_entry is not None:
                if my_entry.msgid == mismatch_entry.msgid:
                    print(f'\nAlready exists.(Skipped)')
                    print(f'\t\t#| msgid "{my_entry.previous_msgid}"')
                    print(f'\t\tmsgctxt "{my_entry.msgctxt}"')
                    print(f'\t\tmsgid "{my_entry.msgid}"')
                else:
                    print(f'\nmsgid has been changed.')
                    print(f'\t\t#| msgid "{my_entry.msgid}"')
                    print(f'\t\tmsgctxt "{mismatch_entry.msgctxt}"')
                    print(f'\t\tmsgid "{mismatch_entry.msgid}"')
                    my_entry.previous_msgid = my_entry.msgid
                    my_entry.msgid = mismatch_entry.msgid
                    modified_entry_count += 1
            else:
                try:
                    self.append(mismatch_entry)
                    print(f'\nNew entry added.')
                    print(f'\t\tmsgctxt "{mismatch_entry.msgctxt}"')
                    print(f'\t\tmsgid "{mismatch_entry.msgid}"')
                    new_entry_count += 1
                except ValueError as e:
                    print(e)
                except IOError as e:
                    print(e)

        print(f'{new_entry_count} entries added.')
        print(f'{modified_entry_count} entries modified.')

    def import_pot(self, pot: SgPo) -> None:
        new_entry_count = 0
        modified_entry_count = 0
        po_key_set = set(self.get_key_list())
        pot_key_set = set(pot.get_key_list())

        diff_pot_only_key = pot_key_set - po_key_set
        diff_po_only_key = po_key_set - pot_key_set

        # Add new my_entry
        print(f'\npot file only: {len(diff_pot_only_key)}')
        for key in diff_pot_only_key:
            print(f'msgctxt:\t"{key.msgctxt}"\n'
                  f'  msgid:\t"{key.msgid}"\n')

            self.append(pot.find_by_key(key.msgctxt, key.msgid))
            new_entry_count += 1

        # Remove obsolete entry
        print(f'\npo file only: {len(diff_po_only_key)}')
        for key in diff_po_only_key:
            print(f'msgctxt:\t"{key.msgctxt}"\n'
                  f'  msgid:\t"{key.msgid}"\n')

            entry = self.find_by_key(key.msgctxt, key.msgid)
            entry.obsolete = True

        # Modified entry
        for my_entry in self:
            if not my_entry.msgctxt.endswith(':'):
                pot_entry = pot.find_by_key(my_entry.msgctxt, None)

                if pot_entry and (my_entry.msgid != pot_entry.msgid):
                    print(f'msgctxt:\t{my_entry.msgctxt}\n'
                          f'  msgid:\t{my_entry.msgid}\n')
                    my_entry.previous_msgid = my_entry.msgid
                    my_entry.msgid = pot_entry.msgid
                    my_entry.flags = ['fuzzy']
                    modified_entry_count += 1

        print(f'\n     new entry:\t{new_entry_count}')
        print(f'\nmodified entry:\t{modified_entry_count}')

    def delete_extracted_comments(self):
        """
        Deletes the extracted comments that originate from unknown or mismatch files.
        In the case of SmartGit, this is where the activity log is output.
        """
        for entry in self:
            if entry.comment:
                entry.comment = None

    def find_by_key(self, msgctxt: str, msgid: str) -> rspolib.POEntry:
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
            self.entries.sort(key=lambda entry: (self._po_entry_to_sort_key(entry)), reverse=reverse)
        else:
            self.entries.sort(key=key, reverse=reverse)

    def format(self):
        self.metadata = self._filter_po_metadata(self.metadata)
        self.sort()

    def save(self, fpath=None, repr_method='__unicode__', newline='\n') -> None:
        # Change the default value of newline to \n (LF).
        self._to_rspolib_file().save(fpath)

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

    def _to_rspolib_file(self) -> rspolib.POFile:
        po = rspolib.POFile()
        po.wrapwidth = self.wrapwidth
        po.update_metadata(self.metadata)
        for entry in self.entries:
            po.append(entry)
        return po

    @staticmethod
    def _is_fuzzy(entry: rspolib.POEntry) -> bool:
        return 'fuzzy' in entry.get_flags()

    def _po_entry_to_sort_key(self, po_entry: rspolib.POEntry) -> str:
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
    def _po_entry_to_legacy_key(po_entry: rspolib.POEntry) -> str:
        if po_entry.msgctxt.endswith(':'):
            return po_entry.msgctxt.rstrip(':') + '"' + po_entry.msgid + '"'
        else:
            return po_entry.msgctxt

    @staticmethod
    def _po_entry_to_key_tuple(po_entry: rspolib.POEntry) -> Key_tuple:
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
