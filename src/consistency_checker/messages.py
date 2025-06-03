"""多言語メッセージ定義"""

MESSAGES = {
    'en': {
        # エラーメッセージ
        'important_escape_missing': "Missing important escape character: '{seq}' ({count} time(s))",
        'important_escape_extra': "Extra important escape character: '{seq}' ({count} time(s))",
        'escape_missing': "Missing escape character: '{seq}' ({count} time(s))",
        'escape_extra': "Extra escape character: '{seq}' ({count} time(s))",
        'html_tag_missing': "Missing HTML tag: <{tag}> ({count} time(s))",
        'html_tag_extra': "Extra HTML tag: <{tag}> ({count} time(s))",
        'html_no_opening': "Closing tag without opening tag: </{name}>",
        'html_wrong_nesting': "Incorrect tag nesting: <{opening}>... but </{closing}>",
        'html_not_closed': "Unclosed tag: <{name}>",
        'placeholder_missing': "Missing placeholder: '{ph}' ({count} time(s))",
        'placeholder_extra': "Extra placeholder: '{ph}' ({count} time(s))",
        'placeholder_order': "Placeholder order differs",
        
        # 一般メッセージ
        'entry_issue': "Entry {linenum} has issues:",
        'error_detected': "Errors detected. PO file updated with 'fuzzy' flags and error comments.",
        'no_errors': "No errors found.",
        'file_not_found': "File not found: {filepath}",
        'file_not_selected': "No PO file selected. Exiting.",
        'select_po_file': "Please select a PO file",
        'error_saving_file': "Error saving PO file.",
        'error_export': "Problematic entries exported to: {filepath}",
        
        # セクションヘッダー
        'errors_section': "=== ERRORS ===",
        'warnings_section': "=== WARNINGS ===",
        'escape_issues': "Escape Character Issues:",
        'html_issues': "HTML Tag Issues:",
        'placeholder_issues': "Placeholder Issues:",
        
        # レポート関連
        'report_notice': "This report was created based on LLM evaluation results.\nPlease note that it may contain incorrect findings (especially when context is insufficient).",
        'empty_translations': "Empty Translations",
        'empty_translations_desc': "The following entries have intentionally deleted translations:",
        'and_more': "and {count} more",
        'created': "Created",
    },
    
    'ja': {
        # エラーメッセージ
        'important_escape_missing': "重要なエスケープ文字が不足: '{seq}' ({count}個)",
        'important_escape_extra': "重要なエスケープ文字が余分: '{seq}' ({count}個)",
        'escape_missing': "エスケープ文字が不足: '{seq}' ({count}個)",
        'escape_extra': "エスケープ文字が余分: '{seq}' ({count}個)",
        'html_tag_missing': "HTMLタグが不足: <{tag}> ({count}個)",
        'html_tag_extra': "HTMLタグが余分: <{tag}> ({count}個)",
        'html_no_opening': "対応する開始タグがない終了タグ: </{name}>",
        'html_wrong_nesting': "タグの入れ子が不正: <{opening}>...に対して</{closing}>",
        'html_not_closed': "閉じられていないタグ: <{name}>",
        'placeholder_missing': "プレースホルダーが不足: '{ph}' ({count}個)",
        'placeholder_extra': "プレースホルダーが余分: '{ph}' ({count}個)",
        'placeholder_order': "プレースホルダーの順序が異なります",
        
        # 一般メッセージ
        'entry_issue': "エントリ {linenum} に問題があります:",
        'error_detected': "エラーが検出されました。'fuzzy'フラグとエラーコメントをPOファイルに追加しました。",
        'no_errors': "エラーは見つかりませんでした。",
        'file_not_found': "ファイルが見つかりません: {filepath}",
        'file_not_selected': "POファイルが選択されませんでした。終了します。",
        'select_po_file': "POファイルを選択してください",
        'error_saving_file': "POファイルの保存中にエラーが発生しました。",
        'error_export': "問題のあるエントリを以下にエクスポートしました: {filepath}",
        
        # セクションヘッダー
        'errors_section': "=== エラー ===",
        'warnings_section': "=== 警告 ===",
        'escape_issues': "エスケープ文字の問題:",
        'html_issues': "HTMLタグの問題:",
        'placeholder_issues': "プレースホルダーの問題:",
        
        # レポート関連
        'report_notice': "このレポートはLLMによる評価結果をもとに作成されました。\n(特にコンテキスト不足の場合に)誤った指摘をする場合があることに留意してください。",
        'empty_translations': "空の翻訳",
        'empty_translations_desc': "翻訳文が空白の項目は訳文が敢えて削除された箇所です:",
        'and_more': "他 {count} 件",
        'created': "作成日時",
    },
    
    'zh': {
        # エラーメッセージ
        'important_escape_missing': "缺少重要的转义字符: '{seq}' ({count}次)",
        'important_escape_extra': "多余的重要转义字符: '{seq}' ({count}次)",
        'escape_missing': "缺少转义字符: '{seq}' ({count}次)",
        'escape_extra': "多余的转义字符: '{seq}' ({count}次)",
        'html_tag_missing': "缺少HTML标签: <{tag}> ({count}次)",
        'html_tag_extra': "多余的HTML标签: <{tag}> ({count}次)",
        'html_no_opening': "没有对应开始标签的结束标签: </{name}>",
        'html_wrong_nesting': "标签嵌套错误: <{opening}>...但是</{closing}>",
        'html_not_closed': "未关闭的标签: <{name}>",
        'placeholder_missing': "缺少占位符: '{ph}' ({count}次)",
        'placeholder_extra': "多余的占位符: '{ph}' ({count}次)",
        'placeholder_order': "占位符顺序不同",
        
        # 一般メッセージ
        'entry_issue': "第 {linenum} 条目有问题:",
        'error_detected': "检测到错误。已在PO文件中添加'fuzzy'标记和错误注释。",
        'no_errors': "未发现错误。",
        'file_not_found': "找不到文件: {filepath}",
        'file_not_selected': "未选择PO文件。退出。",
        'select_po_file': "请选择一个PO文件",
        'error_saving_file': "保存PO文件时出错。",
        'error_export': "有问题的条目已导出至: {filepath}",
        
        # セクションヘッダー
        'errors_section': "=== 错误 ===",
        'warnings_section': "=== 警告 ===",
        'escape_issues': "转义字符问题:",
        'html_issues': "HTML标签问题:",
        'placeholder_issues': "占位符问题:",
        
        # レポート関連
        'report_notice': "本报告基于LLM评估结果创建。\n请注意可能包含错误的指摘（特别是在上下文不足的情况下）。",
        'empty_translations': "空翻译",
        'empty_translations_desc': "以下条目的译文被有意删除:",
        'and_more': "还有 {count} 项",
        'created': "创建时间",
    },
    
    'ru': {
        # Сообщения об ошибках
        'important_escape_missing': "Отсутствует важный экранирующий символ: '{seq}' ({count} раз(а))",
        'important_escape_extra': "Лишний важный экранирующий символ: '{seq}' ({count} раз(а))",
        'escape_missing': "Отсутствует экранирующий символ: '{seq}' ({count} раз(а))",
        'escape_extra': "Лишний экранирующий символ: '{seq}' ({count} раз(а))",
        'html_tag_missing': "Отсутствует HTML-тег: <{tag}> ({count} раз(а))",
        'html_tag_extra': "Лишний HTML-тег: <{tag}> ({count} раз(а))",
        'html_no_opening': "Закрывающий тег без открывающего: </{name}>",
        'html_wrong_nesting': "Неправильная вложенность тегов: <{opening}>... но </{closing}>",
        'html_not_closed': "Незакрытый тег: <{name}>",
        'placeholder_missing': "Отсутствует заполнитель: '{ph}' ({count} раз(а))",
        'placeholder_extra': "Лишний заполнитель: '{ph}' ({count} раз(а))",
        'placeholder_order': "Порядок заполнителей отличается",
        
        # Общие сообщения
        'entry_issue': "Запись {linenum} содержит ошибки:",
        'error_detected': "Обнаружены ошибки. PO-файл обновлён с флагами 'fuzzy' и комментариями об ошибках.",
        'no_errors': "Ошибки не найдены.",
        'file_not_found': "Файл не найден: {filepath}",
        'file_not_selected': "PO-файл не выбран. Выход.",
        'select_po_file': "Пожалуйста, выберите PO-файл",
        'error_saving_file': "Ошибка при сохранении PO-файла.",
        'error_export': "Проблемные записи экспортированы в: {filepath}",
        
        # Заголовки разделов
        'errors_section': "=== ОШИБКИ ===",
        'warnings_section': "=== ПРЕДУПРЕЖДЕНИЯ ===",
        'escape_issues': "Проблемы с экранирующими символами:",
        'html_issues': "Проблемы с HTML-тегами:",
        'placeholder_issues': "Проблемы с заполнителями:",
        
        # Отчёт
        'report_notice': "Этот отчёт создан на основе результатов оценки LLM.\nОбратите внимание, что он может содержать неверные замечания (особенно при недостатке контекста).",
        'empty_translations': "Пустые переводы",
        'empty_translations_desc': "Следующие записи имеют намеренно удалённые переводы:",
        'and_more': "и ещё {count}",
        'created': "Создано",
    }
}


class MessageFormatter:
    """メッセージフォーマッター"""
    
    def __init__(self, language: str = 'en'):
        self.language = language
        self.messages = MESSAGES.get(language, MESSAGES['en'])
    
    def get(self, key: str, **kwargs) -> str:
        """メッセージを取得してフォーマット"""
        template = self.messages.get(key, key)
        try:
            return template.format(**kwargs)
        except KeyError:
            return template