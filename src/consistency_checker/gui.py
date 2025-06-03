"""PySide6を使用したGUIインターフェース"""

import sys
import os
import html
from typing import List
from dataclasses import dataclass
from datetime import datetime

import polib

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QCheckBox, QTextEdit,
    QFileDialog, QGroupBox, QProgressBar, QSplitter,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QTabWidget, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor, QAction
from PySide6.QtWidgets import QHeaderView

from .checker import ConsistencyChecker, CheckResult
from .config import CheckerConfig, CheckType
from .messages import MessageFormatter
from .i18n import setup_translation, get_available_languages


@dataclass
class GuiConfig:
    """GUI設定"""
    window_width: int = 1200
    window_height: int = 800
    font_family: str = "Segoe UI" if sys.platform == "win32" else "Hiragino Sans" if sys.platform == "darwin" else "Ubuntu"
    font_size: int = 11
    mono_font_family: str = "Consolas" if sys.platform == "win32" else "Monaco" if sys.platform == "darwin" else "Ubuntu Mono"
    mono_font_size: int = 10


class CheckerThread(QThread):
    """バックグラウンドでチェックを実行するスレッド"""
    
    progress_update = Signal(int, int)  # current, total
    result_ready = Signal(object)  # CheckResult
    finished_all = Signal(list, list)  # List[CheckResult], List[POEntry] (empty entries)
    error_occurred = Signal(str)
    
    def __init__(self, checker: ConsistencyChecker, filepath: str):
        super().__init__()
        self.checker = checker
        self.filepath = filepath
        self.results = []
        self.empty_entries = []
        self._is_cancelled = False
    
    def cancel(self):
        """処理をキャンセル"""
        self._is_cancelled = True
    
    def run(self):
        """チェックを実行"""
        try:
            results, po, empty_entries = self.checker.check_file(self.filepath)
            self.empty_entries = empty_entries
            
            # 結果を一つずつ送信
            total = len(results)
            for i, result in enumerate(results):
                if self._is_cancelled:
                    break
                
                self.progress_update.emit(i + 1, total)
                self.result_ready.emit(result)
                self.results.append(result)
            
            # POファイルを保存
            if not self._is_cancelled and results:
                po.save()
                
                # エラーをエクスポート
                if self.checker.config.export_errors:
                    error_results = [r for r in results if r.has_errors]
                    if error_results:
                        self.checker.export_errors(error_results, self.filepath)
            
            self.finished_all.emit(self.results, self.empty_entries)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class ConsistencyCheckerGUI(QMainWindow):
    """メインウィンドウ"""
    
    def __init__(self):
        super().__init__()
        self.gui_config = GuiConfig()
        # 常に厳密モードを使用
        self.checker_config = CheckerConfig.strict()
        self.checker_config.output_language = 'en'  # Default to English
        self.formatter = MessageFormatter(self.checker_config.output_language)
        
        # 翻訳システムの初期化
        self.current_language = 'en'
        self._ = setup_translation(self.current_language)
        self.current_file = None
        self.checker_thread = None
        
        # i18n設定
        self.current_language = 'en'
        self._ = setup_translation(self.current_language)
        
        # UIコンポーネントの初期化
        self.update_po_file = None
        self.add_fuzzy = None
        self.add_comment = None
        self.remove_comments_button = None
        
        self.init_ui()
        
        # 初期状態の設定
        if self.update_po_file:
            self.on_update_setting_changed(self.update_po_file.isChecked())
    
    def init_ui(self):
        """UIを初期化"""
        self.setWindowTitle(self._("PO File Consistency Checker"))
        self.resize(self.gui_config.window_width, self.gui_config.window_height)
        
        # メニューバー
        self.create_menu_bar()
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # メインタブウィジェット
        self.main_tabs = QTabWidget()
        
        # 設定タブ
        settings_tab = self.create_settings_tab()
        self.main_tabs.addTab(settings_tab, self._("Settings"))
        
        # サマリータブ
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.main_tabs.addTab(self.summary_text, self._("Summary"))
        
        # 詳細タブ
        detail_tab = self.create_detail_tab()
        self.main_tabs.addTab(detail_tab, self._("Details"))
        
        # プログレスバー（メインタブの下）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(self.main_tabs)
        
        # ステータスバー
        self.create_status_bar()
        
        # フォント設定
        self.set_fonts()
    
    def create_menu_bar(self):
        """メニューバーを作成"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu(self._("File(&F)"))
        
        open_action = QAction(self._("Open(&O)..."), self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(self._("Exit(&X)"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 設定メニュー
        settings_menu = menubar.addMenu(self._("Settings(&S)"))
        
        # 言語メニュー
        language_menu = settings_menu.addMenu(self._("Language(&L)"))
        available_languages = get_available_languages()
        for lang_code, lang_name in available_languages.items():
            action = QAction(lang_name, self)
            action.setCheckable(True)
            action.setChecked(self.current_language == lang_code)
            action.triggered.connect(lambda checked, code=lang_code: self.change_language(code))
            language_menu.addAction(action)
    
    def create_settings_tab(self) -> QWidget:
        """設定タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # ファイル選択部
        file_group = QGroupBox(self._("File Selection"))
        file_layout = QHBoxLayout()
        
        self.file_label = QLabel(self._("No file selected"))
        self.file_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }")
        file_layout.addWidget(self.file_label, 1)
        
        self.browse_button = QPushButton(self._("Browse..."))
        self.browse_button.setMinimumWidth(100)
        self.browse_button.clicked.connect(self.open_file)
        file_layout.addWidget(self.browse_button)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # チェックレベル設定は廃止（常に厳密モードを使用）
        
        # チェック項目設定
        check_items_group = self.create_check_items_group()
        layout.addWidget(check_items_group)
        
        # POファイル更新設定
        update_group = self.create_update_settings_group()
        layout.addWidget(update_group)
        
        # エクスポート設定
        export_group = self.create_export_settings_group()
        layout.addWidget(export_group)
        
        # 実行ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.check_button = QPushButton(self._("Start Check"))
        self.check_button.setEnabled(False)
        self.check_button.setMinimumHeight(40)
        self.check_button.setMinimumWidth(150)
        self.check_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.check_button.clicked.connect(self.start_check)
        button_layout.addWidget(self.check_button)
        
        layout.addLayout(button_layout)
        
        # セパレータ
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(separator)
        
        # [Checker]コメントを削除ボタン
        remove_button_layout = QHBoxLayout()
        remove_button_layout.addStretch()
        
        self.remove_comments_button = QPushButton(self._("Remove [Checker] Comments"))
        self.remove_comments_button.setEnabled(False)
        self.remove_comments_button.setMinimumHeight(40)
        self.remove_comments_button.setMinimumWidth(200)
        self.remove_comments_button.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ec971f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.remove_comments_button.clicked.connect(self.remove_checker_comments)
        remove_button_layout.addWidget(self.remove_comments_button)
        
        layout.addLayout(remove_button_layout)
        layout.addStretch()
        
        return widget
    
    
    def create_check_items_group(self) -> QGroupBox:
        """チェック項目設定グループを作成"""
        group = QGroupBox(self._("Check Items"))
        layout = QVBoxLayout()
        
        self.check_escape = QCheckBox(self._("Escape Characters"))
        self.check_escape.setChecked(True)
        self.check_escape.setToolTip(self._("Check escape sequences like \\n, \\t, \\\\"))
        layout.addWidget(self.check_escape)
        
        self.check_html = QCheckBox(self._("HTML Tags"))
        self.check_html.setChecked(True)
        self.check_html.setToolTip(self._("Check HTML tag consistency like <b>, <i>, </p>"))
        layout.addWidget(self.check_html)
        
        self.check_placeholder = QCheckBox(self._("Placeholders"))
        self.check_placeholder.setChecked(True)
        self.check_placeholder.setToolTip(self._("Check placeholders like %s, %d, {0}, ${var}"))
        layout.addWidget(self.check_placeholder)
        
        group.setLayout(layout)
        return group
    
    def create_update_settings_group(self) -> QGroupBox:
        """更新設定グループを作成"""
        group = QGroupBox(self._("PO File Update Settings"))
        layout = QVBoxLayout()
        
        self.update_po_file = QCheckBox(self._("Add check results to PO file"))
        self.update_po_file.setChecked(True)
        self.update_po_file.setToolTip(self._("Add information to entries with errors"))
        layout.addWidget(self.update_po_file)
        
        # 子項目（インデント）
        sub_layout = QVBoxLayout()
        sub_layout.setContentsMargins(20, 0, 0, 0)
        
        self.add_fuzzy = QCheckBox(self._("Add fuzzy flag"))
        self.add_fuzzy.setChecked(True)
        self.add_fuzzy.setToolTip(self._("Add fuzzy flag to entries with errors to indicate translation review is needed"))
        sub_layout.addWidget(self.add_fuzzy)
        
        self.add_comment = QCheckBox(self._("Add error comments"))
        self.add_comment.setChecked(True)
        self.add_comment.setToolTip(self._("Add specific error details as translator comments starting with [Checker]"))
        sub_layout.addWidget(self.add_comment)
        
        layout.addLayout(sub_layout)
        
        
        # 更新設定の有効/無効制御
        self.update_po_file.toggled.connect(self.on_update_setting_changed)
        
        group.setLayout(layout)
        return group
    
    def create_export_settings_group(self) -> QGroupBox:
        """エクスポート設定グループを作成"""
        group = QGroupBox(self._("Export Settings"))
        layout = QVBoxLayout()
        
        self.export_errors = QCheckBox(self._("Export entries with errors to separate file"))
        self.export_errors.setChecked(True)
        layout.addWidget(self.export_errors)
        
        export_desc = QLabel(self._("Create a PO file containing only entries with errors found.\nFilename: original_filename_errors.po"))
        export_desc.setWordWrap(True)
        export_desc.setStyleSheet("QLabel { color: #666; padding-left: 20px; }")
        layout.addWidget(export_desc)
        
        group.setLayout(layout)
        return group
    
    def on_update_setting_changed(self, checked: bool):
        """更新設定の変更時の処理"""
        self.add_fuzzy.setEnabled(checked)
        self.add_comment.setEnabled(checked)
    
    def remove_checker_comments(self):
        """チェッカーコメントを削除"""
        if not self.current_file:
            QMessageBox.warning(self, self._("Warning"), self._("No PO file selected."))
            return
        
        # カスタムダイアログを作成
        dialog = QDialog(self)
        dialog.setWindowTitle(self._("Confirm Removal"))
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # メッセージ
        message = QLabel(self._("Remove comments starting with [Checker]?\n\nFile: {filename}").format(
            filename=os.path.basename(self.current_file)
        ))
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # チェックボックス
        remove_fuzzy_checkbox = QCheckBox(self._("Also remove fuzzy flags"))
        remove_fuzzy_checkbox.setChecked(False)
        layout.addWidget(remove_fuzzy_checkbox)
        
        # ボタン
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No,
            dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # POファイルを読み込み
                import sgpo
                po = sgpo.pofile(self.current_file)
                
                # チェッカーコメントを削除
                removed_count = 0
                fuzzy_removed_count = 0
                remove_fuzzy = remove_fuzzy_checkbox.isChecked()
                
                for entry in po:
                    modified = False
                    
                    # コメントを削除
                    if entry.tcomment:
                        lines = entry.tcomment.split('\n')
                        filtered_lines = [line for line in lines if not line.startswith('[Checker]')]
                        if len(filtered_lines) < len(lines):
                            modified = True
                            entry.tcomment = '\n'.join(filtered_lines) if filtered_lines else ''
                    
                    # fuzzyフラグを削除（オプション）
                    if remove_fuzzy and 'fuzzy' in entry.flags:
                        entry.flags.remove('fuzzy')
                        fuzzy_removed_count += 1
                    
                    if modified:
                        removed_count += 1
                
                # 保存
                po.save()
                
                # 結果メッセージ
                result_msg = self._("{count} entries had checker comments removed.").format(
                    count=removed_count
                )
                if remove_fuzzy and fuzzy_removed_count > 0:
                    result_msg += '\n' + self._("{count} fuzzy flags were removed.").format(
                        count=fuzzy_removed_count
                    )
                
                QMessageBox.information(
                    self,
                    self._("Complete"),
                    result_msg
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    self._("Error"), 
                    self._("Error occurred while removing comments:\n{error}").format(error=str(e))
                )
    
    def create_detail_tab(self) -> QWidget:
        """詳細タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(5)
        self.detail_table.setHorizontalHeaderLabels([
            self._("Line"),
            self._("msgctxt"),
            self._("msgid (excerpt)"),
            self._("Problem Type"),
            self._("Details")
        ])
        
        # ヘッダーのスタイル設定
        header = self.detail_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # 列幅の設定
        self.detail_table.setColumnWidth(0, 60)   # 行
        self.detail_table.setColumnWidth(1, 200)  # msgctxt
        self.detail_table.setColumnWidth(2, 350)  # msgid
        self.detail_table.setColumnWidth(3, 150)  # 問題の種類
        header.setStretchLastSection(True)       # 詳細
        
        # テーブルのスタイル設定
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.detail_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)  # 1行のみ選択
        self.detail_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #d0d0d0;
                gridline-color: #d0d0d0;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)
        
        self.detail_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        
        # エントリ詳細
        self.entry_detail = QTextEdit()
        self.entry_detail.setReadOnly(True)
        
        # スプリッター（上下分割）
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.detail_table)
        splitter.addWidget(self.entry_detail)
        splitter.setStretchFactor(0, 2)  # テーブルを大きく
        splitter.setStretchFactor(1, 1)  # 詳細を小さく
        
        layout.addWidget(splitter)
        
        return widget
    
    def create_status_bar(self):
        """ステータスバーを作成"""
        self.status_bar = self.statusBar()
        self.status_label = QLabel(self._("Ready"))
        self.status_bar.addWidget(self.status_label)
    
    def set_fonts(self):
        """フォントを設定"""
        app_font = QFont(self.gui_config.font_family, self.gui_config.font_size)
        self.setFont(app_font)
        
        mono_font = QFont(self.gui_config.mono_font_family, self.gui_config.mono_font_size)
        self.summary_text.setFont(mono_font)
        self.entry_detail.setFont(mono_font)
    
    def open_file(self):
        """ファイルを開く"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            self._("Select PO File"),
            "",
            f"{self._('PO Files')} (*.po);;{self._('All Files')} (*.*)"
        )
        
        if filepath:
            self.current_file = filepath
            self.file_label.setText(os.path.basename(filepath))
            self.check_button.setEnabled(True)
            self.remove_comments_button.setEnabled(True)
            self.clear_results()
    
    
    def apply_current_settings(self):
        """現在のUI設定を反映"""
        # チェック項目
        enabled_checks = set()
        if self.check_escape.isChecked():
            enabled_checks.add(CheckType.ESCAPE_SEQUENCE)
        if self.check_html.isChecked():
            enabled_checks.add(CheckType.HTML_TAG)
        if self.check_placeholder.isChecked():
            enabled_checks.add(CheckType.PLACEHOLDER)
        
        self.checker_config.enabled_checks = enabled_checks
        
        # オプション
        self.checker_config.add_fuzzy_flag = self.add_fuzzy.isChecked()
        self.checker_config.add_checker_comment = self.add_comment.isChecked()
        self.checker_config.export_errors = self.export_errors.isChecked()
    
    def start_check(self):
        """チェックを開始"""
        if not self.current_file:
            return
        
        # 設定を適用
        self.apply_current_settings()
        
        # 結果タブに切り替え
        self.main_tabs.setCurrentIndex(1)  # 結果タブ
        
        # UIを準備
        self.clear_results()
        self.check_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # チェッカーを作成
        checker = ConsistencyChecker(self.checker_config)
        
        # スレッドで実行
        self.checker_thread = CheckerThread(checker, self.current_file)
        self.checker_thread.progress_update.connect(self.update_progress)
        self.checker_thread.result_ready.connect(self.add_result)
        self.checker_thread.finished_all.connect(self.on_check_finished)
        self.checker_thread.error_occurred.connect(self.on_check_error)
        self.checker_thread.start()
        
        self.status_label.setText(self._("Checking..."))
    
    def update_progress(self, current: int, total: int):
        """プログレスを更新"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{self._('Checking...')} {current}/{total} ({current*100//total}%)")
    
    def add_result(self, result: CheckResult):
        """結果を追加"""
        row = self.detail_table.rowCount()
        self.detail_table.insertRow(row)
        
        # 行番号
        line_item = QTableWidgetItem(str(result.linenum))
        line_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_table.setItem(row, 0, line_item)
        
        # msgctxt
        msgctxt = result.entry.msgctxt if result.entry.msgctxt else self._("(none)")
        msgctxt_item = QTableWidgetItem(msgctxt)
        msgctxt_item.setToolTip(msgctxt)  # フルテキストをツールチップで表示
        self.detail_table.setItem(row, 1, msgctxt_item)
        
        # msgid (最初の50文字)
        msgid_preview = result.entry.msgid[:50]
        if len(result.entry.msgid) > 50:
            msgid_preview += "..."
        msgid_item = QTableWidgetItem(msgid_preview)
        msgid_item.setToolTip(result.entry.msgid)  # フルテキストをツールチップで表示
        self.detail_table.setItem(row, 2, msgid_item)
        
        # 問題の種類
        problem_types = []
        if result.has_errors:
            problem_types.append(self._("Errors({count})").format(count=len(result.errors)))
        if result.has_warnings:
            problem_types.append(self._("Warnings({count})").format(count=len(result.warnings)))
        type_text = " / ".join(problem_types)
        type_item = QTableWidgetItem(type_text)
        self.detail_table.setItem(row, 3, type_item)
        
        # 詳細（最初の問題のサマリー）
        detail_text = ""
        if result.errors:
            detail_text = result.errors[0]
        elif result.warnings:
            detail_text = result.warnings[0]
        if len(result.errors) + len(result.warnings) > 1:
            detail_text += self._("+{count} more").format(count=len(result.errors) + len(result.warnings) - 1)
        detail_item = QTableWidgetItem(detail_text)
        detail_item.setToolTip("\n".join(result.errors + result.warnings))  # すべての問題をツールチップで表示
        self.detail_table.setItem(row, 4, detail_item)
        
        # 結果オブジェクトを保存
        self.detail_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, result)
        
        # 行の高さを調整
        self.detail_table.setRowHeight(row, 30)
        
        # 色分け
        if result.has_errors:
            color = QColor(255, 230, 230)  # 薄い赤
        elif result.has_warnings:
            color = QColor(255, 250, 230)  # 薄い黄色
        else:
            color = QColor(255, 255, 255)  # 白
            
        for col in range(5):
            item = self.detail_table.item(row, col)
            if item:
                item.setBackground(color)
    
    def on_check_finished(self, results: List[CheckResult], empty_entries: List[polib.POEntry] = None):
        """チェック完了時の処理"""
        self.check_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # サマリーを表示
        total_issues = len(results)
        error_count = sum(1 for r in results if r.has_errors)
        warning_count = sum(1 for r in results if r.has_warnings)
        
        # エラーと警告の詳細カウント
        error_details = {}
        warning_details = {}
        
        # Categories for classification
        escape_keywords = ["escape", "エスケープ文字", "\\n", "\\t", "\\\\"]
        html_keywords = ["HTML", "HTMLタグ", "<", ">", "tag"]
        placeholder_keywords = ["placeholder", "プレースホルダー", "%s", "%d", "{0}", "${"]
        
        for result in results:
            for error in result.errors:
                # エラーの種類を抽出
                if any(kw in error for kw in escape_keywords):
                    key = self._("Escape character issues")
                elif any(kw in error for kw in html_keywords):
                    key = self._("HTML tag issues")
                elif any(kw in error for kw in placeholder_keywords):
                    key = self._("Placeholder issues")
                else:
                    key = self._("Other")
                error_details[key] = error_details.get(key, 0) + 1
                
            for warning in result.warnings:
                if any(kw in warning for kw in escape_keywords):
                    key = self._("Escape character warnings")
                elif any(kw in warning for kw in html_keywords):
                    key = self._("HTML tag warnings")
                elif any(kw in warning for kw in placeholder_keywords):
                    key = self._("Placeholder warnings")
                else:
                    key = self._("Other")
                warning_details[key] = warning_details.get(key, 0) + 1
        
        # HTMLスタイルのサマリー
        summary = f"""<html>
