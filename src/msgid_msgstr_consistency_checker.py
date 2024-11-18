#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PO File Checker Script
----------------------

This script checks for inconsistencies between the `msgid` and `msgstr` entries
in PO files, specifically focusing on escape sequences and HTML tags. It ensures
that the same escape sequences and HTML tags present in the `msgid` are also
present in the `msgstr`.

Key Features:
- **Escape Sequence Check**: Verifies that the escape sequences (e.g., `\n`, `\t`, `\\`)
  in the `msgid` are matched in the `msgstr`.
- **HTML Tag Check**: Ensures that HTML tags (e.g., `<b>`, `</i>`) are consistently used
  between `msgid` and `msgstr`.
- **Fixed Flag Support**: Entries with the 'fixed' flag (case-insensitive) are skipped
  from checking.
- **Error Export**: Option to export problematic entries to a separate PO file
  for review.
- **Localization Support**: Output messages are available in English, Japanese,
  and Chinese.
- **Integration with sgpo**: Uses the `sgpo` library (an extension of `polib`)
  to read and write PO files.
- **Fuzzy Flagging**: Automatically adds the `fuzzy` flag to entries with
  inconsistencies.
- **Translator Comments**: Adds or updates translator comments to provide detailed
  error messages, prefixed with `[Checker]`.

Usage:
1. **Running the Script**:
   - From the command line, specify the PO file and optional language code:
     ```
     python po_checker.py path/to/your_file.po --language ja
     ```
   - If no PO file is specified, a file selection dialog will appear.

2. **Command-Line Arguments**:
   - `po_file`: Path to the PO file to check (optional).
   - `-l` or `--language`: Language code for output messages (`en`, `ja`, or `zh`).
     Defaults to `en` (English).
   - `-e` or `--export`: Export problematic entries to a separate PO file.
     The output file will be named with '_errors' suffix.

3. **Output**:
   - The script prints any inconsistencies found, indicating the entry number
     and issues.
   - Updates the PO file by adding `fuzzy` flags and translator comments for
     problematic entries.
   - If export option is enabled, creates a new PO file containing only the
     problematic entries.

