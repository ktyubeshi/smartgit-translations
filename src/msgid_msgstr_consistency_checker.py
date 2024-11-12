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
- **Localization Support**: Output messages are available in English, Japanese, and Chinese.
  The language can be specified via command-line arguments.
- **Integration with sgpo**: Uses the `sgpo` library (an extension of `polib`) to read and
  write PO files.
- **Fuzzy Flagging**: Automatically adds the `fuzzy` flag to entries with inconsistencies.
- **Translator Comments**: Adds or updates translator comments to provide detailed error
  messages, prefixed with `[Checker]`.

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

3. **Output**:
   - The script prints any inconsistencies found, indicating the entry number and issues.
   - Updates the PO file by adding `fuzzy` flags and translator comments for problematic entries.

4. **Example**:
   - Checking a PO file with messages in Japanese:
     ```
     python po_checker.py -l ja
     ```
     This will prompt you to select a PO file and display messages in Japanese.

Requirements:
- **Python 3**: The script is compatible with Python 3.
- **sgpo Library**: Ensure the `sgpo` library is installed and accessible.
- **tkinter**: Used for the file selection dialog if no PO file is specified via command line.

Notes:
- **Backup**: It's recommended to backup your PO file before running the script, as it modifies the file.
- **Extensibility**: The script can be extended to support additional languages by adding entries to the `languages` dictionary.

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

def check_pot_entry(msgid, msgstr, lang):
    """Check escape sequences and HTML tags in a POT entry."""
    # Skip if msgstr is empty or whitespace only
    if not msgstr.strip():
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

def process_po_file(po_filepath, lang_code):
    """Process the PO file, report errors, and update entries with fuzzy flags and translator comments."""
    po = sgpo.pofile(po_filepath)

    errors_found = False
    checker_prefix = '[Checker] '  # Prefix to identify comments added by the checker

    lang = languages.get(lang_code, languages['en'])

    try:
        for entry in po:
            msgid = entry.msgid
            msgstr = entry.msgstr
            error = check_pot_entry(msgid, msgstr, lang)

            # Remove existing checker comments
            entry.tcomment = remove_checker_comments(entry.tcomment, checker_prefix)

            if error:
                errors_found = True
                print(f"{lang['entry_issue'].format(linenum=entry.linenum)}\n{error}\n")
                # Add fuzzy flag
                if 'fuzzy' not in entry.flags:
                    entry.flags.append('fuzzy')
                # Add error message to translator comments with prefix
                error_with_prefix = '\n'.join([checker_prefix + line for line in error.split('\n')])
                if entry.tcomment:
                    entry.tcomment += f"\n{error_with_prefix}"
                else:
                    entry.tcomment = error_with_prefix
        # Save the PO file
        po.save()
        if errors_found:
            print(lang['error_detected'])
        else:
            print(lang['no_errors'])
    except Exception as e:
        print(lang['error_saving_file'])
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='A script to check escape sequences and HTML tags in PO files.')
    parser.add_argument('po_file', nargs='?', help='Path to the PO file to check')
    parser.add_argument('-l', '--language', choices=['en', 'ja', 'zh'], default='en', help='Language for output messages (default: en)')
    args = parser.parse_args()

    po_filepath = args.po_file
    lang_code = args.language
    lang = languages.get(lang_code, languages['en'])

    if not po_filepath:
        # No command-line argument; show file dialog
        root = Tk()
        root.withdraw()  # Hide the main window
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

    process_po_file(po_filepath, lang_code)

if __name__ == "__main__":
    main()
