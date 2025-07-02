import argparse
import os
import sgpo
from path_finder import PoPathFinder


def main():
    parser = argparse.ArgumentParser(description="Format SmartGit PO files.")
    parser.add_argument(
        'file',
        nargs='?',
        default=None,
        help='The PO file to format. If not provided, all PO files will be formatted.'
    )
    args = parser.parse_args()

    po_files = []
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found at {args.file}")
            exit(-1)
        po_files.append(args.file)
    else:
        finder = PoPathFinder()
        po_files = finder.get_po_files(translation_file_only=True)

    for po_file in po_files:
        try:
            po = sgpo.pofile(po_file)
            print(f' po file:\t{po_file}')
        except FileNotFoundError as e:
            print(e)
            exit(-1)

        po.format()
        po.save(po_file)


if __name__ == "__main__":
    main()
