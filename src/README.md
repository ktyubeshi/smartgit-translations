# SmartGit Translations Utilities

## Overview

The scripts found here are utility tools designed to efficiently handle the localization files of SmartGit. 

These scripts are designed to migrate localization files to the PO file format and maintain them.

The PO file format originates from GNU gettext, and is now considered one of the de facto standards for localization files, being supported by many translation support tools. 
By doing so, it is expected that the use of many translation support tools will be possible, leading to improvements in translation efficiency and quality.

Translation support tools such as Poedit, Virtaal, and Lokalize are expected to be used.

## Scripts

For detailed information about each script, see [_docs/en/scripts.md](_docs/en/scripts.md).

### Main Scripts

- **format-po**: Format PO files
- **import-pot**: Import POT file content to all language PO files
- **import-unknown**: Import unknown keys to POT file
- **import-mismatch**: Import mismatched keys to POT file
- **delete-extracted-comments**: Delete extracted comments


## Setup

This project can be set up in two ways:
* Using uv (recommended: fast and easy management after initial setup)
* Using Python standard venv

### Method 1: Using uv

[uv](https://docs.astral.sh/uv/) is a fast Python package manager.

Install uv (macOS/Linux):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install uv (Windows):
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Setup:
```bash
cd <Repository_root>/src
uv sync
```

For details → [Setup with uv](_docs/en/setup_uv.md)

### Method 2: Using Python standard venv

Traditional method using Python virtual environment.

```bash
cd <Repository_root>/src
python -m venv .venv
```

Activate virtual environment (macOS/Linux):
```bash
source .venv/bin/activate
```

Activate virtual environment (Windows):
```bash
.venv\Scripts\activate
```

Install package:
```bash
pip install -e .
```

For details → [Setup with venv](_docs/en/setup_venv.md)

## How to Use

For detailed usage instructions → [_docs/en/usage.md](_docs/en/usage.md)

## Development

For development guidelines, testing, and code quality tools, see [Development Guide](_docs/en/development.md). 