<head>
<style>
body {{ font-family: 'Hiragino Sans', sans-serif; }}
h2 {{ color: #333; margin-top: 10px; }}
.notice {{ background-color: #f9f2e5; padding: 10px; border-radius: 5px; margin: 10px 0; border: 1px solid #e6d7c3; font-size: 0.9em; white-space: pre-line; }}
.stats {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0; }}
.error {{ color: #d9534f; font-weight: bold; }}
.warning {{ color: #f0ad4e; font-weight: bold; }}
.success {{ color: #5cb85c; font-weight: bold; }}
.detail {{ margin-left: 20px; color: #666; }}
.empty-table {{ margin: 10px 0; border-collapse: collapse; width: 100%; }}
.empty-table th {{ background-color: #f0f0f0; padding: 5px; border: 1px solid #ddd; text-align: left; }}
.empty-table td {{ padding: 5px; border: 1px solid #ddd; }}
</style>
</head>
<body>
<h2>{self._("Check Results")}</h2>
<p style="color: #666; font-size: 0.9em;">{self.formatter.get("created")}: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
<div class="notice">{self.formatter.get('report_notice')}</div>
<div class="stats">
<p><b>{self._("Issues detected")}:</b> {total_issues}</p>
<p class="error">{self._("Errors")}: {error_count}</p>"""
        
        if error_details:
            for key, count in error_details.items():
                summary += f'<p class="detail">• {key}: {count}</p>'
                
        summary += f'<p class="warning">{self._("Warnings")}: {warning_count}</p>'
        
        if warning_details:
            for key, count in warning_details.items():
                summary += f'<p class="detail">• {key}: {count}</p>'
        
        summary += "</div>"
        
        if error_count > 0:
            summary += f"<p><b>{self._('Action')}:</b> {self._('Errors were detected. Fuzzy flags and error comments have been added to the PO file.')}</p>"
            if self.checker_config.export_errors:
                summary += f"<p>{self._('Entries with errors have been exported to a separate file.')}</p>"
        else:
            summary += f'<p class="success">✓ {self._("No errors found.")}</p>'
        
        # 空の翻訳セクション
        if empty_entries:
            summary += f"""
<h3>{self.formatter.get('empty_translations')}</h3>
<p>{self.formatter.get('empty_translations_desc')}</p>
<table class="empty-table">
<tr>
<th>#</th>
<th>{self._("Line")}</th>
<th>msgctxt</th>
<th>msgid</th>
</tr>"""
            for idx, entry in enumerate(empty_entries[:20], 1):  # 最初の20件のみ表示
                msgctxt = entry.msgctxt if entry.msgctxt else self._("(none)")
                msgid_preview = entry.msgid[:80]
                if len(entry.msgid) > 80:
                    msgid_preview += "..."
                line_num = int(entry.linenum) if hasattr(entry, 'linenum') and entry.linenum else 0
                summary += f"""
<tr>
<td>{idx}</td>
<td>{line_num}</td>
<td>{html.escape(msgctxt)}</td>
<td>{html.escape(msgid_preview)}</td>
</tr>"""
            if len(empty_entries) > 20:
                summary += f"""
<tr>
<td colspan="4" style="text-align: center;">... {self.formatter.get("and_more", count=len(empty_entries) - 20)}</td>
</tr>"""
            summary += "</table>"
            
        summary += """
</body>
</html>"""
        
        self.summary_text.setHtml(summary)
        self.status_label.setText(self._("Check complete - Errors: {errors}, Warnings: {warnings}").format(errors=error_count, warnings=warning_count))
        
        # 詳細タブも更新（エラーがある場合）
        if error_count > 0:
            self.main_tabs.setTabText(2, f"{self._('Details')} ({error_count})")
        else:
            self.main_tabs.setTabText(2, self._("Details"))
    
    def on_check_error(self, error_msg: str):
        """エラー発生時の処理"""
        self.check_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, self._("Error"), f"{self._('Error occurred during check')}:\n{error_msg}")
        self.status_label.setText(self._("Error occurred"))
    
    def on_table_selection_changed(self):
        """テーブル選択変更時の処理"""
        selected = self.detail_table.selectedItems()
        if not selected:
            self.entry_detail.clear()
            return
        
        # 選択された行の結果を取得
        row = selected[0].row()
        result = self.detail_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if result:
            # HTML形式でエントリ詳細を表示
            detail = f"""<html>
<head>
<style>
body {{ font-family: 'Monaco', 'Courier New', monospace; font-size: 10pt; }}
.header {{ background-color: #f0f0f0; padding: 5px; font-weight: bold; position: relative; }}
.entry-number {{ position: absolute; right: 10px; top: 5px; font-size: 14px; color: #666666; }}
.msgid {{ background-color: #e8f4f8; padding: 8px; margin: 5px 0; white-space: pre-wrap; }}
.msgstr {{ background-color: #f8f4e8; padding: 8px; margin: 5px 0; white-space: pre-wrap; }}
.error {{ color: #d9534f; font-weight: bold; }}
.warning {{ color: #f0ad4e; font-weight: bold; }}
.label {{ color: #666; font-weight: bold; }}
</style>
</head>
<body>
<div class="header">
    {self._("Entry {linenum}").format(linenum=result.linenum)}
    <span class="entry-number">#{row + 1}</span>
</div>
"""
            
            if result.entry.msgctxt:
                detail += f'<p><span class="label">msgctxt:</span> {html.escape(result.entry.msgctxt)}</p>'
            
            detail += f'<div class="label">msgid:</div>'
            detail += f'<div class="msgid">{html.escape(result.entry.msgid)}</div>'
            
            detail += f'<div class="label">msgstr:</div>'
            detail += f'<div class="msgstr">{html.escape(result.entry.msgstr)}</div>'
            
            if result.errors:
                detail += f'<div class="error">{self._("Errors")}:</div><ul>'
                for error in result.errors:
                    detail += f"<li>{html.escape(error)}</li>"
                detail += "</ul>"
            
            if result.warnings:
                detail += f'<div class="warning">{self._("Warnings")}:</div><ul>'
                for warning in result.warnings:
                    detail += f"<li>{html.escape(warning)}</li>"
                detail += "</ul>"
            
            detail += """
</body>
</html>"""
            
            self.entry_detail.setHtml(detail)
    
    def clear_results(self):
        """結果をクリア"""
        font_family = "Segoe UI" if sys.platform == "win32" else "Hiragino Sans" if sys.platform == "darwin" else "Ubuntu"
        self.summary_text.setHtml(f"""<html>
<head>
<style>
body {{ font-family: '{font_family}', sans-serif; color: #666; text-align: center; padding-top: 50px; }}
</style>
</head>
<body>
<h3>{self._("Checking...")}</h3>
<p>{self._("Please wait.")}</p>
</body>
</html>""")
        self.detail_table.setRowCount(0)
        self.entry_detail.clear()
    
    def change_language(self, language: str):
        """言語を変更"""
        self.current_language = language
        self.checker_config.output_language = language
        self.formatter = MessageFormatter(language)
        
        # 翻訳システムを更新
        self._ = setup_translation(language)
        
        # UIを再構築（簡単のためウィンドウタイトルのみ更新）
        self.setWindowTitle(self._("PO File Consistency Checker"))
        
        # メニューのチェック状態を更新
        menubar = self.menuBar()
        for action in menubar.actions():
            if action.menu() and "Settings" in action.menu().title():
                for sub_action in action.menu().actions():
                    if sub_action.menu() and "Language" in sub_action.menu().title():
                        for lang_action in sub_action.menu().actions():
                            lang_action.setChecked(False)
                        # 現在の言語をチェック
                        available_languages = get_available_languages()
                        for i, (lang_code, lang_name) in enumerate(available_languages.items()):
                            if lang_code == language:
                                sub_action.menu().actions()[i].setChecked(True)
                                break


def main():
    """GUIアプリケーションを起動"""
    app = QApplication(sys.argv)
    
    # アプリケーション設定
    app.setApplicationName("PO Consistency Checker")
    app.setOrganizationName("SmartGit Translation Community")
    
    # メインウィンドウ
    window = ConsistencyCheckerGUI()
    window.show()
    
    sys.exit(app.exec())