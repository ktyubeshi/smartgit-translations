import os

import polib


def optimize_po_entry(po_entry: polib.POEntry) -> polib.POEntry:
    """
    In the process of converting the SmartGit v23 mapping file to the .po file format, the existing key is assigned to msgctxt.
    If the sentence of msgid is included at the end of msgctxt, remove the original text from msgctxt and convert it to a concise expression.
    The optimized entries through this processing indicate that a combination of msgctxt and msgid becomes a key, which is signified by appending ':' at the end of msgctxt.
    """

    new_po_entry = po_entry
    original_text = '"' + po_entry.msgid + '"'
    if po_entry.msgctxt.endswith(original_text):
        new_po_entry.msgctxt = po_entry.msgctxt[: -len(original_text)] + ':'
    else:
        new_po_entry.msgctxt = po_entry.msgctxt

    return new_po_entry

def get_repository_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_po_dir(base_dir: str) -> str:
    return os.path.normpath(os.path.join(base_dir, "po"))

