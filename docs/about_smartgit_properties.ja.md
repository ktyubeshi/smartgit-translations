<!--
  source: docs/about_smartgit_properties.md
  source-commit: <commit-id>
  synced-at: 2026-05-07
-->
# smartgit.properties について

`smartgit.properties` は、SmartGit の設定ディレクトリに置かれている設定ファイルです。
通常、このファイルには Low-level Properties の設定内容が記録されていますが、開発者および翻訳者向けに以下の特別なオプションが設けられています。
なお、このオプションの仕様は内部的な都合により変更される可能性があることに留意してください。

| #  | キー | 型 | 既定値 | 説明 |
|----|-----|------|---------|-------------|
| 1  | smartgit.i18n | string | - | 翻訳者向けのモードを有効化する場合にこの項目を作成し、ロケール識別子を指定してください。一時的に無効化するときは `false` を設定します。<br> 有効な値の例: `false`, `zh_CN`, `ja_JP`, `ru_RU` |
| 2  | smartgit.debug.i18n.development | string | - | PO/POT ファイルが格納されているディレクトリのパスを指定してください。ここで設定したディレクトリから、`smartgit.i18n` で設定されたロケール識別子に対応する翻訳ファイルが読み込まれます。 例: `ja_JP.po`|
| 3  | smartgit.debug.i18n.markTranslatable | boolean | false | まだ `messages.pot` に含まれていない翻訳可能な UI 要素の翻訳の先頭に、指定のマークを表示します。 |
| 4  | smartgit.debug.i18n.markUntranslated | boolean | false | `messages.pot` に含まれているが、まだ翻訳されていない UI 要素の翻訳の先頭に、指定のマークを表示します。 |
| 5  | smartgit.debug.i18n.markerTranslatable | string | ✨ | オプション 3 で `i18n.markTranslatable` が true の場合に表示する文字を指定します。 |
| 6  | smartgit.debug.i18n.markerUntranslated | string | ■ | オプション 4 で `i18n.markUntranslated` が true の場合に表示する文字を指定します。 |

オプション 5 と 6 を設定しても GUI 上で英語表記のまま残る文字列は、現時点では翻訳できません。翻訳可能にするには SmartGit のソースコードを変更する必要があります。
もし翻訳を希望する場合は当該箇所のスクリーンショットなどを添えてIssueを作成してください。


オプション 2 に設定するファイルパスの区切り文字はWindows環境でも `/` でなければならないことに注意してください。また、`:` は `\` でエスケープしなければなりません。
例えば `c:\dir1\dir2` は  `c\:/dir1/dir2` となります。

完全な設定例:

```smartgit.properties
smartgit.i18n=ja_JP
smartgit.debug.i18n.development=C\:/temp/smartgit-translations/po
smartgit.debug.i18n.markTranslatable=true
smartgit.debug.i18n.markUntranslated=true
smartgit.debug.i18n.markerTranslatable=✨
smartgit.debug.i18n.markerUntranslated=■

```

## smartgit.properties の格納先

`smartgit.properties` の格納先が分からない場合は、SmartGit の画面から設定ディレクトリを確認できます。

1. メニューから `Help` -> `About SmartGit` を選択します。

![Help メニューの About SmartGit](img/about_smartgit_properties/menu-help-about_smart_git.png)

2. `Information` タブを開き、`Settings Path` に表示されているディレクトリを確認します。このディレクトリに `smartgit.properties` ファイルが保存されています。

![About SmartGit ダイアログの Settings Path](img/about_smartgit_properties/dialog-about_smart_git-information-settings_path.png)

