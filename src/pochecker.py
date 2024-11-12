import re
import html
import argparse
import sys
import os
from collections import Counter
import sgpo

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
    return re.findall(r'\\.', text_unescaped)

def get_html_tags(text):
    """テキスト中のHTMLタグのリストを取得"""
    # HTMLエンティティをデコード
    text_unescaped = unescape_html_entities(text)
    # タグ名を抽出（開始タグと終了タグの両方）
    return re.findall(r'</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>', text_unescaped)

def format_error_message(missing, extra, item_type):
    """エラーメッセージを整形"""
    messages = []
    if missing:
        for seq, count in missing.items():
            messages.append(f"・不足している{item_type}: '{seq}' が {count} 個")
    if extra:
        for seq, count in extra.items():
            messages.append(f"・余分な{item_type}: '{seq}' が {count} 個")
    return '\n'.join(messages)

def check_pot_entry(msgid, msgstr):
    """POTエントリのエスケープシーケンスとHTMLタグをチェック"""
    # msgstr が空または空白のみの場合はチェックをスキップ
    if not msgstr.strip():
        return None

    error_messages = []

    # エスケープシーケンスの種類と数を取得
    escapes_msgid = Counter(get_escape_sequences(msgid))
    escapes_msgstr = Counter(get_escape_sequences(msgstr))
    if escapes_msgid != escapes_msgstr:
        missing = escapes_msgid - escapes_msgstr
        extra = escapes_msgstr - escapes_msgid
        error = "エスケープ文字に問題があります。\n"
        error += format_error_message(missing, extra, "エスケープ文字")
        error_messages.append(error)

    # HTMLタグの種類と数を取得
    tags_msgid = Counter(get_html_tags(msgid))
    tags_msgstr = Counter(get_html_tags(msgstr))
    if tags_msgid != tags_msgstr:
        missing = tags_msgid - tags_msgstr
        extra = tags_msgstr - tags_msgid
        error = "HTMLタグに問題があります。\n"
        error += format_error_message(missing, extra, "HTMLタグ")
        error_messages.append(error)

    if error_messages:
        return '\n'.join(error_messages)
    return None

def remove_checker_comments(tcomment, prefix):
    """チェッカーが付与したコメントを削除"""
    if not tcomment:
        return ''
    lines = tcomment.split('\n')
    filtered_lines = [line for line in lines if not line.startswith(prefix)]
    return '\n'.join(filtered_lines)

def process_po_file(po_filepath):
    """POファイルを処理し、エラーを報告し、必要に応じてエントリにfuzzyフラグとTranslatorコメントを追加"""
    po = sgpo.pofile(po_filepath)

    errors_found = False
    checker_prefix = '[Checker] '  # チェッカーが付与したコメントのプレフィックス

    for entry in po:
        msgid = entry.msgid
        msgstr = entry.msgstr
        error = check_pot_entry(msgid, msgstr)

        # 既存のチェッカーコメントを削除
        entry.tcomment = remove_checker_comments(entry.tcomment, checker_prefix)

        if error:
            errors_found = True
            print(f"エントリ {entry.linenum} に問題があります:\n{error}\n")
            # fuzzy フラグを追加
            if 'fuzzy' not in entry.flags:
                entry.flags.append('fuzzy')
            # エラーの理由をTranslatorコメントに追加
            # 各行にチェッカーのプレフィックスを付加
            error_with_prefix = '\n'.join([checker_prefix + line for line in error.split('\n')])
            if entry.tcomment:
                entry.tcomment += f"\n{error_with_prefix}"
            else:
                entry.tcomment = error_with_prefix

    if errors_found:
        # PO ファイルを上書き保存
        po.save()
        print(f"エラーが検出されたため、'fuzzy' フラグとエラーの理由を追加して PO ファイルを保存しました。")
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
