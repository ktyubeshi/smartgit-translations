"""国際化（i18n）サポート"""

import os
import sys
import gettext
from pathlib import Path
from typing import Dict, Callable

# 利用可能な言語
AVAILABLE_LANGUAGES = {
    'en': 'English',
    'ja': '日本語',
    'zh': '中文',
    'ru': 'Русский'
}

# デフォルト言語
DEFAULT_LANGUAGE = 'en'

# モジュールレベルの翻訳関数
_translate: Callable[[str], str] = lambda x: x


def get_locale_dir() -> Path:
    """ロケールディレクトリのパスを取得"""
    current_dir = Path(__file__).parent
    return current_dir / 'locale'


def setup_translation(language: str = None) -> Callable[[str], str]:
    """翻訳を設定し、翻訳関数を返す
    
    Args:
        language: 言語コード（en, ja, zh, ru）
        
    Returns:
        翻訳関数
    """
    global _translate
    
    if language is None:
        language = DEFAULT_LANGUAGE
    
    # 利用可能な言語をチェック
    if language not in AVAILABLE_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    try:
        # ロケールディレクトリを取得
        locale_dir = get_locale_dir()
        
        # gettextの翻訳オブジェクトを作成
        translation = gettext.translation(
            'messages',
            localedir=str(locale_dir),
            languages=[language],
            fallback=True
        )
        
        # 翻訳関数を設定
        _translate = translation.gettext
        
        # 現在のモジュールにも関数を設定
        import builtins
        builtins._ = _translate
        
        return _translate
        
    except Exception as e:
        print(f"Warning: Failed to setup translation for '{language}': {e}")
        # フォールバック：恒等関数を返す
        _translate = lambda x: x
        import builtins
        builtins._ = _translate
        return _translate


def get_current_language_name(language: str) -> str:
    """現在の言語の表示名を取得"""
    return AVAILABLE_LANGUAGES.get(language, language)


def get_available_languages() -> Dict[str, str]:
    """利用可能な言語の辞書を取得"""
    return AVAILABLE_LANGUAGES.copy()


def compile_po_files():
    """PO ファイルを MO ファイルにコンパイル
    
    Note: 
        この関数は開発時やデプロイ時に呼ばれることを想定
        実行時には通常必要ない
    """
    import subprocess
    
    locale_dir = get_locale_dir()
    
    for lang_code in AVAILABLE_LANGUAGES.keys():
        po_file = locale_dir / lang_code / 'LC_MESSAGES' / 'messages.po'
        mo_file = locale_dir / lang_code / 'LC_MESSAGES' / 'messages.mo'
        
        if po_file.exists():
            try:
                # msgfmt を使ってコンパイル
                subprocess.run([
                    'msgfmt',
                    '-o', str(mo_file),
                    str(po_file)
                ], check=True, capture_output=True)
                print(f"Compiled {po_file} -> {mo_file}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to compile {po_file}: {e}")
            except FileNotFoundError:
                # msgfmt が見つからない場合のフォールバック
                print(f"msgfmt not found. Cannot compile {po_file}")


# 初期化時にデフォルト言語を設定
setup_translation(DEFAULT_LANGUAGE)