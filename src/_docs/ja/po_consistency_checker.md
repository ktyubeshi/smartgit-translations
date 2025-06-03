# POファイル整合性チェッカー

## 概要

POファイル整合性チェッカーは、`msgid`と`msgstr`間の整合性を検証する改善されたツールです。従来のスクリプトの問題点を解決し、より柔軟で正確なチェックを提供します。

## 主な改善点

### 1. 文脈を考慮したチェック
- 重要なエスケープシーケンス（`\n`、`\t`など）とそうでないものを区別
- 正規表現パターンや説明文での使用を考慮
- 言語特有の文字（日本語の全角括弧など）を適切に処理

### 2. 柔軟なチェックレベル
- **Strict（厳密）**: すべてを厳密にチェック
- **Normal（通常）**: 一般的なケースをチェック（デフォルト）
- **Lenient（寛容）**: 最小限のチェックのみ

### 3. エラーと警告の区別
- 重要な問題はエラーとして報告
- 軽微な問題は警告として報告
- チェックレベルに応じて警告の表示を制御

### 4. GUI対応
- PySide6を使用した使いやすいGUIインターフェース
- リアルタイムでの結果表示
- 詳細なエラー情報の確認が可能

## 使用方法

### コマンドライン版

```bash
# 基本的な使用
uv run python check_po_consistency.py ja_JP.po

# チェックレベルを指定
uv run python check_po_consistency.py ja_JP.po --level strict

# 特定のチェックのみ実行
uv run python check_po_consistency.py ja_JP.po --check escape --check html

# オプションを指定
uv run python check_po_consistency.py ja_JP.po --no-fuzzy --no-export
```

### GUI版

```bash
# GUIを起動
uv run python check_po_consistency_gui.py
```

GUIでは以下の操作が可能です：
1. ファイルをドラッグ＆ドロップまたは参照ボタンで選択
2. チェックレベルとチェック項目を設定
3. 「チェック開始」ボタンをクリック
4. 結果をリアルタイムで確認
5. エラーの詳細を個別に確認

## コマンドライン引数

| 引数 | 説明 | デフォルト |
|------|------|------------|
| `po_file` | チェック対象のPOファイル | - |
| `-l`, `--language` | 出力言語（en/ja/zh） | ja |
| `--level` | チェックレベル（strict/normal/lenient） | normal |
| `--no-export` | エラーのエクスポートを無効化 | False |
| `--no-fuzzy` | fuzzyフラグの追加を無効化 | False |
| `--no-comment` | エラーコメントの追加を無効化 | False |
| `--check` | 実行するチェック（escape/html/placeholder） | すべて |

## チェック項目

### 1. エスケープシーケンスチェック
重要なエスケープシーケンス：
- `\n` - 改行（必須）
- `\t` - タブ（必須）
- `\"` - ダブルクォート
- `\\` - バックスラッシュ

警告のみ（通常は無視）：
- `\r` - キャリッジリターン（OS依存）
- `\(`, `\)` - 括弧（説明文で使用）
- `\*`, `\[`, `\]` - Markdown記法
- `\u` - Unicode文字指定

### 2. HTMLタグチェック
- 開始タグと終了タグの対応をチェック
- タグの入れ子構造を検証
- 属性は基本的に無視（翻訳で変更される可能性があるため）

### 3. プレースホルダーチェック
以下の形式に対応：
- C形式: `%d`, `%s`, `%f` など
- 位置指定: `%1$d`, `%2$s` など
- Python/Java形式: `{name}`, `{0}` など
- テンプレート形式: `${variable}`

## 設定のカスタマイズ

`consistency_checker/config.py`を編集することで、詳細な設定が可能です：

```python
# カスタム設定の例
config = CheckerConfig()
config.important_escape_sequences.add('\\v')  # 垂直タブを重要に
config.warning_only_escape_sequences.remove('\\r')  # \rをエラーに
config.language_specific_ignores['ja'].add('\\・')  # 中点を無視
```

## トラブルシューティング

### 多くの誤検出が発生する場合
1. チェックレベルを`lenient`に変更
2. 特定のチェックのみを有効化（`--check escape`など）
3. 言語設定が正しいか確認（日本語ファイルには`--language ja`）

### GUIが起動しない場合
PySide6が正しくインストールされているか確認：
```bash
uv pip install PySide6
```

### チェックに時間がかかる場合
大きなPOファイルの場合、GUIでプログレスバーを確認しながら処理することを推奨

## 注意事項

- このツールはPOファイルを直接更新します。実行前にバックアップを推奨
- `fixed`フラグが付いたエントリはチェックから除外されます
- 空の`msgstr`はチェック対象外です