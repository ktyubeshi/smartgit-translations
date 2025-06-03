# Internationalization (i18n) for PO Consistency Checker

This directory contains the internationalization files for the PO Consistency Checker GUI.

## Structure

```
locale/
├── messages.pot          # Template file (source for translations)
├── en/LC_MESSAGES/
│   ├── messages.po       # English translations
│   └── messages.mo       # Compiled English translations
├── ja/LC_MESSAGES/
│   ├── messages.po       # Japanese translations
│   └── messages.mo       # Compiled Japanese translations
├── zh/LC_MESSAGES/
│   ├── messages.po       # Chinese translations
│   └── messages.mo       # Compiled Chinese translations
└── ru/LC_MESSAGES/
    ├── messages.po       # Russian translations
    └── messages.mo       # Compiled Russian translations
```

## Supported Languages

- **en** - English
- **ja** - Japanese (日本語)
- **zh** - Chinese Simplified (中文)
- **ru** - Russian (Русский)

## Usage

The i18n system is automatically initialized when the GUI starts. Users can change the language through the Settings > Language menu in the GUI.

### Programmatic Usage

```python
from consistency_checker.i18n import setup_translation

# Set up translation for Japanese
_ = setup_translation('ja')

# Use translation
translated_text = _("Settings")  # Returns "設定"
```

## Updating Translations

### For Developers

1. **Extract new strings**: When adding new translatable strings to the GUI, update the `messages.pot` template file.

2. **Update PO files**: Merge new strings into existing PO files:
   ```bash
   msgmerge --update ja/LC_MESSAGES/messages.po messages.pot
   ```

3. **Compile translations**: After updating PO files, compile them to MO files:
   ```bash
   python3 -c "from i18n import compile_po_files; compile_po_files()"
   ```

### For Translators

1. Edit the appropriate `.po` file for your language
2. Translate the `msgstr` fields
3. Compile the translations using the method above

## Technical Details

- Uses Python's built-in `gettext` module
- MO files are automatically compiled from PO files
- Fallback to English if a translation is missing
- Thread-safe translation switching

## File Formats

- **POT files**: Portable Object Template - contains the source strings
- **PO files**: Portable Object - contains translations for a specific language
- **MO files**: Machine Object - compiled binary format for fast runtime access

## Adding New Languages

1. Create a new directory: `{language_code}/LC_MESSAGES/`
2. Copy `messages.pot` to `{language_code}/LC_MESSAGES/messages.po`
3. Update the language header in the PO file
4. Translate all `msgstr` fields
5. Add the language to `AVAILABLE_LANGUAGES` in `i18n.py`
6. Compile the PO file to MO format