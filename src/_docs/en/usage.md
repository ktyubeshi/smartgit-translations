# Usage

## Using with uv

In an environment set up with uv, use the `uv run` command.

### Running as commands

Format PO files:
```bash
uv run format-po
```

Apply POT file contents to each language:
```bash
uv run import-pot
```

Other commands:
```bash
uv run import-unknown
uv run import-mismatch
uv run delete-extracted-comments
```

## Using with venv

### 1. Activate virtual environment

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

### 2. Run commands

With the virtual environment active:

Run as commands:
```bash
format-po
import-pot
```

Or run as Python scripts:
```bash
python format_po_files.py
python import_pot.py
```

### 3. Deactivate virtual environment

When finished:

```bash
deactivate
```

## Usage Examples for Each Command

### format-po

Format all PO files:

```bash
uv run format-po
```

### import-pot

Apply POT file changes to each language's PO file:

```bash
uv run import-pot
```

## Workflow Examples

### When new translation keys are added

1. Import unknown files
   ```bash
   uv run import-unknown
   ```

2. Apply POT file to each language
   ```bash
   uv run import-pot
   ```

3. Format PO files
   ```bash
   uv run format-po
   ```

### When fixing mismatched keys

1. Import mismatch files
   ```bash
   uv run import-mismatch
   ```

2. Follow the same steps as above

## Notes

- Run all commands from the `src` directory
- File paths are automatically detected, so arguments are usually not needed
- It's recommended to commit changes in Git before running commands