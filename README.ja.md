# SmartGit ローカライズ - 翻訳ファイル

このリポジトリには、Git クライアント SmartGit の翻訳ファイルが含まれています。

https://www.syntevo.com/smartgit/download/

# SmartGit のローカライズの仕組み

SmartGit の多くの UI 文字列（'strings'）は、ソースコード内に直接記述されており、一部は動的に生成されます。主要な UI コンポーネントには固有のキーが割り当てられており、このキーを使用してローカライズファイルから翻訳を検索します。

`./po` ディレクトリには、現在把握されているすべてのキーと英語の原文を含む `messages.pot` ファイル（マスターマッピング）があります。各言語のローカライズファイル `<locale_code>.po` にも同様のキーと原文が含まれ、それぞれの翻訳（または未翻訳）が記述されています。

マスターマッピングは定期的に SmartGit のソースコードから更新されます。`<locale_code>.po` ファイルは主にコントリビューターによって更新され、その後私たちが SmartGit のソースコードと同期します。

最新プレビュー版の翻訳は `main` ブランチで管理され、各安定版には `smartgit-25.1` のようなバージョン別のブランチが用意されています。

> [!NOTE]
> SmartGit 24.1 から、ローカライズファイルの形式を標準的な PO 形式に移行しました。以前のバージョンについては、各ブランチの README.md を参照してください。

# 貢献方法

SmartGit のローカライズには、以下の2つの方法で貢献できます。

* **翻訳への協力**: ご自身の言語の `<locale_code>.po` ファイルに翻訳を追加したり改善する
* **キー収集への協力**: まだ `messages.pot` ファイルに含まれていないキーを収集する

## 事前準備

### リポジトリのクローン

いずれの貢献方法の場合も、このリポジトリをフォークしてクローンし、適切なブランチを使用する必要があります。

1. SmartGit の最新リリース版または現在のプレビュー版を使用します
1. リポジトリをフォークします
1. フォークしたリポジトリをクローンします（例: `C:\temp\smartgit-translations`）
1. 適切なブランチをチェックアウトします
   1. `main` - 現在のプレビュー版の翻訳が含まれています
   1. `smartgit-...` - 対応する SmartGit バージョンの翻訳が含まれています

> [!IMPORTANT]
> プルリクエストは、これら2つのバージョンのいずれかに対してのみ送信してください。

### 実際の GUI で翻訳結果を確認する設定

翻訳のみを行う場合は必須ではありませんが、この設定により、実際の GUI 上でどのように翻訳が表示されるかを確認しながら作業できます。

1. SmartGit の設定ディレクトリを開きます（Help → About SmartGit → Information タブ）
1. SmartGit を終了します（Repository → Exit）
1. 設定ディレクトリ内の `smartgit.properties` に以下の行を追加します:
   ```
   smartgit.i18n=<locale>
   smartgit.debug.i18n.development=<path-to-localization-directory>
   ```
   `<locale>` には `zh_CN` や `ja_JP` などのロケールコードを指定します。

   例: リポジトリを上記の場所にクローンし、`zh_CN` の翻訳を行う場合
   ```
   smartgit.i18n=zh_CN
   smartgit.debug.i18n.development=C\:/temp/smartgit-translations.git/po
   ```

`smartgit.properties` には、未翻訳箇所や未知のキーを GUI 上にマーク表示するオプションもあります。これはキー収集時に特に役立ちますので、必要に応じて有効にしてください。詳細は [About smartgit.properties](docs/about_smartgit_properties.md) を参照してください。

> [!IMPORTANT]
> キー収集を行う場合、この設定は必須です。

### エディターの準備

po ファイルは通常のテキストエディターでも編集できますが、以下のような翻訳支援ツールを使うと便利です。お好みのツールをご使用ください。

