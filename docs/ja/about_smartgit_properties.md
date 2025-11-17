# smartgit.properties について

`smartgit.properties` は、SmartGit の設定ディレクトリに配置される設定ファイルです。以下のオプションは、SmartGit の開発者および翻訳者向けのものであり、仕様は変更される可能性があります。

| #  | キー | 型 | デフォルト値 | 説明 |
|----|-----|------|---------|-------------|
| 1  | smartgit.debug.i18n.markTranslatable | boolean | false | `messages.pot` にまだ含まれていない UI 要素の翻訳の先頭に、特定のマークを表示します。 |
| 2  | smartgit.debug.i18n.markUntranslated | boolean | false | まだ翻訳されていない UI 要素の翻訳の先頭に、特定のマークを表示します。 |
| 3  | smartgit.debug.i18n.markerTranslatable | string | ✨ | オプション 1 で `i18n.markTranslatable` が true の場合に表示される文字を指定します。 |
| 4  | smartgit.debug.i18n.markerUntranslated | string | ■ | オプション 2 で `i18n.markUntranslated` が true の場合に表示される文字を指定します。 |

オプション 3 と 4 を設定しても、GUI 上でマーカーが付かず、且つ原文のままで表示されている文字列は、現在翻訳できない状態であり、翻訳可能にするには SmartGit のソースコードの変更が必要です。

すべての設定を明示的に記述した設定ファイルの例

```smartgit.properties
smartgit.i18n=ja_JP
smartgit.debug.i18n.development=C\:/temp/smartgit-translations/po
smartgit.debug.i18n.markTranslatable=true
smartgit.debug.i18n.markUntranslated=true
smartgit.debug.i18n.markerTranslatable=✨
smartgit.debug.i18n.markerUntranslated=■
smartgit.i18n.enable=true
```
