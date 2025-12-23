import unittest

import sgpo
from sgpo.actions import _remove_duplicate_entries_po, _remove_duplicate_entries_pot


POT_CONTENT = """msgid ""
msgstr ""

msgctxt "dup.key"
msgid "Hello"
msgstr ""

msgctxt "dup.key"
msgid "Hello"
msgstr ""
"""


PO_CONTENT = """msgid ""
msgstr ""

msgctxt "dup.one"
msgid "Hello"
msgstr ""

msgctxt "dup.one"
msgid "Hello"
msgstr "Translated"

msgctxt "dup.two"
msgid "Bonjour"
msgstr "FR1"

msgctxt "dup.two"
msgid "Bonjour"
msgstr "FR2"

msgctxt "dup.three"
msgid "Ciao"
msgstr ""

msgctxt "dup.three"
msgid "Ciao"
msgstr ""
"""


class TestRemoveDuplicateEntriesPot(unittest.TestCase):
    def test_removes_duplicate_msgctxt_msgid_pairs(self):
        po = sgpo.pofile_from_text(POT_CONTENT)

        removed = _remove_duplicate_entries_pot(po)

        self.assertEqual(1, removed)
        remaining = [(entry.msgctxt, entry.msgid) for entry in po if entry.msgid]
        self.assertEqual([("dup.key", "Hello")], remaining)


class TestRemoveDuplicateEntriesPo(unittest.TestCase):
    def test_prefers_translated_entries_and_marks_fuzzy_on_duplicates(self):
        po = sgpo.pofile_from_text(PO_CONTENT)

        removed, fuzzy_marked = _remove_duplicate_entries_po(po)

        self.assertEqual(2, removed)
        self.assertEqual(2, fuzzy_marked)

        dup_one = [entry for entry in po if entry.msgctxt == "dup.one"]
        self.assertEqual(1, len(dup_one))
        self.assertEqual("Translated", dup_one[0].msgstr)

        dup_two = [entry for entry in po if entry.msgctxt == "dup.two"]
        self.assertEqual(2, len(dup_two))
        self.assertTrue(all("fuzzy" in (entry.flags or []) for entry in dup_two))

        dup_three = [entry for entry in po if entry.msgctxt == "dup.three"]
        self.assertEqual(1, len(dup_three))
