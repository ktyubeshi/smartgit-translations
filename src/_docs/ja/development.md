# 開発ガイド

このドキュメントでは、プロジェクトの開発ワークフローと使用ツールについて説明します。

## 開発環境のセットアップ

uvまたはvenvでプロジェクトをセットアップした後、開発用依存関係をインストールします：

```bash
# uvの場合
uv sync --all-extras

# venvの場合
pip install -e ".[dev]"
```

## コード品質ツール

### Ruff

Rustで書かれた高速なPythonリンター・フォーマッター。

```bash
# リントチェック
uv run ruff check .

# 自動修正
uv run ruff check . --fix

# コードフォーマット
uv run ruff format .
```

`pyproject.toml`での設定：
- 行長: 120文字
- 対象Python: 3.12
- 有効なルール: E, W, F, I, N, UP, B, C4, RUF

### mypy

Python用の静的型チェッカー。

```bash
# 型チェック実行
uv run mypy .

# 特定ファイルのチェック
uv run mypy path/to/file.py
```

`pyproject.toml`での設定：
- Pythonバージョン: 3.12
- 段階的型付け有効（allow_untyped_defs）
- 外部ライブラリの型スタブ含む

## テスト

### pytest

カバレッジ対応のテストフレームワーク。

```bash
# 全テスト実行
uv run pytest

# 詳細出力
uv run pytest -v

# 特定のテストファイルを実行
uv run pytest tests/test_sgpo.py

# カバレッジ付き実行
uv run pytest --cov=.
uv run pytest --cov=. --cov-report=html  # HTMLレポート

# 特定のテストを実行
uv run pytest tests/test_sgpo.py::TestSgpo::test_init_sgpo
```

## コミット前のワークフロー

コードをコミットする前に：

1. **コードフォーマット**
   ```bash
   uv run ruff format .
   ```

2. **リントチェック**
   ```bash
   uv run ruff check . --fix
   ```

3. **型チェック**
   ```bash
   uv run mypy .
   ```

4. **テスト実行**
   ```bash
   uv run pytest
   ```

## プロジェクト構造

```
src/
├── sgpo/              # POファイル処理コアモジュール
├── path_finder/       # パスユーティリティ
├── tests/             # テストファイル
│   └── data/         # テストデータ
├── _docs/            # ドキュメント
│   ├── ja/          # 日本語ドキュメント
│   └── en/          # 英語ドキュメント
└── *.py              # メインスクリプトファイル
```

## 新機能の追加

1. まずテストを書く（TDDアプローチ推奨）
2. 機能を実装
3. すべての品質チェックをパス
4. 必要に応じてドキュメントを更新

## 将来のツール

### ty（Astralの型チェッカー）

現在プレビュー版。設定は`pyproject.toml`にコメントアウトして含まれています。
安定版になったら以下のように使用できます：

```bash
uvx ty check .
```

## コントリビューション

1. フィーチャーブランチを作成
2. コードスタイルに従って変更
3. すべてのテストがパスすることを確認
4. プルリクエストを提出

すべてのツールは`pyproject.toml`で設定されており、開発用依存関係と共に自動的にインストールされます。