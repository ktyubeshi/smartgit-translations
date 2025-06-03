"""メインのチェッカークラス"""

import os
from typing import List, Optional, Tuple
from dataclasses import dataclass

import sgpo
import polib

from .config import CheckerConfig, CheckType
from .validators import (
    EscapeSequenceValidator,
    HTMLTagValidator,
    PlaceholderValidator
)
from .messages import MessageFormatter


@dataclass
class CheckResult:
    """チェック結果"""
    entry: polib.POEntry
    errors: List[str]
    warnings: List[str]
    linenum: int
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    @property
    def has_issues(self) -> bool:
        return self.has_errors or self.has_warnings


class ConsistencyChecker:
    """POファイル整合性チェッカー"""
    
    def __init__(self, config: Optional[CheckerConfig] = None):
        self.config = config or CheckerConfig()
        self.formatter = MessageFormatter(self.config.output_language)
        
        # バリデーターの初期化
        self.validators = {
            CheckType.ESCAPE_SEQUENCE: EscapeSequenceValidator(self.config),
            CheckType.HTML_TAG: HTMLTagValidator(self.config),
            CheckType.PLACEHOLDER: PlaceholderValidator(self.config),
        }
    
    def check_entry(self, entry: polib.POEntry, language: Optional[str] = None) -> Optional[CheckResult]:
        """単一のエントリをチェック"""
        # 空のmsgstrはスキップ
        if not entry.msgstr.strip():
            return None
        
        # fixedフラグがある場合はスキップ
        if hasattr(entry, 'flags') and any(flag.lower() == 'fixed' for flag in entry.flags):
            return None
        
        all_errors = []
        all_warnings = []
        
        # 各バリデーターでチェック
        for check_type, validator in self.validators.items():
            if not self.config.should_check(check_type):
                continue
            
            if check_type == CheckType.ESCAPE_SEQUENCE:
                # エスケープシーケンスは言語情報を渡す
                result = validator.validate(entry.msgid, entry.msgstr, language)
            else:
                result = validator.validate(entry.msgid, entry.msgstr)
            
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        if all_errors or all_warnings:
            return CheckResult(
                entry=entry,
                errors=all_errors,
                warnings=all_warnings,
                linenum=int(entry.linenum) if hasattr(entry, 'linenum') and entry.linenum is not None else 0
            )
        
        return None
    
    def format_check_result(self, result: CheckResult) -> str:
        """チェック結果をフォーマット"""
        lines = []
        
        # エントリ情報
        lines.append(self.formatter.get('entry_issue', linenum=result.linenum))
        
        # エラー
        if result.errors:
            lines.append(self.formatter.get('errors_section'))
            for error in result.errors:
                lines.append(f"  • {error}")
        
        # 警告（NORMALレベル以上で表示）
        if result.warnings and self.config.check_level.value != 'lenient':
            lines.append(self.formatter.get('warnings_section'))
            for warning in result.warnings:
                lines.append(f"  • {warning}")
        
        return '\n'.join(lines)
    
    def remove_checker_comments(self, tcomment: str) -> str:
        """チェッカーが追加したコメントを削除"""
        if not tcomment:
            return ''
        
        prefix = self.config.checker_comment_prefix
        lines = tcomment.split('\n')
        filtered_lines = [line for line in lines if not line.startswith(prefix)]
        return '\n'.join(filtered_lines)
    
    def update_entry_with_errors(self, entry: polib.POEntry, result: CheckResult):
        """エラーがあるエントリを更新"""
        # 既存のチェッカーコメントを削除
        entry.tcomment = self.remove_checker_comments(entry.tcomment)
        
        # fuzzyフラグを追加
        if self.config.add_fuzzy_flag and result.has_errors:
            if 'fuzzy' not in entry.flags:
                entry.flags.append('fuzzy')
        
        # エラーコメントを追加
        if self.config.add_checker_comment:
            error_lines = []
            
            if result.errors:
                error_lines.append(f"{self.config.checker_comment_prefix} {self.formatter.get('errors_section')}")
                for error in result.errors:
                    error_lines.append(f"{self.config.checker_comment_prefix}   • {error}")
            
            if result.warnings and self.config.check_level.value != 'lenient':
                if error_lines:
                    error_lines.append(f"{self.config.checker_comment_prefix}")
                error_lines.append(f"{self.config.checker_comment_prefix} {self.formatter.get('warnings_section')}")
                for warning in result.warnings:
                    error_lines.append(f"{self.config.checker_comment_prefix}   • {warning}")
            
            if error_lines:
                error_comment = '\n'.join(error_lines)
                if entry.tcomment:
                    entry.tcomment += f"\n{error_comment}"
                else:
                    entry.tcomment = error_comment
    
    def check_file(self, filepath: str) -> Tuple[List[CheckResult], polib.POFile, List[polib.POEntry]]:
        """POファイル全体をチェック"""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(self.formatter.get('file_not_found', filepath=filepath))
        
        # ファイルから言語コードを推測
        language = None
        basename = os.path.basename(filepath)
        if basename.startswith('ja') or '_ja' in basename:
            language = 'ja'
        elif basename.startswith('zh') or '_zh' in basename:
            language = 'zh'
        
        # POファイルを読み込む
        po = sgpo.pofile(filepath)
        results = []
        empty_entries = []
        
        # 各エントリをチェック
        for entry in po:
            # 空のmsgstrは別途記録
            if not entry.msgstr.strip():
                empty_entries.append(entry)
                continue
                
            result = self.check_entry(entry, language)
            if result:
                results.append(result)
                self.update_entry_with_errors(entry, result)
        
        return results, po, empty_entries
    
    def export_errors(self, results: List[CheckResult], original_filepath: str) -> Optional[str]:
        """エラーのあるエントリを別ファイルにエクスポート"""
        if not results:
            return None
        
        # エクスポート用のPOファイルを作成
        error_po = polib.POFile()
        
        # エラーのあるエントリのみを追加
        for result in results:
            if result.has_errors:  # エラーのみ（警告は除外）
                error_po.append(result.entry)
        
        # ファイル名を生成
        base, ext = os.path.splitext(original_filepath)
        export_path = f"{base}_errors{ext}"
        
        # 保存
        error_po.save(export_path)
        
        return export_path
    
    def process_file(self, filepath: str) -> bool:
        """ファイルを処理（メインエントリポイント）"""
        try:
            # チェック実行
            results, po, empty_entries = self.check_file(filepath)
            
            if results:
                # エラーを表示
                for result in results:
                    print(self.format_check_result(result))
                    print()  # 空行
                
                # POファイルを保存
                po.save()
                
                # エラーをエクスポート
                if self.config.export_errors:
                    error_results = [r for r in results if r.has_errors]
                    if error_results:
                        export_path = self.export_errors(error_results, filepath)
                        if export_path:
                            print(self.formatter.get('error_export', filepath=export_path))
                
                print(self.formatter.get('error_detected'))
                return False
            else:
                print(self.formatter.get('no_errors'))
                return True
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return False