#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
POファイル整合性チェッカー CLI
------------------------------

改善されたPOファイル整合性チェッカーのコマンドラインインターフェース
"""

import argparse
import sys
import os

from tkinter import Tk, filedialog

from .checker import ConsistencyChecker
from .config import CheckerConfig
from .messages import MessageFormatter


def parse_arguments():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description='POファイル内のmsgidとmsgstr間の整合性をチェックします',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
チェックレベル:
  strict  - すべてを厳密にチェック
  normal  - 一般的なケースをチェック（デフォルト）
  lenient - 最小限のチェックのみ

例:
  %(prog)s ja_JP.po --language ja
  %(prog)s translations.po --level strict
  %(prog)s --no-export --no-fuzzy
"""
    )
    
    parser.add_argument(
        'po_file',
        nargs='?',
        help='チェックするPOファイルへのパス'
    )
    
    parser.add_argument(
        '-l', '--language',
        choices=['en', 'ja', 'zh'],
        default='ja',
        help='出力メッセージの言語（デフォルト: ja）'
    )
    
    parser.add_argument(
        '--level',
        choices=['strict', 'normal', 'lenient'],
        default='normal',
        help='チェックレベル（デフォルト: normal）'
    )
    
    parser.add_argument(
        '--no-export',
        action='store_true',
        help='エラーのあるエントリを別ファイルにエクスポートしない'
    )
    
    parser.add_argument(
        '--no-fuzzy',
        action='store_true',
        help='エラーがあってもfuzzyフラグを追加しない'
    )
    
    parser.add_argument(
        '--no-comment',
        action='store_true',
        help='エラーコメントを追加しない'
    )
    
    parser.add_argument(
        '--check',
        action='append',
        choices=['escape', 'html', 'placeholder'],
        help='実行するチェックタイプを指定（複数指定可）'
    )
    
    return parser.parse_args()


def select_file_dialog(language: str) -> str:
    """ファイル選択ダイアログを表示"""
    formatter = MessageFormatter(language)
    
    root = Tk()
    root.withdraw()
    
    filepath = filedialog.askopenfilename(
        title=formatter.get('select_po_file'),
        filetypes=[('PO files', '*.po'), ('All files', '*.*')]
    )
    
    root.update()
    root.destroy()
    
    return filepath


def create_config_from_args(args) -> CheckerConfig:
    """コマンドライン引数から設定を作成"""
    # レベルに応じた基本設定
    if args.level == 'strict':
        config = CheckerConfig.strict()
    elif args.level == 'lenient':
        config = CheckerConfig.lenient()
    else:
        config = CheckerConfig()
    
    # 個別の設定を上書き
    config.output_language = args.language
    config.export_errors = not args.no_export
    config.add_fuzzy_flag = not args.no_fuzzy
    config.add_checker_comment = not args.no_comment
    
    # チェックタイプの指定
    if args.check:
        from .config import CheckType
        enabled_checks = set()
        
        for check in args.check:
            if check == 'escape':
                enabled_checks.add(CheckType.ESCAPE_SEQUENCE)
            elif check == 'html':
                enabled_checks.add(CheckType.HTML_TAG)
            elif check == 'placeholder':
                enabled_checks.add(CheckType.PLACEHOLDER)
        
        config.enabled_checks = enabled_checks
    
    return config


def main():
    """メインエントリポイント"""
    args = parse_arguments()
    
    # POファイルのパスを取得
    po_filepath = args.po_file
    if not po_filepath:
        po_filepath = select_file_dialog(args.language)
        if not po_filepath:
            formatter = MessageFormatter(args.language)
            print(formatter.get('file_not_selected'))
            sys.exit(1)
    
    # ファイルの存在確認
    if not os.path.isfile(po_filepath):
        formatter = MessageFormatter(args.language)
        print(formatter.get('file_not_found', filepath=po_filepath))
        sys.exit(1)
    
    # 設定を作成
    config = create_config_from_args(args)
    
    # チェッカーを実行
    checker = ConsistencyChecker(config)
    success = checker.process_file(po_filepath)
    
    # 終了コード
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()