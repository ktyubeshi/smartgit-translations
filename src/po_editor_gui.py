import sys
import logging
from typing import Callable, Dict, List, Optional, Tuple
from pathlib import Path
import glob
import sgpo

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QLabel,
    QLineEdit,
    QFileDialog,
    QGroupBox,
    QTabWidget,
    QDialog,
    QComboBox,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, QThread, Signal

import delete_extracted_comments
import format_po_files
import import_mismatch
import import_unknown
import import_pot
from path_finder import PoPathFinder

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ファイルハンドラの設定
file_handler = logging.FileHandler("po_editor_gui.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

# コンソールハンドラの設定
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(console_handler)

# 既存のハンドラをクリア（重複を防ぐため）
logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.debug("ロガーを初期化しました")


class WorkerThread(QThread):
    finished = Signal(bool, str)
    log = Signal(str)

    def __init__(self, task_func: Callable[[], None]):
        super().__init__()
        self.task_func = task_func

    def run(self):
        try:
            # 標準出力をキャプチャするための設定
            import io
            import sys

            captured_output = io.StringIO()
            sys.stdout = captured_output

            # タスクを実行
            self.task_func()

            # 出力を取得
            output = captured_output.getvalue()
            sys.stdout = sys.__stdout__

            self.log.emit(output)
            self.finished.emit(True, "処理が完了しました")
        except Exception as e:
            self.finished.emit(False, f"エラーが発生しました: {str(e)}")


class LanguageSelectionDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("言語選択")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 言語選択コンボボックス
        self.language_combo = QComboBox()
        # 言語コードと言語名のマッピング（ロケール形式）
        self.languages = {
            "ja_JP": "日本語 (日本)",
            "de_DE": "ドイツ語 (ドイツ)",
            "fr_FR": "フランス語 (フランス)",
            "es_ES": "スペイン語 (スペイン)",
            "it_IT": "イタリア語 (イタリア)",
            "ko_KR": "韓国語 (韓国)",
            "zh_CN": "中国語 (中国)",
            "zh_TW": "中国語 (台湾)",
            "ru_RU": "ロシア語 (ロシア)",
            "pt_BR": "ポルトガル語 (ブラジル)",
            "pt_PT": "ポルトガル語 (ポルトガル)",
            "nl_NL": "オランダ語 (オランダ)",
            "en_US": "英語 (アメリカ)",
            "en_GB": "英語 (イギリス)",
        }
        for code, name in sorted(self.languages.items(), key=lambda x: x[1]):
            self.language_combo.addItem(name, code)
        layout.addWidget(QLabel("言語を選択してください:"))
        layout.addWidget(self.language_combo)

        # OKとキャンセルボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_language(self) -> str:
        return self.language_combo.currentData()


class FileSettingsTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # POTファイル
        pot_group = QGroupBox("POTファイル")
        pot_layout = QHBoxLayout(pot_group)
        self.pot_path = QLineEdit()
        pot_layout.addWidget(self.pot_path)
        browse_pot = QPushButton("参照")
        browse_pot.clicked.connect(
            lambda: self.browse_file(self.pot_path, "POT Files (*.pot)")
        )
        pot_layout.addWidget(browse_pot)
        layout.addWidget(pot_group)

        # POファイル
        po_group = QGroupBox("POファイル")
        po_layout = QVBoxLayout(po_group)

        # POファイルテーブル
        self.po_files_table = QTableWidget()
        self.po_files_table.setColumnCount(3)
        self.po_files_table.setHorizontalHeaderLabels(["言語", "ファイルパス", "操作"])
        header = self.po_files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.po_files_table.setColumnWidth(0, 100)
        self.po_files_table.setColumnWidth(2, 100)
        po_layout.addWidget(self.po_files_table)

        # 言語追加ボタン
        add_language = QPushButton("言語追加")
        add_language.clicked.connect(self.add_language)
        po_layout.addWidget(add_language)

        layout.addWidget(po_group)

        # Unknown/Mismatchファイル
        other_group = QGroupBox("その他のファイル")
        other_layout = QGridLayout(other_group)

        # Unknownファイル
        other_layout.addWidget(QLabel("Unknownファイル:"), 0, 0)
        self.unknown_path = QLineEdit()
        other_layout.addWidget(self.unknown_path, 0, 1)
        browse_unknown = QPushButton("参照")
        browse_unknown.clicked.connect(
            lambda: self.browse_file(
                self.unknown_path,
                "Unknown Files (unknown.24_1 unknown.25_1);;All Files (*)",
            )
        )
        other_layout.addWidget(browse_unknown, 0, 2)

        # Mismatchファイル
        other_layout.addWidget(QLabel("Mismatchファイル:"), 1, 0)
        self.mismatch_path = QLineEdit()
        other_layout.addWidget(self.mismatch_path, 1, 1)
        browse_mismatch = QPushButton("参照")
        browse_mismatch.clicked.connect(
            lambda: self.browse_file(
                self.mismatch_path,
                "Mismatch Files (mismatch.24_1 mismatch.25_1);;All Files (*)",
            )
        )
        other_layout.addWidget(browse_mismatch, 1, 2)

        layout.addWidget(other_group)

    def browse_file(self, line_edit: QLineEdit, file_filter: str):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "ファイルを選択", "", file_filter
        )
        if file_path:
            line_edit.setText(file_path)

    def add_language_to_table(self, language: str, file_path: str = "") -> None:
        row = self.po_files_table.rowCount()
        self.po_files_table.insertRow(row)

        # 言語
        lang_item = QTableWidgetItem(language)
        lang_item.setFlags(lang_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.po_files_table.setItem(row, 0, lang_item)

        # ファイルパス
        path_item = QTableWidgetItem(file_path)
        self.po_files_table.setItem(row, 1, path_item)

        # 操作ボタン用のウィジェット
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)

        # 参照ボタン
        browse_button = QPushButton("参照")
        browse_button.clicked.connect(lambda: self.browse_po_file(row))
        button_layout.addWidget(browse_button)

        # 削除ボタン
        delete_button = QPushButton("削除")
        delete_button.clicked.connect(lambda: self.delete_language_row(row))
        button_layout.addWidget(delete_button)

        self.po_files_table.setCellWidget(row, 2, button_widget)

    def browse_po_file(self, row: int) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "POファイルを選択", "", "PO Files (*.po)"
        )
        if file_path:
            self.po_files_table.item(row, 1).setText(file_path)

    def delete_language_row(self, row: int) -> None:
        language = self.po_files_table.item(row, 0).text()
        if (
            QMessageBox.question(self, "確認", f"{language}の設定を削除しますか？")
            == QMessageBox.StandardButton.Yes
        ):
            self.po_files_table.removeRow(row)

    def add_language(self):
        dialog = LanguageSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_lang = dialog.get_selected_language()
            if not self.find_language_row(selected_lang):
                self.add_language_to_table(selected_lang)
            else:
                QMessageBox.warning(
                    self,
                    "警告",
                    f"言語 {selected_lang} は既に追加されています。",
                )

    def find_language_row(self, language: str) -> Optional[int]:
        for row in range(self.po_files_table.rowCount()):
            if self.po_files_table.item(row, 0).text() == language:
                return row
        return None

    def get_language_file_pairs(self) -> List[Tuple[str, str]]:
        pairs = []
        for row in range(self.po_files_table.rowCount()):
            lang = self.po_files_table.item(row, 0).text()
            path = self.po_files_table.item(row, 1).text()
            pairs.append((lang, path))
        return pairs


class OperationsTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        buttons = [
            ("未知の翻訳インポート", import_unknown.main),
            ("POTファイルインポート", import_pot.main),
            ("不一致翻訳インポート", import_mismatch.main),
            ("POファイルフォーマット", format_po_files.main),
            ("抽出コメント削除", delete_extracted_comments.main),
        ]

        for text, func in buttons:
            button = QPushButton(text)
            button.clicked.connect(lambda checked, f=func: self.execute_task(f))
            layout.addWidget(button)

    def execute_task(self, task_func: Callable[[], None]):
        # MainWindowのexecute_taskを呼び出す
        self.window().execute_task(task_func)


class ExtractionTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 入力ファイル選択グループ
        input_group = QGroupBox("入力ファイル")
        input_layout = QVBoxLayout(input_group)
        self.input_list = QListWidget()
        input_layout.addWidget(self.input_list)
        layout.addWidget(input_group)

        # 出力ファイル設定グループ
        output_group = QGroupBox("出力ファイル")
        output_layout = QGridLayout(output_group)

        # 翻訳済みファイル
        output_layout.addWidget(QLabel("翻訳済み:"), 0, 0)
        self.translated_path = QLineEdit()
        output_layout.addWidget(self.translated_path, 0, 1)
        browse_translated = QPushButton("参照")
        browse_translated.clicked.connect(
            lambda: self.save_file(self.translated_path, "PO Files (*.po)")
        )
        output_layout.addWidget(browse_translated, 0, 2)

        # 未翻訳ファイル
        output_layout.addWidget(QLabel("未翻訳:"), 1, 0)
        self.untranslated_path = QLineEdit()
        output_layout.addWidget(self.untranslated_path, 1, 1)
        browse_untranslated = QPushButton("参照")
        browse_untranslated.clicked.connect(
            lambda: self.save_file(self.untranslated_path, "PO Files (*.po)")
        )
        output_layout.addWidget(browse_untranslated, 1, 2)

        layout.addWidget(output_group)

        # 抽出操作グループ
        extract_group = QGroupBox("抽出操作")
        extract_layout = QVBoxLayout(extract_group)

        # 翻訳済みエントリの抽出
        extract_translated = QPushButton("翻訳済みのエントリを抽出")
        extract_translated.clicked.connect(
            lambda: self.extract_entries(translated=True)
        )
        extract_layout.addWidget(extract_translated)

        # 未翻訳エントリの抽出
        extract_untranslated = QPushButton("未翻訳のエントリを抽出")
        extract_untranslated.clicked.connect(
            lambda: self.extract_entries(translated=False)
        )
        extract_layout.addWidget(extract_untranslated)

        layout.addWidget(extract_group)

        # 入力ファイル選択時の処理
        self.input_list.currentItemChanged.connect(self.update_output_paths)

    def update_input_files(self):
        """ファイル設定タブのPOファイルリストを取得して表示を更新"""
        self.input_list.clear()
        file_settings_tab = self.window().file_settings_tab
        for lang, path in file_settings_tab.get_language_file_pairs():
            if path:  # パスが設定されている場合のみ追加
                item = QListWidgetItem(f"{lang}: {path}")
                item.setData(Qt.ItemDataRole.UserRole, path)  # パスを保持
                self.input_list.addItem(item)

    def update_output_paths(self, current: QListWidgetItem, previous: QListWidgetItem):
        """入力ファイル選択時に出力ファイルパスを更新"""
        if current:
            input_path = Path(current.data(Qt.ItemDataRole.UserRole))
            self.translated_path.setText(
                str(
                    input_path.with_name(
                        f"{input_path.stem}_translated{input_path.suffix}"
                    )
                )
            )
            self.untranslated_path.setText(
                str(
                    input_path.with_name(
                        f"{input_path.stem}_untranslated{input_path.suffix}"
                    )
                )
            )

    def save_file(self, line_edit: QLineEdit, file_filter: str):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ファイルを保存", "", file_filter
        )
        if file_path:
            line_edit.setText(file_path)

    def extract_entries(self, translated: bool):
        if not self.input_list.currentItem():
            QMessageBox.warning(self, "警告", "入力ファイルを選択してください。")
            return

        input_file = self.input_list.currentItem().data(Qt.ItemDataRole.UserRole)
        output_file = (
            self.translated_path.text() if translated else self.untranslated_path.text()
        )

        if not output_file:
            QMessageBox.warning(self, "警告", "出力ファイルを指定してください。")
            return

        if not Path(input_file).exists():
            QMessageBox.warning(self, "警告", "入力ファイルが存在しません。")
            return

        try:
            logger.debug(f"エントリ抽出開始: {'翻訳済み' if translated else '未翻訳'}")
            logger.debug(f"入力ファイル: {input_file}")
            logger.debug(f"出力ファイル: {output_file}")

            # POファイルを読み込み
            po = sgpo.pofile(input_file)

            # 翻訳済み/未翻訳エントリを抽出
            extracted_po = sgpo.POFile()
            for entry in po:
                if bool(entry.msgstr) == translated:  # msgstrが空でない = 翻訳済み
                    extracted_po.append(entry)

            # 抽出したエントリを保存
            extracted_po.save(output_file)

            logger.info(f"エントリ抽出完了: {len(extracted_po)}件")
            QMessageBox.information(
                self,
                "完了",
                f"{'翻訳済み' if translated else '未翻訳'}エントリを抽出しました。\n"
                f"抽出件数: {len(extracted_po)}件",
            )

        except Exception as e:
            logger.error(f"エントリ抽出中にエラー発生: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self, "エラー", f"エントリの抽出に失敗しました: {str(e)}"
            )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PO File Editor")
        self.setMinimumSize(800, 600)

        # メインウィジェットとレイアウト
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # タブウィジェット
        self.tabs = QTabWidget()
        self.file_settings_tab = FileSettingsTab()
        self.operations_tab = OperationsTab()
        self.extraction_tab = ExtractionTab()
        self.tabs.addTab(self.file_settings_tab, "ファイル設定")
        self.tabs.addTab(self.operations_tab, "操作")
        self.tabs.addTab(self.extraction_tab, "抽出")
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)

        # ログ表示エリア
        status_group = QGroupBox("ステータス")
        status_layout = QVBoxLayout(status_group)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        status_layout.addWidget(self.log_area)
        layout.addWidget(status_group)

        self.worker: Optional[WorkerThread] = None

        # 初期ファイル検出
        self.detect_files()

    def on_tab_changed(self, index: int):
        """タブ切り替え時の処理"""
        if self.tabs.widget(index) == self.extraction_tab:
            logger.debug("抽出タブに切り替え: 入力ファイルリストを更新")
            self.extraction_tab.update_input_files()

    def detect_files(self):
        logger.debug("ファイル検出を開始")
        finder = PoPathFinder()
        try:
            # POTファイル検出
            pot_file = finder.get_pot_file()
            logger.debug(f"POTファイルを検出: {pot_file}")
            self.file_settings_tab.pot_path.setText(str(pot_file))

            # POファイル検出とunknown/mismatchファイルの検出
            po_files = finder.get_po_files()
            logger.debug(f"POファイルを検出: {po_files}")
            if po_files:
                # POファイルが存在するディレクトリを取得
                po_dir = Path(po_files[0]).parent
                logger.debug(f"POファイルディレクトリ: {po_dir}")

                # unknown/mismatchファイルのパターン
                patterns = {
                    "unknown": "unknown.[0-9]*_[0-9]*",
                    "mismatch": "mismatch.[0-9]*_[0-9]*",
                }

                # 最新のunknown/mismatchファイルを検出
                for file_type, pattern in patterns.items():
                    files = sorted(po_dir.glob(pattern))
                    logger.debug(f"{file_type}ファイルを検出: {files}")
                    if files:
                        latest_file = str(files[-1])
                        logger.debug(f"最新の{file_type}ファイル: {latest_file}")
                        if file_type == "unknown":
                            self.file_settings_tab.unknown_path.setText(latest_file)
                        else:
                            self.file_settings_tab.mismatch_path.setText(latest_file)

            # POファイルの言語設定
            for po_file in po_files:
                # TODO: 言語コードの抽出ロジックを実装
                lang = Path(po_file).stem
                logger.debug(f"言語コードを抽出: {lang} from {po_file}")
                if not self.file_settings_tab.find_language_row(lang):
                    logger.debug(f"言語{lang}をテーブルに追加")
                    self.file_settings_tab.add_language_to_table(lang, str(po_file))

        except Exception as e:
            logger.error(f"ファイル検出中にエラー発生: {str(e)}", exc_info=True)
            QMessageBox.warning(
                self, "警告", f"ファイル検出中にエラーが発生しました: {str(e)}"
            )

    def execute_task(self, task_func: Callable[[], None]):
        if self.worker and self.worker.isRunning():
            logger.warning("他の処理が実行中のため、新しいタスクを開始できません")
            QMessageBox.warning(self, "警告", "他の処理が実行中です")
            return

        logger.debug(f"タスクを開始: {task_func.__name__}")
        self.worker = WorkerThread(task_func)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.log.connect(self.append_log)
        self.worker.start()

    def append_log(self, text: str):
        logger.debug(f"ログを追加: {text}")
        self.log_area.append(text)

    def on_task_finished(self, success: bool, message: str):
        if success:
            logger.info(f"タスク完了: {message}")
            QMessageBox.information(self, "完了", message)
        else:
            logger.error(f"タスク失敗: {message}")
            QMessageBox.critical(self, "エラー", message)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
