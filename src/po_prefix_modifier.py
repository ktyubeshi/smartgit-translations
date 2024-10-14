import tkinter as tk
from tkinter import filedialog, messagebox
import polib
import os

class PoEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PO File Prefix Editor")

        # Input File Section
        self.file_path = ""

        self.file_button = tk.Button(root, text="参照", command=self.browse_file)
        self.file_button.grid(row=0, column=0, padx=10, pady=10)

        self.file_label = tk.Label(root, text="ファイルが選択されていません", width=50, anchor="w")
        self.file_label.grid(row=0, column=1, padx=10, pady=10)

        # Output File Section
        tk.Label(root, text="出力ファイル名:").grid(row=1, column=0, padx=10, pady=10)
        self.output_entry = tk.Entry(root, width=50)
        self.output_entry.grid(row=1, column=1, padx=10, pady=10)

        # Prefix Section
        tk.Label(root, text="付加する文字:").grid(row=2, column=0, padx=10, pady=10)
        self.prefix_entry = tk.Entry(root, width=50)
        self.prefix_entry.insert(0, "★")
        self.prefix_entry.grid(row=2, column=1, padx=10, pady=10)

        # Action Buttons
        self.add_prefix_button = tk.Button(root, text="Prefix付加", command=self.add_prefix)
        self.add_prefix_button.grid(row=3, column=0, padx=10, pady=10)

        self.remove_prefix_button = tk.Button(root, text="Prefix削除", command=self.remove_prefix)
        self.remove_prefix_button.grid(row=3, column=1, padx=10, pady=10)

    def browse_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("PO files", "*.po")])
        if self.file_path:
            self.file_label.config(text=self.file_path)
            default_output = os.path.splitext(self.file_path)[0] + "_PrefixAdded.po"
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, default_output)

    def add_prefix(self):
        self.modify_prefix(add=True)

    def remove_prefix(self):
        self.modify_prefix(add=False)

    def modify_prefix(self, add=True):
        if not self.file_path:
            messagebox.showerror("エラー", "入力ファイルを選択してください")
            return

        output_path = self.output_entry.get()
        prefix = self.prefix_entry.get()

        if not prefix:
            messagebox.showerror("エラー", "付加する文字を入力してください")
            return

        try:
            po = polib.pofile(self.file_path, wrapwidth=9999)
            for entry in po:
                if add:
                    if not entry.msgstr.startswith(prefix):
                        entry.msgstr = prefix + entry.msgstr
                else:
                    if entry.msgstr.startswith(prefix):
                        entry.msgstr = entry.msgstr[len(prefix):]
            po.save(output_path, newline='\n')
            messagebox.showinfo("完了", f"ファイルを保存しました: {output_path}")
        except Exception as e:
            messagebox.showerror("エラー", f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PoEditorApp(root)
    root.mainloop()