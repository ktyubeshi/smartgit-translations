import tkinter as tk
from tkinter import filedialog, messagebox
import os
import polib


class POMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PO File Merger")

        # 左側の入力ファイル
        self.left_file_label = tk.Label(root, text="Left Input File:")
        self.left_file_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.left_file_path = tk.StringVar()
        self.left_file_entry = tk.Entry(root, textvariable=self.left_file_path, width=50)
        self.left_file_entry.grid(row=0, column=1, padx=5, pady=5)

        self.left_browse_button = tk.Button(root, text="Browse", command=self.browse_left_file)
        self.left_browse_button.grid(row=0, column=2, padx=5, pady=5)

        # 右側の入力ファイル
        self.right_file_label = tk.Label(root, text="Right Input File:")
        self.right_file_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.right_file_path = tk.StringVar()
        self.right_file_entry = tk.Entry(root, textvariable=self.right_file_path, width=50)
        self.right_file_entry.grid(row=1, column=1, padx=5, pady=5)

        self.right_browse_button = tk.Button(root, text="Browse", command=self.browse_right_file)
        self.right_browse_button.grid(row=1, column=2, padx=5, pady=5)

        # 出力ファイル名の入力欄
        self.output_file_label = tk.Label(root, text="Output File:")
        self.output_file_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")

        self.output_file_name = tk.StringVar()
        self.output_file_entry = tk.Entry(root, textvariable=self.output_file_name, width=50)
        self.output_file_entry.grid(row=2, column=1, padx=5, pady=5)

        # Mergeボタン
        self.merge_button = tk.Button(root, text="Merge", command=self.merge_files)
        self.merge_button.grid(row=3, column=1, pady=10)

    def browse_left_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PO Files", "*.po")])
        if file_path:
            self.left_file_path.set(file_path)
            self.set_default_output_file_name()

    def browse_right_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PO Files", "*.po")])
        if file_path:
            self.right_file_path.set(file_path)
            self.set_default_output_file_name()

    def set_default_output_file_name(self):
        left_path = self.left_file_path.get()
        if left_path:
            base_name = os.path.splitext(os.path.basename(left_path))[0]
            directory = os.path.dirname(left_path)
            self.output_file_name.set(os.path.join(directory, f"{base_name}_Merged.po"))

    def merge_files(self):
        left_file = self.left_file_path.get()
        right_file = self.right_file_path.get()
        output_file = self.output_file_name.get()

        if not left_file or not right_file or not output_file:
            messagebox.showerror("Error", "Please select both input files and specify an output file.")
            return

        try:
            # 左側と右側のファイルを読み込み
            left_po = polib.pofile(left_file, wrapwidth=9999)
            right_po = polib.pofile(right_file, wrapwidth=9999)

            # 右側のエントリを辞書化
            right_entries = {(entry.msgctxt, entry.msgid): entry for entry in right_po}

            # マージ処理
            for entry in left_po:
                key = (entry.msgctxt, entry.msgid)
                if key in right_entries and right_entries[key].msgstr:
                    entry.msgstr = right_entries[key].msgstr

            # マージしたファイルを保存
            left_po.save(output_file, newline='\n')
            messagebox.showinfo("Success", f"Files merged successfully and saved to {output_file}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = POMergerApp(root)
    root.mainloop()