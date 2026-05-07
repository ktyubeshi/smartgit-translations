# smartgit.properties について

`smartgit.properties` は、SmartGit の設定ディレクトリに置かれる設定ファイルです。以下のオプションは SmartGit の開発者および翻訳者向けであり、仕様は変更される可能性があります。

| #  | キー | 型 | 既定値 | 説明 |
|----|-----|------|---------|-------------|
| 1  | smartgit.debug.i18n.markTranslatable | boolean | false | まだ `messages.pot` に含まれていない翻訳可能な UI 要素の翻訳の先頭に、指定のマークを表示します。 |
| 2  | smartgit.debug.i18n.markUntranslated | boolean | false | `messages.pot` に含まれているが、まだ翻訳されていない UI 要素の翻訳の先頭に、指定のマークを表示します。 |
| 3  | smartgit.debug.i18n.markerTranslatable | string | ✨ | オプション 1 で `i18n.markTranslatable` が true の場合に表示する文字を指定します。 |
| 4  | smartgit.debug.i18n.markerUntranslated | string | ■ | オプション 2 で `i18n.markUntranslated` が true の場合に表示する文字を指定します。 |

オプション 3 と 4 を設定しても GUI 上で元の言語のまま残る文字列は、現時点では翻訳できません。翻訳可能にするには SmartGit のソースコードを変更する必要があります。
