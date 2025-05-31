# Scripts

## Scripts for po file operations

### import_unknown.py
'unknown.*' の内容を 'messages.pot' に取り込みます。

### import_mismatch.py
'mismatch.*' の内容を 'messages.pot' に取り込みます。

### delete_extracted_comments.py
'messages.pot' に含まれる extracted-comments を全て削除します。
extracted-comments には未知のキーが検出される直前の操作履歴が含まれています。

### import_pot.py
'messages.pot' の内容を 全ての'<locale_code>.po' に取り込みます。

### format_po_files.py（コマンド名: format-po）
'<locale_code>.po' のフォーマットを修正します。