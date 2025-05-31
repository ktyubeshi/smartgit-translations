# Scripts

## Scripts for po file operations

### import_unknown.py
Imports the contents of 'unknown.*' files into 'messages.pot'.

### import_mismatch.py
Imports the contents of 'mismatch.*' files into 'messages.pot'.

### delete_extracted_comments.py
Deletes all extracted-comments contained in 'messages.pot'.
The extracted-comments contain the operation history immediately before an unknown key was detected.

### import_pot.py
Imports the contents of 'messages.pot' into all '<locale_code>.po' files.

### format_po_files.py (command name: format-po)
Fixes the formatting of '<locale_code>.po' files.