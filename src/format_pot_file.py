import sgpo
from path_finder import PoPathFinder


def main():
    finder = PoPathFinder()
    pot_file = finder.get_pot_file()

    try:
        po = sgpo.pofile(pot_file)
        print(f' po file:\t{pot_file}')
    except FileNotFoundError as e:
        print(e)
        exit(-1)

    po.format()
    po.save(pot_file, newline='\n')


if __name__ == "__main__":
    main()
