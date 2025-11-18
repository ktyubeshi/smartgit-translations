import sgpo
from path_finder import PoPathFinder


def _compress_one_po(po) -> int:
    changed = 0
    for entry in po:
        if getattr(entry, "obsolete", False):
            continue
        if entry.msgid == "":  # header 等
            continue
        if not getattr(entry, "msgctxt", None):
            continue

        pattern = '"' + entry.msgid + '"'  # polib でアンエスケープ済み前提
        if entry.msgctxt.endswith(pattern):
            entry.msgctxt = entry.msgctxt[: -len(pattern)] + ":"
            changed += 1
    return changed


def main():
    finder = PoPathFinder()
    pot_file = finder.get_pot_file()
    po_files = finder.get_po_files(translation_file_only=True)

    targets = []
    if pot_file:
        targets.append(pot_file)  # messages.pot なども処理対象に含める
    targets.extend(po_files)

    total = 0
    for po_path in targets:
        po = sgpo.pofile(po_path)
        changed = _compress_one_po(po)
        if changed:
            po.save(po_path)
        print(f"{po_path}: compressed {changed} entries.")
        total += changed
    print(f"Total compressed: {total}")


if __name__ == "__main__":
    main()
