[English](README.md) , [Simplified Chinese](README_zh-CN.md) ,[Japanese](README_ja-JP.md)

# SmartGit本地化 - SmartGit翻译文件

此存储库包含Git客户端SmartGit的翻译文件：

https://www.syntevo.com/smartgit/download/

# SmartGit的本地化如何工作？

SmartGit直接将各种UI文本（“字符串”）包含在源代码中。其中许多字符串是动态组合的。主要的UI组件分配了键，用于从映射文件中查找翻译。根`mapping`文件（“主映射”）包含所有当前已知的键及其英文原始文本。对于所有当前支持的区域设置，相应的子目录包含一个`mapping.dev`文件，其中包含适当的翻译和/或未翻译键或可能需要新翻译的键的注释。还有一个辅助`mapping.state`文件。

我们会定期从SmartGit源代码更新主映射。 `mapping.dev`和`mapping.state`将主要由贡献者更新，并由我们同步回SmartGit源代码。

对于每个SmartGit版本，都有一个单独的分支，例如`smartgit-22.1`。

# 如何贡献？

您可以通过两种方式为SmartGit的本地化做出贡献：

* **帮助翻译**：在`mapping.dev`语言映射中添加/改进翻译
* **帮助收集**：收集尚未知晓的键以填充主映射

## 准备

无论哪种情况，您都必须fork和克隆此存储库，并确保您处于正确的分支：

1.确保使用最新发布的或当前预览版本的SmartGit
1. Fork存储库
1.克隆您的fork，例如到`C:\temp\smartgit-translations.git`
1.检查适当的分支：
   1.`master`包含当前预览版本的翻译
   1.`smartgit-...`包含相应SmartGit版本的翻译

> **注意！**请只发送这两个版本之一的拉取请求。

## 翻譯幫助

歡迎每一個新的翻譯！要貢獻，請按照以下步驟：

1. 按照上述說明進行準備
1. 檢查待處理的拉取請求，以查看哪些翻譯目前正在進行中
1. 使用`mapping.dev`來確定您要翻譯的文本。
   對於需要（重新）翻譯的鍵，`mapping.dev`包含帶有`! =`標記的特殊注釋行（`#`）位於鍵行直下。
   `! =`標記之後的文本是從主映射中提取的，代表英文原文，翻譯應反映其內容。
   例如，如果尚未存在翻譯，則可能如下所示：

   ```
   dlgProgress.lbl"Please wait ..."=
   #                              !=Please wait ...
   ```

   如果已經存在翻譯，但英文原文已更改，則可能如下所示：

   ```
   dlgProgress.lbl"Please wait ..."=你得等一等
   #                              !=Please wait ...
   ```
1. 在`mapping.dev`中應用適當的翻譯並刪除注釋行。
   對於上述示例，可能如下所示：
   ```
   dlgProgress.lbl"Please wait ..."=请稍等 ...
   ```
1. 在`mapping.state`中定位您已翻譯的鍵，並更新/設置您的翻譯現在對應的英文原文。
   這應該是主映射中存在的相同英文文本，並且出現在`! =`注釋中。
   對於上述示例，可能如下所示：
   ```
   dlgProgress.lbl"Please wait ..."=Please wait ...
   ```
1. 有一個包含兩個文件的提交
   1. 在提交消息中添加前綴`Chinese translation updated: `（或適當的語言名稱）
1. 發送給我們一個拉取請求，再次使用`Chinese translation update: `前綴（或適當的語言名稱）

> **注意！** 請確保您的拉取請求不包含任何無關的格式更改（如行尾）或任何其他不必要的更改，如重新排序（我們會自動對鍵進行排序）。

### 语法详情

如果特定文本的翻译应保持与原英文文本相同，请在文本前面加上 `=`。例如：

> *.btn"OK"==OK

## 收集帮助

由于SmartGit文本的动态生成，主映射不包含*所有*键，而只包含*当前已知*键，这些键是我们的贡献者和我们收集的。要帮助收集键：

1. 按照上述说明完成准备工作。
1. 确保SmartGit未运行（Repository | Exit）。
1. 在SmartGit设置目录中找到`smartgit.properties`（参见关于对话框），并添加以下行：
   ```
   smartgit.i18n=<locale>
   smartgit.debug.i18n.development=<path-to-localization-directory>
   smartgit.debug.i18n.master=<path-to-master-mapping>
   ```
   对于上述示例目录和中文语言环境，将为：
   ```
   smartgit.i18n=zh_CN
   smartgit.debug.i18n.development=C\:/temp/smartgit-translations.git/zh-CN
   smartgit.debug.i18n.master=C\:/temp/smartgit-translations.git/mapping
   ```
1. 重新启动SmartGit
1. SmartGit现在将在指定的`development`目录中创建几个新文件，最重要的是：
   1. `unknown.*`，其中包含尚未知道的键，即尚无匹配条目的主映射文件中的键。
   1. `mismatch.code.*`，其中包含已知的键，表示代码中的当前状态。
   1. `mismatch.mapping.*`，其中包含已知的键，表示主映射中的过时状态。
   1. 请注意，所有三个文件都被忽略，因此由您“拥有”。
1. 关闭SmartGit
1. 定期检查这些文件，将其压缩并发送至`smartgit@syntevo.com`
   1. 以“语言映射：新/更改的键”为邮件前缀
1. **删除所有三个文件**，以从头开始收集新键
1. 重新启动SmartGit，继续收集新键

## 帮助审核

待处理的拉取请求和`mapping.dev`中的现有翻译有时可能需要精细化。欢迎审查意见和建议，以改善现有翻译！