# Setup with uv

[uv](https://docs.astral.sh/uv/) is a fast Python package manager written in Rust.
It's 10-100 times faster than pip and automatically manages Python versions.

## Installing uv

### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Alternative methods

Using pip:
```bash
pip install uv
```

Using Homebrew (macOS):
```bash
brew install uv
```

## Project Setup

### 1. Clone the repository

```bash
git clone https://github.com/syntevo/smartgit-translations.git
cd smartgit-translations/src
```

### 2. Install dependencies

Regular dependencies only:
```bash
uv sync
```

Include development dependencies:
```bash
uv sync --all-extras
```

> [!NOTE]
> uv automatically:
> - Installs Python 3.12 or higher (if not present on your system)
> - Creates a virtual environment (.venv directory)
> - Installs dependencies

## Verification

Verify that commands are installed correctly:
```bash
uv run format-po
```

## Advantages of uv

- **Fast**: 10-100 times faster than pip
- **Automatic Python management**: Automatically downloads and manages required Python versions
- **Lock file**: `uv.lock` ensures reproducible environments
- **Standards compliant**: Fully compliant with PEP 517/518/621

## Troubleshooting

### If uv command is not found

After installation, open a new terminal session or run:

macOS/Linux:
```bash
source ~/.bashrc
```
or:
```bash
source ~/.zshrc
```

Windows:
Restart PowerShell.

### If dependency installation fails

Clear cache and retry:
```bash
uv cache clean
uv sync --refresh
```