# SmartGit Translations Utilities

## Overview

ここにあるスクリプトは、SmartGit のローカリゼーションファイルを効率よく取り扱うためのユーティリティツールです。

SmartGitのローカリゼーションファイルをpoファイルフォーマットに移行することと、そのメンテナンスを目的として作成されました。

poファイルフォーマットはGNU gettext に由来するファイルフォーマットですが、現在ではローカリゼーションファイルのデファクトスタンダードの一つとなっており、多くの翻訳支援ツールでサポートされています。
これにより、多くの翻訳支援ツールの使用が可能になり、翻訳の効率化と品質向上ができることを期待しています。

翻訳支援ツールにはPoedit、Virtaal、Lokalizeなどが使用されることを想定しています。

## Scripts

各スクリプトの詳細については [_docs/ja/scripts.md](_docs/ja/scripts.md) を参照してください。

### 主なスクリプト

- **format-po**: POファイルのフォーマットを整形
- **import-pot**: POTファイルの内容を各言語のPOファイルに反映
- **import-unknown**: 未知のキーをPOTファイルに取り込み
- **import-mismatch**: ミスマッチしたキーをPOTファイルに取り込み
- **delete-extracted-comments**: 抽出されたコメントを削除


## セットアップ

このプロジェクトは以下の2つの方法でセットアップできます：
* uvを使用する方法（推奨：一度初期設定をすれば以降の運用が簡単になります）
* Python標準のvenvを使用する方法

### 方法1: uvを使用

[uv](https://docs.astral.sh/uv/)は高速なPythonパッケージマネージャーです。

uvのインストール（macOS/Linux）:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

uvのインストール（Windows）:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

セットアップ:
```bash
cd <Repository_root>/src
uv sync
```

詳細は → [uvを使用したセットアップ](_docs/ja/setup_uv.md)

### 方法2: Python標準のvenvを使用

従来のPython仮想環境を使用する方法です。

```bash
cd <Repository_root>/src
python -m venv .venv
```

仮想環境のアクティベート（macOS/Linux）:
```bash
source .venv/bin/activate
```

仮想環境のアクティベート（Windows）:
```bash
.venv\Scripts\activate
```

パッケージのインストール:
```bash
pip install -e .
```

詳細は → [venvを使用したセットアップ](_docs/ja/setup_venv.md)

## How to Use

### uvでセットアップした場合

```bash
uv run format-po
```

### venvでセットアップした場合

仮想環境をアクティベート後:
```bash
format-po
```

使用方法の詳細は [_docs/ja/usage.md](_docs/ja/usage.md) を参照してください。

## 開発

開発ガイドライン、テスト、コード品質ツールについては [開発ガイド](_docs/ja/development.md) を参照してください。



