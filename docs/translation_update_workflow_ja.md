# SmartGit 追加翻訳項目の処理手順

このメモは、SmartGit の実行ログから追加された `po/messages.pot` と `po/ja_JP.po` の項目を、公開可能な形へ整えるための手順をまとめたものです。将来自動化する場合も、この順序と判断基準を基準にします。

## 前提

- 対象ファイルは主に `po/messages.pot` と `po/ja_JP.po`。
- 追加項目はファイル末尾付近に `# DON'T EDIT, this file will be rewritten!` と `# BUILD: ...` のブロックとして入ることが多い。
- SmartGit からステージ済みの状態で追加されることがあるため、作業前に staged / unstaged の両方を見る。
- 検証には MSYS2 の gettext を使う。

```powershell
& 'C:\msys64\usr\bin\msgfmt.exe' --check --output-file=/dev/null 'po/messages.pot'
& 'C:\msys64\usr\bin\msgfmt.exe' --check --output-file=/dev/null 'po/ja_JP.po'
```

Windows で MSYS2 版 `msgfmt` を使う場合、出力先に `NUL` を指定しない。MSYS 環境ではリテラルの `NUL` ファイルができることがあるため、必ず `/dev/null` を使う。

## 1. 差分の確認

まず、対象ファイルがステージ済みか未ステージかを確認する。

```powershell
git status --short -- po/messages.pot po/ja_JP.po
git diff -- po/messages.pot
git diff --cached -- po/messages.pot
git diff -- po/ja_JP.po
git diff --cached -- po/ja_JP.po
```

`M  file` はステージ済み、` M file` は未ステージ、`MM file` は両方に差分がある状態。ステージ済みの追加を修正した場合は、最後に `git add -- <file>` でインデックスを更新する。

## 2. `messages.pot` のマスク

`messages.pot` の追加ブロックには、SmartGit の操作履歴が extracted comment として入る。コメントは翻訳時の文脈として有用なので原則残すが、ユーザ固有・環境固有・一時的な値は抽象化する。

置換例:

| 対象 | 置換後 |
|------|--------|
| `C:\Users\<user>\...\po` などの絶対パス | `<directory>` |
| リポジトリ名 | `<repository>` |
| コミット ID | `<commit_id>` |
| ブランチ名 | `<branch_name>` |
| リモート名 | `<remote_name>` |
| 一時ファイル名や収集用ファイル名 | `<file_name>` |
| 評価期限などの日付 | `<date>` |

例:

```po
#. opening smartgit.bFP@53O46I:ja_JP.po [<repository>] - Log for po/ja_JP.po@<commit_id> (smartgit.bFP@JEBXPF)
```

プロバイダー名やサービス名として固定的に表示される `GitHub`、`GitLab`、`github.com`、`Bitbucket` などは通常マスクしない。

## 3. `msgid` 内の可変値

`msgid` に具体的なブランチ名、リモート名、コミット ID などが含まれている場合は、SmartGit のプレースホルダー形式 `$1`, `$2` へ置換する。置換前の意味は `placeholder:` コメントとして残す。

例:

```po
#. placeholder: $1=<branch_name>
msgctxt "wndStd.mni:"
msgid "On $1: SmartGit: automatic stash on Edit Message."
msgstr ""
```

プレースホルダーコメントは具体値ではなく `<branch_name>`、`<commit_id>` のような抽象表記にする。

## 4. 重複項目の整理

`msgfmt --check` で duplicate message definition が出た場合は、後から追加された重複エントリを削除する。既存側にマスク済み・プレースホルダー化済みの同等項目がある場合は、既存側を残す。

よくある重複例:

- `There are no obsolete local branches.`
- `Providers`
- `Select a provider`
- `On $1: SmartGit: automatic stash on Edit Message.`

重複削除後に再度 `msgfmt --check` を実行する。

## 5. `ja_JP.po` の下訳

追加された未翻訳項目は、既存訳と用語を合わせて下訳を入れる。下訳には原則 `#, fuzzy` を付ける。

```po
#, fuzzy
msgctxt "wndLog.mni:"
msgid "Select from GitLab"
msgstr "GitLab から選択"
```

既存訳がある短い語は `rg` で確認して揃える。

```powershell
rg -n 'msgid "Refresh"|msgid "Remove"|msgid "Select a provider"|msgid "GitLab"' po/ja_JP.po
```

ブランド名、サービス名、ドメイン名は原文のままにすることが多い。

## 6. `fuzzy` フラグの扱い

- 新しく下訳した箇所は `#, fuzzy` を付ける。
- 過去訳と照合して訳語を統一済み、またはユーザが確定判断した箇所は `fuzzy` を外す。
- `#, fuzzy` は対象エントリの `msgctxt` / `msgid` より前に置く。

## 7. 検証

編集後は必ず以下を実行する。

```powershell
& 'C:\msys64\usr\bin\msgfmt.exe' --check --output-file=/dev/null 'po/messages.pot'
& 'C:\msys64\usr\bin\msgfmt.exe' --check --output-file=/dev/null 'po/ja_JP.po'
git diff --check -- po/messages.pot po/ja_JP.po
git diff --cached --check -- po/messages.pot po/ja_JP.po
```

追加差分に機密情報が残っていないかも確認する。

```powershell
git diff --unified=0 -- po/messages.pot |
  rg -n '^\+.*(C:\\Users\\[^\\]+|<actual_repository_name>|[0-9a-f]{7,40}|unknown\.[A-Za-z0-9_]+)'

git diff --cached --unified=0 -- po/messages.pot |
  rg -n '^\+.*(C:\\Users\\[^\\]+|<actual_repository_name>|[0-9a-f]{7,40}|unknown\.[A-Za-z0-9_]+)'
```

検索結果が削除行だけに出ている場合は問題ない。追加行に出ている場合はマスク漏れ。

## 8. ステージ状態の更新

SmartGit から追加されたファイルがステージ済みだった場合、修正後に再ステージする。

```powershell
git add -- po/messages.pot
git add -- po/ja_JP.po
git status --short -- po/messages.pot po/ja_JP.po
```

`M  po/messages.pot` のように左列だけが `M` なら、変更はステージ済み。` M` や `MM` が残る場合は未ステージ差分も確認する。

## 自動化候補

将来スクリプト化する場合は、以下を独立した処理として実装するとよい。

1. staged / unstaged の追加ブロック抽出
2. extracted comment 内のパス、リポジトリ名、コミット ID、日付、一時ファイル名のマスク
3. `msgid` 内のブランチ名・リモート名・コミット ID の `$1`, `$2` 化と `placeholder:` コメント追加
4. `msgctxt + msgid` をキーにした重複検出と後続重複の削除
5. `ja_JP.po` の未翻訳項目リストアップ
6. 既存訳検索による短い UI 語の訳語提案
7. 下訳追加時の `#, fuzzy` 付与
8. `msgfmt --check`、`git diff --check`、機密情報検索の一括実行
