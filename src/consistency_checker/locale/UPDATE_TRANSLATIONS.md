# 翻訳の更新方法 / How to Update Translations

このツール自身が国際化（i18n）に対応しており、POファイルを使用して翻訳を管理しています。

## サポート言語 / Supported Languages

- **英語 (English)** - デフォルト言語
- **日本語 (Japanese)** - 日本語
- **中国語 (Chinese)** - 中文
- **ロシア語 (Russian)** - Русский

## 翻訳ファイルの場所 / Translation File Locations

```
src/consistency_checker/locale/
├── messages.pot                    # テンプレートファイル
├── en/LC_MESSAGES/
│   ├── messages.po                 # 英語翻訳
│   └── messages.mo                 # コンパイル済み（自動生成）
├── ja/LC_MESSAGES/
│   ├── messages.po                 # 日本語翻訳
│   └── messages.mo                 # コンパイル済み（自動生成）
├── zh/LC_MESSAGES/
│   ├── messages.po                 # 中国語翻訳
│   └── messages.mo                 # コンパイル済み（自動生成）
└── ru/LC_MESSAGES/
    ├── messages.po                 # ロシア語翻訳
    └── messages.mo                 # コンパイル済み（自動生成）
```

## 翻訳の更新手順 / How to Update Translations

### 1. POTファイルの更新 / Update POT Template

新しい翻訳可能な文字列を追加した場合：

```bash
# GUI コードから翻訳可能な文字列を抽出
cd src/consistency_checker
xgettext --language=Python --keyword=_ --output=locale/messages.pot gui.py
```

### 2. POファイルの更新 / Update PO Files

```bash
# 各言語のPOファイルを更新
cd src/consistency_checker/locale

# 日本語
msgmerge --update ja/LC_MESSAGES/messages.po messages.pot

# 中国語
msgmerge --update zh/LC_MESSAGES/messages.po messages.pot

# ロシア語
msgmerge --update ru/LC_MESSAGES/messages.po messages.pot
```

### 3. 翻訳の編集 / Edit Translations

POファイルをテキストエディタで開いて翻訳を編集：

```po
msgid "Start Check"
msgstr "チェック開始"  # 日本語の場合
```

### 4. MOファイルのコンパイル / Compile MO Files

```bash
# Python を使用してコンパイル
cd src
python -c "from consistency_checker.i18n import compile_po_files; compile_po_files()"

# または msgfmt を直接使用
cd src/consistency_checker/locale
msgfmt -o ja/LC_MESSAGES/messages.mo ja/LC_MESSAGES/messages.po
msgfmt -o zh/LC_MESSAGES/messages.mo zh/LC_MESSAGES/messages.po
msgfmt -o ru/LC_MESSAGES/messages.mo ru/LC_MESSAGES/messages.po
```

## 新しい言語の追加 / Adding New Languages

### 1. ディレクトリ構造の作成

```bash
cd src/consistency_checker/locale
mkdir -p <lang_code>/LC_MESSAGES
```

### 2. i18n.py の更新

`AVAILABLE_LANGUAGES` 辞書に新しい言語を追加：

```python
AVAILABLE_LANGUAGES = {
    'en': 'English',
    'ja': '日本語',
    'zh': '中文',
    'ru': 'Русский',
    'fr': 'Français',  # 新しい言語の例
}
```

### 3. POファイルの初期化

```bash
# POTファイルから新しい言語のPOファイルを作成
msginit --locale=<lang_code> --input=messages.pot --output=<lang_code>/LC_MESSAGES/messages.po
```

### 4. 翻訳とコンパイル

上記の手順3と4に従って翻訳とコンパイルを実行。

## 開発のヒント / Development Tips

### 翻訳可能な文字列のマーキング

GUIコードで翻訳可能な文字列は `_()` 関数でマークする：

```python
# 正しい例
self.button = QPushButton(_("Start Check"))
self.title = _("PO File Consistency Checker")

# 間違った例
self.button = QPushButton("Start Check")  # ハードコード
```

### フォーマット文字列

プレースホルダーを含む文字列：

```python
# 正しい例
message = _("Check complete - Errors: {errors}, Warnings: {warnings}")
result = message.format(errors=5, warnings=2)

# 間違った例
message = f"Check complete - Errors: {errors}, Warnings: {warnings}"  # 翻訳不可
```

### デバッグ

翻訳がうまく動作しない場合：

1. MOファイルが正しくコンパイルされているか確認
2. 翻訳キーが正確か確認（大文字小文字、スペースなど）
3. 言語コードが正しいか確認

## ツール要件 / Tool Requirements

- **msgfmt**: POファイルのコンパイルに必要
- **xgettext**: 翻訳可能文字列の抽出に必要
- **msgmerge**: POファイルの更新に必要

macOSでは：
```bash
brew install gettext
```

Ubuntuでは：
```bash
sudo apt-get install gettext
```