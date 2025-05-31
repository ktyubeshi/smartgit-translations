# 使用方法

## uvを使用する場合

uvでセットアップした環境では、`uv run`コマンドを使用します。

### コマンドとして実行

POファイルのフォーマット:
```bash
uv run format-po
```

POTファイルの内容を各言語に反映:
```bash
uv run import-pot
```

その他のコマンド:
```bash
uv run import-unknown
uv run import-mismatch
uv run delete-extracted-comments
```

## venvを使用する場合

### 1. 仮想環境をアクティベート

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

### 2. コマンドを実行

仮想環境がアクティブな状態で：

コマンドとして実行:
```bash
format-po
import-pot
```

または、Pythonスクリプトとして実行:
```bash
python format_po_files.py
python import_pot.py
```

### 3. 仮想環境を非アクティブ化

作業が終わったら：

```bash
deactivate
```

## 各コマンドの使用例

### format-po

すべてのPOファイルをフォーマット：

```bash
uv run format-po
```

### import-pot

POTファイルの変更を各言語のPOファイルに反映：

```bash
uv run import-pot
```

## ワークフローの例

### 新しい翻訳キーが追加された場合

1. unknownファイルを取り込む
   ```bash
   uv run import-unknown
   ```

2. POTファイルを各言語に反映
   ```bash
   uv run import-pot
   ```

3. POファイルをフォーマット
   ```bash
   uv run format-po
   ```

### ミスマッチしたキーを修正する場合

1. mismatchファイルを取り込む
   ```bash
   uv run import-mismatch
   ```

2. 以降は上記と同じ手順

## 注意事項

- すべてのコマンドは`src`ディレクトリから実行してください
- ファイルパスは自動的に検出されるため、通常は引数不要です
- 実行前に必ずGitで変更をコミットすることを推奨します