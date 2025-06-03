"""チェッカーの設定"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Set, List, Dict


class CheckLevel(Enum):
    """チェックレベル"""
    STRICT = "strict"    # すべてを厳密にチェック
    NORMAL = "normal"    # 一般的なケースをチェック
    LENIENT = "lenient"  # 最小限のチェックのみ


class CheckType(Enum):
    """チェックタイプ"""
    ESCAPE_SEQUENCE = "escape_sequence"
    HTML_TAG = "html_tag"
    PLACEHOLDER = "placeholder"
    FORMAT_STRING = "format_string"


@dataclass
class CheckerConfig:
    """チェッカーの設定"""
    
    # 基本設定
    check_level: CheckLevel = CheckLevel.NORMAL
    enabled_checks: Set[CheckType] = field(default_factory=lambda: {
        CheckType.ESCAPE_SEQUENCE,
        CheckType.HTML_TAG,
        CheckType.PLACEHOLDER,
        CheckType.FORMAT_STRING
    })
    
    # エスケープシーケンス設定
    important_escape_sequences: Set[str] = field(default_factory=lambda: {
        '\\n',  # 改行
        '\\t',  # タブ
        '\\"',  # ダブルクォート
        '\\\\'  # バックスラッシュ
    })
    
    # 無視するエスケープシーケンス（警告のみ）
    warning_only_escape_sequences: Set[str] = field(default_factory=lambda: {
        '\\r',   # キャリッジリターン（OS依存）
        '\\(',   # 括弧（説明文で使用される可能性）
        '\\)',   # 括弧
        '\\*',   # アスタリスク（Markdown）
        '\\[',   # 角括弧（Markdown）
        '\\]',   # 角括弧
        '\\|',   # パイプ（テーブル）
        '\\/',   # スラッシュ
        '\\u',   # Unicode文字
        '\\{',   # 波括弧
        '\\}'    # 波括弧
    })
    
    # 言語特有の設定
    language_specific_ignores: Dict[str, Set[str]] = field(default_factory=lambda: {
        'ja': {'\\（', '\\）', '\\「', '\\」', '\\『', '\\』'},  # 日本語の全角文字
        'zh': {'\\（', '\\）', '\\「', '\\」', '\\【', '\\】'},  # 中国語の全角文字
    })
    
    # HTMLタグ設定
    structural_html_tags: Set[str] = field(default_factory=lambda: {
        'p', 'div', 'span', 'b', 'i', 'u', 'strong', 'em',
        'a', 'br', 'hr', 'img', 'table', 'tr', 'td', 'th',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'pre', 'code', 'tt', 'blockquote'
    })
    
    # 属性を無視するタグ
    ignore_attributes_tags: Set[str] = field(default_factory=lambda: {
        'a',    # href属性は翻訳で変更される可能性
        'img',  # src, alt属性は翻訳で変更される可能性
    })
    
    # プレースホルダー設定
    placeholder_patterns: List[str] = field(default_factory=lambda: [
        r'%[diouxXeEfFgGaAcsp%]',     # C形式
        r'%\d+\$[diouxXeEfFgGaAcsp]', # 位置指定C形式
        r'\{[^}]+\}',                  # Python/Java形式
        r'\$\{[^}]+\}',                # テンプレート形式
        r'#\{[^}]+\}',                 # Ruby形式
    ])
    
    # エラーレポート設定
    max_context_length: int = 50  # エラー前後の文字数
    show_suggestions: bool = True  # 修正提案を表示
    export_errors: bool = True     # エラーをファイルに出力
    
    # 出力設定
    output_language: str = 'en'    # 出力言語
    add_fuzzy_flag: bool = True    # fuzzyフラグを追加
    add_checker_comment: bool = True  # チェッカーコメントを追加
    checker_comment_prefix: str = '[Checker]'
    
    def get_ignored_sequences_for_language(self, language: str) -> Set[str]:
        """言語に応じた無視するエスケープシーケンスを取得"""
        ignored = self.warning_only_escape_sequences.copy()
        if language in self.language_specific_ignores:
            ignored.update(self.language_specific_ignores[language])
        return ignored
    
    def should_check(self, check_type: CheckType) -> bool:
        """指定されたチェックタイプが有効かどうか"""
        return check_type in self.enabled_checks
    
    @classmethod
    def strict(cls) -> 'CheckerConfig':
        """厳密なチェック設定"""
        config = cls(check_level=CheckLevel.STRICT)
        config.warning_only_escape_sequences = set()  # すべてエラーとして扱う
        return config
    
    @classmethod
    def lenient(cls) -> 'CheckerConfig':
        """寛容なチェック設定"""
        config = cls(check_level=CheckLevel.LENIENT)
        config.enabled_checks = {CheckType.ESCAPE_SEQUENCE, CheckType.HTML_TAG}
        config.important_escape_sequences = {'\\n', '\\t'}  # 最小限のみ
        return config