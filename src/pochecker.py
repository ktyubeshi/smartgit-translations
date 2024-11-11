import re
import html
import argparse
import sys
import os
from collections import Counter
import polib

try:
    # Python 3
    from tkinter import Tk, filedialog
except ImportError:
    # Python 2
    from Tkinter import Tk, filedialog

def unescape_html_entities(text):
    """HTMLエンティティをデコード"""
    return html.unescape(text)

def get_escape_sequences(text):
    """テキスト中のエスケープシーケンスのリストを取得"""
    # HTMLエンティティをデコード
    text_unescaped = unescape_html_entities(text)
    # エスケープシーケンスを抽出
    # エスケープ文字のパターン（バックスラッシュに続く任意の文字）
    return re.findall(r'\\.', text_unescaped)

def get_html_tags(text):
    """テキスト中のHTMLタグのリストを取得"""
    # HTMLエンティティをデコード
    text_unescaped = unescape_html_entities(text)
    # タグ名を抽出（開始タグと終了タグの両方）
    return re.findall(r'</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>', text_unescaped)

def check_pot_entry(msgid, msgstr):
    """POTエントリのエスケープシーケンスとHTMLタグをチェック"""
    # msgstr が空または空白のみの場合はチェックをスキップ
    if not msgstr.strip():
        return None

    errors = []

    # エスケープシーケンスの種類と数を取得
    escapes_msgid = Counter(get_escape_sequences(msgid))
    escapes_msgstr = Counter(get_escape_sequences(msgstr))
    if escapes_msgid != escapes_msgstr:
        missing = escapes_msgid - escapes_msgstr
        extra = escapes_msgstr - escapes_msgid
        error_messages = []
        if missing:
            error_messages.append(f"msgstr に不足しているエスケープシーケンス: {dict(missing)}")
        if extra:
            error_messages.append(f"msgstr に余分なエスケープシーケンス: {dict(extra)}")
        errors.append('; '.join(error_messages))

    # HTMLタグの種類と数を取得
    tags_msgid = Counter(get_html_tags(msgid))
    tags_msgstr = Counter(get_html_tags(msgstr))
    if tags_msgid != tags_msgstr:
        missing = tags_msgid - tags_msgstr
        extra = tags_msgstr - tags_msgid
        error_messages = []
        if missing:
            error_messages.append(f"msgstr に不足しているHTMLタグ: {dict(missing)}")
        if extra:
            error_messages.append(f"msgstr に余分なHTMLタグ: {dict(extra)}")
        errors.append('; '.join(error_messages))

    if errors:
        return ' | '.join(errors)
    return None

def process_po_file(po_filepath):
    """POファイルを処理し、エラーを報告し、必要に応じてエントリにfuzzyフラグを追加"""
    po = polib.pofile(po_filepath)

    errors_found = False

    for entry in po:
        msgid = entry.msgid
        msgstr = entry.msgstr
        error = check_pot_entry(msgid, msgstr)
        if error:
            errors_found = True
            print(f"エントリ {entry.linenum}: {error}")
            # fuzzy フラグを追加
            if 'fuzzy' not in entry.flags:
                entry.flags.append('fuzzy')

    if errors_found:
        # PO ファイルを上書き保存
        po.save()
        print(f"\nエラーが検出されたため、'fuzzy' フラグを追加して PO ファイルを保存しました。")
    else:
        print("エラーなし。")

def main():
    parser = argparse.ArgumentParser(description='POファイルのエスケープシーケンスとHTMLタグをチェックするスクリプト')
    parser.add_argument('po_file', nargs='?', help='チェックするPOファイルのパス')
    args = parser.parse_args()

    po_filepath = args.po_file

    if not po_filepath:
        # コマンドライン引数がない場合、ファイル選択ダイアログを表示
        root = Tk()
        root.withdraw()  # メインウィンドウを表示しない
        po_filepath = filedialog.askopenfilename(
            title='POファイルを選択してください',
            filetypes=[('PO files', '*.po'), ('All files', '*.*')]
        )
        root.update()
        root.destroy()

        if not po_filepath:
            print("POファイルが選択されませんでした。スクリプトを終了します。")
            sys.exit(1)

    if not os.path.isfile(po_filepath):
        print(f"指定されたファイルが見つかりません: {po_filepath}")
        sys.exit(1)

    process_po_file(po_filepath)

if __name__ == "__main__":
    main()
