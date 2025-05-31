# Python標準のvenvを使用したセットアップ

Python標準の仮想環境機能を使用した従来のセットアップ方法です。

## 前提条件

### Python 3.12以上のインストール

1. [Python公式サイト](https://www.python.org/)からダウンロード
2. インストーラーを実行
   - Windows: "Add Python to PATH"にチェックを入れる
   - macOS/Linux: 通常はプリインストールされているか、パッケージマネージャーで利用可能

### Pythonバージョンの確認

```bash
python --version
```
または:
```bash
python3 --version
```

Python 3.12以上であることを確認してください。

## プロジェクトのセットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/syntevo/smartgit-translations.git
cd smartgit-translations/src
```

### 2. 仮想環境の作成

Windows:
```bash
python -m venv .venv
```

macOS/Linux:
```bash
python3 -m venv .venv
```

### 3. 仮想環境のアクティベート

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
> プロンプトに `(.venv)` が表示されれば、仮想環境がアクティブになっています。

### 4. 依存関係のインストール

pipをアップグレード:
```bash
pip install --upgrade pip
```

プロジェクトを編集可能モードでインストール:
```bash
pip install -e .
```

開発用の依存関係も含める場合:
```bash
pip install -e ".[dev]"
```

## 動作確認

インストールされたコマンドの確認:
```bash
format-po
```

または、Pythonスクリプトとして実行:
```bash
python format_po_files.py
```

## 仮想環境の管理

### 仮想環境の非アクティブ化

```bash
deactivate
```

### 仮想環境の削除

仮想環境を削除したい場合は、`.venv`ディレクトリを削除するだけです：

Windows:
```bash
rmdir /s .venv
```

macOS/Linux:
```bash
rm -rf .venv
```

## 既存のsetup_venv.batを使用する方法（Windows）

Windows環境では、提供されている`setup_venv.bat`を使用することもできます：

```bash
setup_venv.bat
```

このスクリプトは自動的に：
- 仮想環境を作成
- アクティベート
- 依存関係をインストール
- 新しいコマンドプロンプトを開く

## トラブルシューティング

### 仮想環境のアクティベートに失敗する場合（Windows PowerShell）

実行ポリシーの変更が必要な場合があります：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### pipのインストールに失敗する場合

プロキシ環境下では以下の設定が必要な場合があります：

```bash
pip install --proxy http://proxy.example.com:port -e .
```