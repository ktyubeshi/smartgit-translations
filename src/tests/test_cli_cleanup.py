import unittest

import sgpo
from sgpo.actions import _cleanup_obsolete_empty_msgstr


TEST_PO_CONTENT = """msgid ""
msgstr ""

msgctxt "active.entry"
msgid "Active entry"
msgstr "Translated"

msgctxt "needs.translation"
msgid "Todo entry"
msgstr ""

#~ msgctxt "obsolete.keep"
#~ msgid "Keep me"
#~ msgstr "Old translation"

#~ msgctxt "obsolete.blank"
#~ msgid "Remove me"
#~ msgstr ""

#~ msgctxt "obsolete.whitespace"
#~ msgid "Whitespace translation"
#~ msgstr "   "

#~ msgctxt "obsolete.plural.blank"
#~ msgid "Singular blank"
#~ msgid_plural "Plural blank"
#~ msgstr[0] ""
#~ msgstr[1] ""

#~ msgctxt "obsolete.plural.keep"
#~ msgid "Singular keep"
#~ msgid_plural "Plural keep"
#~ msgstr[0] "one"
#~ msgstr[1] ""
"""


class TestCleanupObsoleteEmptyMsgstr(unittest.TestCase):
    def test_removes_only_blank_obsolete_entries(self):
        po = sgpo.pofile_from_text(TEST_PO_CONTENT)

        removed = _cleanup_obsolete_empty_msgstr(po)

        self.assertEqual(3, removed)

        remaining_keys = {(entry.msgctxt, entry.msgid) for entry in po}
        self.assertIn(("obsolete.keep", "Keep me"), remaining_keys)
        self.assertIn(("obsolete.plural.keep", "Singular keep"), remaining_keys)
        self.assertIn(("needs.translation", "Todo entry"), remaining_keys)
        self.assertNotIn(("obsolete.blank", "Remove me"), remaining_keys)
        self.assertNotIn(("obsolete.whitespace", "Whitespace translation"), remaining_keys)
        self.assertNotIn(("obsolete.plural.blank", "Singular blank"), remaining_keys)

        kept_obsolete = next(entry for entry in po if entry.msgctxt == "obsolete.keep")
        self.assertTrue(getattr(kept_obsolete, "obsolete", False))
        self.assertEqual("Old translation", kept_obsolete.msgstr)

        plural_kept = next(entry for entry in po if entry.msgctxt == "obsolete.plural.keep")
        self.assertTrue(getattr(plural_kept, "obsolete", False))
        self.assertEqual("one", plural_kept.msgstr_plural.get(0))

        non_obsolete_blank = next(entry for entry in po if entry.msgctxt == "needs.translation")
        self.assertFalse(getattr(non_obsolete_blank, "obsolete", False))
        self.assertEqual("", non_obsolete_blank.msgstr)
