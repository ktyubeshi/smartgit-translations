"""各種バリデーター"""

import re
import html
from typing import List, Dict, Optional
from collections import Counter
from dataclasses import dataclass, field

from .config import CheckerConfig, CheckLevel
from .messages import MessageFormatter


@dataclass
class ValidationResult:
    """検証結果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    


class EscapeSequenceValidator:
    """エスケープシーケンスのバリデーター"""
    
    def __init__(self, config: CheckerConfig):
        self.config = config
        self.formatter = MessageFormatter(config.output_language)
    
    def extract_escape_sequences(self, text: str) -> List[str]:
        """エスケープシーケンスを抽出（改善版）"""
        sequences = []
        i = 0
        
        # HTMLエンティティをデコード
        text = html.unescape(text)
        
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                next_char = text[i + 1]
                
                # 特殊なエスケープシーケンスの処理
                if next_char == 'u' and i + 5 < len(text):
                    # Unicode文字（\uXXXX）
                    sequences.append(text[i:i+6])
                    i += 6
                elif next_char == 'x' and i + 3 < len(text):
                    # 16進数文字（\xXX）
                    sequences.append(text[i:i+4])
                    i += 4
                elif next_char == '\\':
                    # エスケープされたバックスラッシュ
                    sequences.append('\\\\')
                    i += 2
                else:
                    # その他のエスケープシーケンス
                    sequences.append(f'\\{next_char}')
                    i += 2
            else:
                i += 1
        
        return sequences
    
    def validate(self, msgid: str, msgstr: str, language: Optional[str] = None) -> ValidationResult:
        """エスケープシーケンスの検証"""
        if not msgstr.strip():
            return ValidationResult(is_valid=True)
        
        # エスケープシーケンスを抽出
        escapes_msgid = self.extract_escape_sequences(msgid)
        escapes_msgstr = self.extract_escape_sequences(msgstr)
        
        # カウント
        count_msgid = Counter(escapes_msgid)
        count_msgstr = Counter(escapes_msgstr)
        
        errors = []
        warnings = []
        
        # 無視するシーケンスを取得
        ignored_sequences = self.config.get_ignored_sequences_for_language(language or '')
        
        # 不足しているシーケンスをチェック
        for seq, count in count_msgid.items():
            msgstr_count = count_msgstr.get(seq, 0)
            if msgstr_count < count:
                diff = count - msgstr_count
                if seq in self.config.important_escape_sequences:
                    errors.append(self.formatter.get('important_escape_missing', seq=seq, count=diff))
                elif seq not in ignored_sequences:
                    warnings.append(self.formatter.get('escape_missing', seq=seq, count=diff))
        
        # 余分なシーケンスをチェック
        for seq, count in count_msgstr.items():
            msgid_count = count_msgid.get(seq, 0)
            if msgid_count < count:
                diff = count - msgid_count
                if seq in self.config.important_escape_sequences:
                    errors.append(self.formatter.get('important_escape_extra', seq=seq, count=diff))
                elif seq not in ignored_sequences:
                    warnings.append(self.formatter.get('escape_extra', seq=seq, count=diff))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class HTMLTagValidator:
    """HTMLタグのバリデーター"""
    
    def __init__(self, config: CheckerConfig):
        self.config = config
        self.formatter = MessageFormatter(config.output_language)
    
    def extract_html_tags(self, text: str) -> List[Dict[str, str]]:
        """HTMLタグを抽出（改善版）"""
        # HTMLエンティティをデコード
        text = html.unescape(text)
        
        tags = []
        # 完全なタグマッチング
        pattern = r'<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^>]+)?)\s*(/?)>'
        
        for match in re.finditer(pattern, text):
            closing = match.group(1)  # '/' or ''
            tag_name = match.group(2).lower()
            attributes = match.group(3)
            self_closing = match.group(4)  # '/' or ''
            
            tag_info = {
                'name': tag_name,
                'type': 'closing' if closing else ('self-closing' if self_closing else 'opening'),
                'full_tag': match.group(0),
                'position': match.start()
            }
            
            # 属性を無視しないタグの場合、属性も保存
            if tag_name not in self.config.ignore_attributes_tags and attributes:
                tag_info['attributes'] = attributes.strip()
            
            tags.append(tag_info)
        
        return tags
    
    def check_tag_structure(self, tags: List[Dict[str, str]]) -> List[str]:
        """タグ構造をチェック"""
        errors = []
        stack = []
        
        for tag in tags:
            if tag['type'] == 'opening':
                stack.append(tag)
            elif tag['type'] == 'closing':
                if not stack:
                    errors.append(self.formatter.get('html_no_opening', name=tag['name']))
                elif stack[-1]['name'] != tag['name']:
                    errors.append(self.formatter.get('html_wrong_nesting', opening=stack[-1]['name'], closing=tag['name']))
                else:
                    stack.pop()
        
        # 閉じられていないタグ
        for tag in stack:
            errors.append(self.formatter.get('html_not_closed', name=tag['name']))
        
        return errors
    
    def validate(self, msgid: str, msgstr: str) -> ValidationResult:
        """HTMLタグの検証"""
        if not msgstr.strip():
            return ValidationResult(is_valid=True)
        
        # タグを抽出
        tags_msgid = self.extract_html_tags(msgid)
        tags_msgstr = self.extract_html_tags(msgstr)
        
        errors = []
        warnings = []
        
        # 構造的なタグのみをカウント
        structural_tags_msgid = [t for t in tags_msgid if t['name'] in self.config.structural_html_tags]
        structural_tags_msgstr = [t for t in tags_msgstr if t['name'] in self.config.structural_html_tags]
        
        # タグ名とタイプでカウント
        def count_tags(tags):
            counter = Counter()
            for tag in tags:
                key = f"{tag['type']}:{tag['name']}"
                counter[key] += 1
            return counter
        
        count_msgid = count_tags(structural_tags_msgid)
        count_msgstr = count_tags(structural_tags_msgstr)
        
        # 不足・余分なタグをチェック
        all_keys = set(count_msgid.keys()) | set(count_msgstr.keys())
        for key in all_keys:
            msgid_count = count_msgid.get(key, 0)
            msgstr_count = count_msgstr.get(key, 0)
            
            if msgid_count != msgstr_count:
                tag_type, tag_name = key.split(':')
                if msgid_count > msgstr_count:
                    errors.append(self.formatter.get('html_tag_missing', tag=f"{'' if tag_type == 'opening' else '/'}{tag_name}", count=msgid_count - msgstr_count))
                else:
                    errors.append(self.formatter.get('html_tag_extra', tag=f"{'' if tag_type == 'opening' else '/'}{tag_name}", count=msgstr_count - msgid_count))
        
        # 構造チェック（NORMALレベル以上）
        if self.config.check_level.value in ['normal', 'strict']:
            msgid_structure_errors = self.check_tag_structure(tags_msgid)
            msgstr_structure_errors = self.check_tag_structure(tags_msgstr)
            
            if msgstr_structure_errors and not msgid_structure_errors:
                errors.extend(msgstr_structure_errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class PlaceholderValidator:
    """プレースホルダーのバリデーター"""
    
    def __init__(self, config: CheckerConfig):
        self.config = config
        self.formatter = MessageFormatter(config.output_language)
    
    def extract_placeholders(self, text: str) -> List[str]:
        """プレースホルダーを抽出"""
        placeholders = []
        
        for pattern in self.config.placeholder_patterns:
            matches = re.findall(pattern, text)
            placeholders.extend(matches)
        
        return placeholders
    
    def validate(self, msgid: str, msgstr: str) -> ValidationResult:
        """プレースホルダーの検証"""
        if not msgstr.strip():
            return ValidationResult(is_valid=True)
        
        placeholders_msgid = self.extract_placeholders(msgid)
        placeholders_msgstr = self.extract_placeholders(msgstr)
        
        # 完全一致をチェック（順序も重要）
        if placeholders_msgid != placeholders_msgstr:
            errors = []
            
            # カウントチェック
            count_msgid = Counter(placeholders_msgid)
            count_msgstr = Counter(placeholders_msgstr)
            
            for ph, count in count_msgid.items():
                msgstr_count = count_msgstr.get(ph, 0)
                if msgstr_count < count:
                    errors.append(self.formatter.get('placeholder_missing', ph=ph, count=count - msgstr_count))
            
            for ph, count in count_msgstr.items():
                msgid_count = count_msgid.get(ph, 0)
                if msgid_count < count:
                    errors.append(self.formatter.get('placeholder_extra', ph=ph, count=count - msgid_count))
            
            # 順序チェック（STRICTレベル）
            warnings = []
            if self.config.check_level == CheckLevel.STRICT:
                if set(placeholders_msgid) == set(placeholders_msgstr) and placeholders_msgid != placeholders_msgstr:
                    warnings.append(self.formatter.get('placeholder_order'))
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
        
        return ValidationResult(is_valid=True)