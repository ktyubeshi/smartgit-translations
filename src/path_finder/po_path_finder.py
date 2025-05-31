from pathlib import Path


class PoPathFinder:
    """
    This class provides the functionality for returning the paths to each file
    in the repository that is used for translation.
    """

    def __init__(self, repository_root_dir="", version='24_1'):
        self.version = version
        if repository_root_dir == "":
            self.root_dir = get_repository_root()
        else:
            self.root_dir = repository_root_dir

    def get_po_files(self, translation_file_only=True) -> list:
        po_dir = Path(self.get_po_file_dir())
        if translation_file_only:
            pattern = '??_??.po'
        else:
            pattern = '*.po'
        po_files = [str(p) for p in po_dir.glob(pattern)]

        return po_files

    def get_pot_file(self) -> str:
        return str(Path(self.get_po_file_dir()) / 'messages.pot')

    def get_po_file_dir(self) -> str:
        return str(Path(self.root_dir) / 'po')

    def get_mismatch_file(self) -> str:
        return str(Path(self.get_po_file_dir()) / f'mismatch.{self.version}')

    def get_unknown_file(self) -> str:
        return str(Path(self.get_po_file_dir()) / f'unknown.{self.version}')


def get_repository_root() -> str:
    """Get the repository root directory (3 levels up from this file)."""
    return str(Path(__file__).resolve().parent.parent.parent)


def get_po_dir(base_dir: str) -> str:
    """Get the po directory path from the base directory."""
    return str(Path(base_dir) / "po")


def main():
    path_finder = PoPathFinder()
    pot_file = path_finder.get_pot_file()
    po_list = path_finder.get_po_files(translation_file_only=True)
    unknown_file = path_finder.get_unknown_file()
    mismatch_file = path_finder.get_mismatch_file()

    print(f"pot file:\t{pot_file}")
    for po_file in po_list:
        print(f"po file:\t{po_file}")

    print(f"unknown file:\t{unknown_file}")
    print(f"mismatch file:\t{mismatch_file}")


if __name__ == "__main__":
    main()
