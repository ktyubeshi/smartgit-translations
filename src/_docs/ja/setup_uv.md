# uvを使用したセットアップ

[uv](https://docs.astral.sh/uv/)は、Rustで書かれた高速なPythonパッケージマネージャーです。
pipよりも10-100倍高速で、Pythonのバージョン管理も自動で行います。

## uvのインストール

### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 別の方法

pipを使用:
```bash
pip install uv
```

Homebrewを使用 (macOS):
```bash
brew install uv
```

## プロジェクトのセットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/syntevo/smartgit-translations.git
cd smartgit-translations/src
```

### 2. 依存関係のインストール

通常の依存関係のみ:
```bash
uv sync
```

開発用の依存関係も含める場合:
```bash
uv sync --all-extras
```

> [!NOTE]
> uvは自動的に以下を行います：
> - Python 3.12以上のインストール（システムにない場合）
> - 仮想環境の作成（.venvディレクトリ）
> - 依存関係のインストール

## 動作確認

コマンドが正しくインストールされたか確認:
```bash
uv run format-po
```

## uvの利点

- **高速**: pipと比べて10-100倍高速
- **自動Python管理**: 必要なPythonバージョンを自動でダウンロード・管理
- **ロックファイル**: `uv.lock`により再現可能な環境を保証
- **標準準拠**: PEP 517/518/621に完全準拠

## トラブルシューティング

### uvコマンドが見つからない場合

インストール後、新しいターミナルセッションを開くか、以下を実行：

macOS/Linux:
```bash
source ~/.bashrc
```
または:
```bash
source ~/.zshrc
```

Windows:
PowerShellを再起動してください。

### 依存関係のインストールに失敗する場合

キャッシュをクリアして再試行:
```bash
uv cache clean
uv sync --refresh
```