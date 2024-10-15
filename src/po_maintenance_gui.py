import threading
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from delete_extracted_comments import main as delete_extracted_comments_main
from format_po_files import main as format_po_files_main
from import_mismatch import main as import_mismatch_main
# 既存のモジュールをインポート
from import_pot import main as import_pot_main
from import_unknown import main as import_unknown_main


class POManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("POファイルメンテナンスツール")

        # フレームの作成
        frame = tk.Frame(root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # ボタンの作成
        # Master to POT ボタンを削除
        # btn_master2pot = tk.Button(frame, text="Master to POT", command=self.run_master2pot)
        # btn_master2pot.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        # Locale to PO ボタンを削除
        # btn_locale2po = tk.Button(frame, text="Locale to PO", command=self.run_locale2po)
        # btn_locale2po.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        btn_import_pot = tk.Button(frame, text="Import POT to PO", command=self.run_import_pot)
        btn_import_pot.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        btn_import_unknown = tk.Button(frame, text="Import Unknown", command=self.run_import_unknown)
        btn_import_unknown.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        btn_import_mismatch = tk.Button(frame, text="Import Mismatch", command=self.run_import_mismatch)
        btn_import_mismatch.grid(row=1, column=0, padx=5, pady=5, sticky='ew')

        btn_delete_comments = tk.Button(frame, text="Delete Extracted Comments", command=self.run_delete_comments)
        btn_delete_comments.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        btn_format_po = tk.Button(frame, text="Format PO Files", command=self.run_format_po)
        btn_format_po.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        # ログ表示エリア
        self.log_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15)
        self.log_area.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

        # フレームのグリッド設定
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args)
        thread.start()

    # Master to POT のメソッドを削除
    # def run_master2pot(self):
    #     self.log("Master to POTの実行を開始します...")
    #     self.run_in_thread(self.execute_script, master2pot_main, "Master to POTが完了しました。")

    # Locale to PO のメソッドを削除
    # def run_locale2po(self):
    #     self.log("Locale to POの実行を開始します...")
    #     self.run_in_thread(self.execute_script, locale2po_main, "Locale to POが完了しました。")

    def run_import_pot(self):
        self.log("Import POT to POの実行を開始します...")
        self.run_in_thread(self.execute_script, import_pot_main, "Import POT to POが完了しました。")

    def run_import_unknown(self):
        self.log("Import Unknownの実行を開始します...")
        self.run_in_thread(self.execute_script, import_unknown_main, "Import Unknownが完了しました。")

    def run_import_mismatch(self):
        self.log("Import Mismatchの実行を開始します...")
        self.run_in_thread(self.execute_script, import_mismatch_main, "Import Mismatchが完了しました。")

    def run_delete_comments(self):
        self.log("Delete Extracted Commentsの実行を開始します...")
        self.run_in_thread(self.execute_script, delete_extracted_comments_main,
                           "Delete Extracted Commentsが完了しました。")

    def run_format_po(self):
        self.log("Format PO Filesの実行を開始します...")
        self.run_in_thread(self.execute_script, format_po_files_main, "Format PO Filesが完了しました。")

    def execute_script(self, script_func, completion_message):
        try:
            script_func()
            self.log(completion_message)
        except Exception as e:
            self.log(f"エラーが発生しました: {e}")
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")


def main():
    root = tk.Tk()
    app = POManagementApp(root)
    root.geometry("800x600")
    root.mainloop()


if __name__ == "__main__":
    main()
