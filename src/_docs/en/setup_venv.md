# Setup with Python Standard venv

Traditional setup method using Python's standard virtual environment feature.

## Prerequisites

### Installing Python 3.12 or Higher

1. Download from [Python official website](https://www.python.org/)
2. Run the installer
   - Windows: Check "Add Python to PATH"
   - macOS/Linux: Usually pre-installed or available via package manager

### Verify Python Version

```bash
python --version
```
or:
```bash
python3 --version
```

Ensure you have Python 3.12 or higher.

## Project Setup

### 1. Clone the repository

```bash
git clone https://github.com/syntevo/smartgit-translations.git
cd smartgit-translations/src
```

### 2. Create virtual environment

Windows:
```bash
python -m venv .venv
```

macOS/Linux:
```bash
python3 -m venv .venv
```

### 3. Activate virtual environment

#### Windows

Command Prompt:
```bash
.venv\Scripts\activate
```

PowerShell:
```bash
.venv\Scripts\Activate.ps1
```

#### macOS/Linux
```bash
source .venv/bin/activate
```

> [!TIP]
> If you see `(.venv)` in your prompt, the virtual environment is active.

### 4. Install dependencies

Upgrade pip:
```bash
pip install --upgrade pip
```

Install project in editable mode:
```bash
pip install -e .
```

Include development dependencies:
```bash
pip install -e ".[dev]"
```

## Verification

Check installed commands:
```bash
format-po
```

Or run as Python script:
```bash
python format_po_files.py
```

## Managing Virtual Environment

### Deactivate virtual environment

```bash
deactivate
```

### Delete virtual environment

To delete the virtual environment, simply remove the `.venv` directory:

Windows:
```bash
rmdir /s .venv
```

macOS/Linux:
```bash
rm -rf .venv
```

## Using the Existing setup_venv.bat (Windows)

On Windows, you can use the provided `setup_venv.bat`:

```bash
setup_venv.bat
```

This script automatically:
- Creates a virtual environment
- Activates it
- Installs dependencies
- Opens a new command prompt

## Troubleshooting

### If virtual environment activation fails (Windows PowerShell)

You may need to change the execution policy:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### If pip installation fails

In proxy environments, you may need the following configuration:

```bash
pip install --proxy http://proxy.example.com:port -e .
```