* [Poedit](https://poedit.net)
* [Virtaal](https://virtaal.translatehouse.org)
* [Lokalize](https://apps.kde.org/lokalize/)

## 翻訳への貢献方法

新しい翻訳はすべて歓迎します！貢献するには、以下の手順に従ってください。

### テキストエディターを使用する場合

1. 上記の準備を完了します
1. 進行中の翻訳を把握するため、オープンになっているプルリクエストを確認します
1. `<locale_code>.po` の内容を確認し、翻訳するテキストを探します
1. テキストを翻訳します。以下は説明のための例です:
   ```
   msgctxt "(wndLog|wndProject).lblStatusBarMessage:"
   msgid "Please wait ..."
   msgstr ""
   ```
   po ファイルでは、`msgctxt` がコンテキストを識別する文字列、`msgid` がキーと原文を兼ねており、翻訳されたメッセージは `msgstr` に記述します。SmartGit では、すべてのエントリに `msgctxt` と `msgid` があり、これらが内部的にキーとして使用されます。

1. `msgstr` に翻訳したメッセージを記述します。
   ```
   msgctxt "(wndLog|wndProject).lblStatusBarMessage:"
   msgid "Please wait ..."
   msgstr "请稍等..."
   ```

1. プルリクエストを送信します（例: `Chinese translation update: ` のように適切な言語名をプレフィックスとして付けてください）

> [!IMPORTANT]
> プルリクエストに、改行コードの変更や並べ替えなどの不要な変更が含まれないようにしてください（エントリは自動的にソートされます）。

#### 構文の詳細

##### 未翻訳エントリ

以下は未翻訳エントリの例です。`msgstr` が空の文字列になっているエントリです。

```
msgctxt "(wndLog|wndProject).lblStatusBarMessage:"
msgid "Please wait ..."
msgstr ""
```

##### 翻訳が不要なエントリ

製品名のように原文のまま残すべき項目は、`msgstr` を `msgid` と同じ文字列に設定します。

```
msgctxt "dlgSgHostingProviderEdit.tle:"
msgid "GitHub"
msgstr "GitHub"
```

##### 確認または修正が必要なエントリ

何らかの理由で確認が必要と判断されたエントリには、`fuzzy` フラグが付けられます。
また、原文が変更されたエントリには、以前の原文が `#| msgid` で始まるコメント行に記述されます。内容を確認し、必要に応じて `msgstr` を調整してください。

```
#, fuzzy
#| msgid "Edit the effective repository settings"
msgctxt "dlgSgRepositorySettings.hdl"
msgid "Edit the repository settings"
msgstr "编辑有效的仓库设置"
```

確認または修正が完了したら、`fuzzy` フラグと以前の原文の行を削除します。

```
msgctxt "dlgSgRepositorySettings.hdl"
msgid "Edit the repository settings"
msgstr "编辑仓库设置"
```

### 翻訳支援ソフトウェアを使用する場合（Poedit の例）

1. 上記の準備を完了します
1. 進行中の翻訳を把握するため、オープンになっているプルリクエストを確認します
1. Poedit を開き、ワードラップを無効に設定します
1. `<locale_code>.po` を開いて翻訳を進めます
1. Poedit の「Needs work」は、ファイル内の `fuzzy` フラグに対応します。確認後はフラグを削除します。
1. ファイルの差分を確認し、Poedit によってヘッダーが変更されている場合は元に戻します。
1. プルリクエストを送信します（例: `Chinese translation update: ` のように適切な言語名をプレフィックスとして付けてください）

> [!IMPORTANT]
> * 不要な変更によるコンフリクトを避けるため、コミット前に必ずヘッダーの変更を元に戻してください。
> * エディターのワードラップ設定を変更して、単語を折り返さないようにしてください。
>   * Poedit の場合: File → Preferences... から Advanced タブを開き、「Preserving formatting of existing files」をオンにします。
>   * それでも単語の折り返しが変更された場合は、「Preserving formatting of existing files」をオフにし、「Wrap at」を 1000 などの十分に大きな値に設定してから、po ファイルを上書き保存してください。

## キー収集への貢献

SmartGit はテキストを動的に生成するため、マスターマッピングには*すべて*のキーが含まれているわけではなく、私たちとコントリビューターが*現時点で把握している*キーのみが含まれています。キー収集に協力するには:

1. 上記の準備（実際の GUI で翻訳結果を確認する設定）を完了します
1. SmartGit を再起動します
1. SmartGit は、指定した `development` ディレクトリにいくつかの新しいファイルを作成します。最も重要なものは:
   1. `unknown.*` - まだ未知のキー、つまりマスターマッピングファイルに一致するエントリがないキー
   1. `mismatch.*` - 既知のキーだが、コードとマスターマッピングファイルの間で原文に違いがあるもの
   1. これら2つのファイルは無視してかまいません。つまり「あなたが所有する」ファイルです
1. SmartGit をシャットダウンします
1. 時々この2つのファイルを確認し、圧縮して `smartgit@syntevo.com` に送信します
   1. メールの件名は「Language mappings: new/changed keys」としてください
1. **2つのファイルをすべて削除**して、新しいキーの収集を再開します
1. SmartGit を再起動し、新しいキーの収集を続けます

## レビューによる貢献

各言語のネイティブスピーカーによるレビューが必要です。
オープンになっているプルリクエストや `mapping.dev` の既存翻訳には、改善の余地がある場合があります。
既存の翻訳を改善するためのレビューコメントや提案をお待ちしています！
