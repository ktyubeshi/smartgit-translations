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

    # コメントがないエントリとコメントがあるエントリを分ける
    no_comment_entries = []
    comment_entries = []

    for entry in po:
        if not entry.comment:  # コメントがないエントリ
            no_comment_entries.append(entry)
        else:  # コメントがあるエントリ
            comment_entries.append(entry)

    # コメントがないエントリのみを一時的に新しいsgpo.SgPoオブジェクトに追加
    formatted_po = sgpo.SgPo()  # SgPo クラスのインスタンスを作成
    formatted_po.extend(no_comment_entries)

    # メタデータのLanguageを設定
    formatted_po.metadata["Language"] = "en_US"

    # フォーマットを実行
    formatted_po.format()

    # コメントがあるエントリを末尾に追加
    formatted_po.extend(comment_entries)

    # ファイルに保存
    formatted_po.save(pot_file, newline='\n')


if __name__ == "__main__":
    main()
