import sgpo
from path_finder import PoPathFinder


def _ensure_colon(po) -> int:
    changed = 0
    for entry in po:
        if getattr(entry, "obsolete", False):
            continue
        if entry.msgid == "":
            continue
        if not getattr(entry, "msgctxt", None):
            continue
        if not entry.msgctxt.endswith(':'):
            entry.msgctxt = entry.msgctxt + ':'
            changed += 1
    return changed


def main():
    finder = PoPathFinder()
    po_files = finder.get_po_files(translation_file_only=True)

    total = 0
    for po_path in po_files:
        po = sgpo.pofile(po_path)
        changed = _ensure_colon(po)
        if changed:
            po.save(po_path)
        print(f"{po_path}: appended colon to {changed} entries.")
        total += changed
    print(f"Total changed: {total}")


if __name__ == "__main__":
    main()
