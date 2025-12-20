import re
import sgpo
from path_finder import PoPathFinder

_PLACEHOLDER_TAIL = re.compile(r'(?:%\d+)+$')


def _strip_placeholders_tail(text: str) -> str:
    if text is None:
        return text
    # 末尾の ':' はいったん外してから処理し、最後に戻す
    has_colon = text.endswith(':')
    base = text[:-1] if has_colon else text
    new_base = _PLACEHOLDER_TAIL.sub('', base)
    return new_base + (':' if has_colon else '')


def _process_one_po(po) -> int:
    changed = 0
    for entry in po:
        if getattr(entry, "obsolete", False):
            continue
        if entry.msgid == "":
            continue
        if not getattr(entry, "msgctxt", None):
            continue
        new_ctxt = _strip_placeholders_tail(entry.msgctxt)
        if new_ctxt != entry.msgctxt:
            entry.msgctxt = new_ctxt
            changed += 1
    return changed


def main():
    finder = PoPathFinder()
    po_files = finder.get_po_files(translation_file_only=True)

    total = 0
    for po_path in po_files:
        po = sgpo.pofile(po_path)
        changed = _process_one_po(po)
        if changed:
            po.save(po_path)
        print(f"{po_path}: stripped {changed} entries.")
        total += changed
    print(f"Total stripped: {total}")


if __name__ == "__main__":
    main()