"""

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
    # Python 2 (Not recommended)
    from Tkinter import Tk, filedialog

# Localization messages
languages = {
    'en': {
        'missing': " - Missing {item_type}: '{seq}' ({count} time(s))",
        'extra': " - Extra {item_type}: '{seq}' ({count} time(s))",
        'escape_issue': "There is an issue with escape characters.",
        'html_issue': "There is an issue with HTML tags.",
        'escape_char': "escape character",
        'html_tag': "HTML tag",
        'entry_issue': "Entry {linenum} has issues:",
        'error_detected': "Errors were detected. The PO file has been updated with 'fuzzy' flags and error comments.",
        'no_errors': "No errors found.",
        'file_not_found': "The specified file was not found: {filepath}",
        'file_not_selected': "No PO file was selected. Exiting the script.",
        'select_po_file': "Please select a PO file",
        'error_saving_file': "Error saving the PO file.",
        'error_export': "Problematic entries have been exported to: {filepath}",
    },
    'ja': {
        'missing': "・不足している{item_type}: '{seq}' が {count} 個",
        'extra': "・余分な{item_type}: '{seq}' が {count} 個",
        'escape_issue': "エスケープ文字に問題があります。",
        'html_issue': "HTMLタグに問題があります。",
        'escape_char': "エスケープ文字",
        'html_tag': "HTMLタグ",
        'entry_issue': "エントリ {linenum} に問題があります:",
        'error_detected': "エラーが検出されたため、'fuzzy' フラグとエラーの理由を PO ファイルに追加しました。",
        'no_errors': "エラーなし。",
        'file_not_found': "指定されたファイルが見つかりません: {filepath}",
        'file_not_selected': "POファイルが選択されませんでした。スクリプトを終了します。",
        'select_po_file': "POファイルを選択してください",
        'error_saving_file': "POファイルの保存中にエラーが発生しました。",
        'error_export': "問題のあるエントリーを以下のファイルにエクスポートしました: {filepath}",
    },
    'zh': {
        'missing': " - 缺少的{item_type}: '{seq}' （{count} 次）",
        'extra': " - 多余的{item_type}: '{seq}' （{count} 次）",
        'escape_issue': "转义字符存在问题。",
        'html_issue': "HTML标签存在问题。",
        'escape_char': "转义字符",
        'html_tag': "HTML标签",
        'entry_issue': "第 {linenum} 行存在问题：",
        'error_detected': "检测到错误。PO文件已更新了 'fuzzy' 标记和错误注释。",
        'no_errors': "未发现错误。",
        'file_not_found': "未找到指定的文件：{filepath}",
        'file_not_selected': "未选择PO文件。脚本退出。",
        'select_po_file': "请选择一个PO文件",
        'error_saving_file': "保存PO文件时出错。",
        'error_export': "有问题的条目已导出至：{filepath}",
    }
}

def unescape_html_entities(text):
    """Decode HTML entities in the text."""
    return html.unescape(text)

def get_escape_sequences(text):
    """Extract a list of escape sequences from the text."""
    # Decode HTML entities
    text_unescaped = unescape_html_entities(text)
    # Extract escape sequences (backslash followed by any character)
    return re.findall(r'\\.', text_unescaped)

def get_html_tags(text):
    """Extract a list of HTML tags from the text."""
    # Decode HTML entities
    text_unescaped = unescape_html_entities(text)
    # Extract tag names (both start and end tags)
    return re.findall(r'</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>', text_unescaped)

def format_error_message(missing, extra, item_type, lang):
    """Format the error message."""
    messages = []
    if missing:
        for seq, count in missing.items():
            messages.append(lang['missing'].format(item_type=item_type, seq=seq, count=count))
    if extra:
        for seq, count in extra.items():
            messages.append(lang['extra'].format(item_type=item_type, seq=seq, count=count))
    return '\n'.join(messages)

def check_pot_entry(msgid, msgstr, lang, entry):
    """Check escape sequences and HTML tags in a POT entry."""
    # Skip if msgstr is empty or whitespace only
    if not msgstr.strip():
        return None

    # Skip if the entry has a 'fixed' flag (case-insensitive)
    if hasattr(entry, 'flags') and any(flag.lower() == 'fixed' for flag in entry.flags):
        return None

    error_messages = []

    # Get counts of escape sequences
    escapes_msgid = Counter(get_escape_sequences(msgid))
    escapes_msgstr = Counter(get_escape_sequences(msgstr))
    if escapes_msgid != escapes_msgstr:
        missing = escapes_msgid - escapes_msgstr
        extra = escapes_msgstr - escapes_msgid
        error = lang['escape_issue'] + '\n'
        error += format_error_message(missing, extra, lang['escape_char'], lang)
        error_messages.append(error)

    # Get counts of HTML tags
    tags_msgid = Counter(get_html_tags(msgid))
    tags_msgstr = Counter(get_html_tags(msgstr))
    if tags_msgid != tags_msgstr:
        missing = tags_msgid - tags_msgstr
        extra = tags_msgstr - tags_msgid
        error = lang['html_issue'] + '\n'
        error += format_error_message(missing, extra, lang['html_tag'], lang)
        error_messages.append(error)

    if error_messages:
        return '\n'.join(error_messages)
    return None

def remove_checker_comments(tcomment, prefix):
    """Remove comments added by the checker."""
    if not tcomment:
        return ''
    lines = tcomment.split('\n')
    filtered_lines = [line for line in lines if not line.startswith(prefix)]
    return '\n'.join(filtered_lines)

def process_po_file(po_filepath, lang_code, export_errors=False):
    """Process the PO file, report errors, and update entries with fuzzy flags and translator comments."""
    po = sgpo.pofile(po_filepath)
    error_entries = []  # エラーのあるエントリを保存するリスト
    errors_found = False
    checker_prefix = '[Checker] '

    lang = languages.get(lang_code, languages['en'])

    try:
        for entry in po:
            msgid = entry.msgid
            msgstr = entry.msgstr
            error = check_pot_entry(msgid, msgstr, lang, entry)

            entry.tcomment = remove_checker_comments(entry.tcomment, checker_prefix)

            if error:
                errors_found = True
                print(f"{lang['entry_issue'].format(linenum=entry.linenum)}\n{error}\n")
                if 'fuzzy' not in entry.flags:
                    entry.flags.append('fuzzy')
                error_with_prefix = '\n'.join([checker_prefix + line for line in error.split('\n')])
                if entry.tcomment:
                    entry.tcomment += f"\n{error_with_prefix}"
                else:
                    entry.tcomment = error_with_prefix
                
                if export_errors:
                    error_entries.append(entry)

        po.save()
        
        if errors_found:
            print(lang['error_detected'])
            if export_errors and error_entries:
                # エラーエントリを新しいPOファイルに保存
                error_po = sgpo.POFile()
                error_po.extend(error_entries)
                export_path = os.path.splitext(po_filepath)[0] + '_errors.po'
                error_po.save(export_path)
                print(lang['error_export'].format(filepath=export_path))
        else:
            print(lang['no_errors'])
    except Exception as e:
        print(lang['error_saving_file'])
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='A script to check escape sequences and HTML tags in PO files.'
    )
    parser.add_argument('po_file', nargs='?', help='Path to the PO file to check')
    parser.add_argument(
        '-l', '--language',
        choices=['en', 'ja', 'zh'],
        default='ja',
        help='Language for output messages (default: en)'
    )
    parser.add_argument(
        '-e', '--export',
        action='store_true',
        help='Export problematic entries to a separate PO file'
    )
    args = parser.parse_args()

    po_filepath = args.po_file
    lang_code = args.language
    lang = languages.get(lang_code, languages['en'])

    if not po_filepath:
        root = Tk()
        root.withdraw()
        po_filepath = filedialog.askopenfilename(
            title=lang['select_po_file'],
            filetypes=[('PO files', '*.po'), ('All files', '*.*')]
        )
        root.update()
        root.destroy()

        if not po_filepath:
            print(lang['file_not_selected'])
            sys.exit(1)

    if not os.path.isfile(po_filepath):
        print(lang['file_not_found'].format(filepath=po_filepath))
        sys.exit(1)

    process_po_file(po_filepath, lang_code, args.export)

if __name__ == "__main__":
    main()
