import tkinter as tk
from tkinter import filedialog, messagebox
import polib
import os


class UntranslatedEntryExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('POファイルエントリ抽出アプリ')
        self.root.geometry('700x400')
        self.root.configure(bg='#f8f9fa')

        # 入力ファイルパス
        self.input_file_path = tk.StringVar()
        self.untranslated_output_file_name = tk.StringVar()
        self.translated_output_file_name = tk.StringVar()

        # ヘッダー
        self.header_label = tk.Label(root, text='POファイルエントリ抽出アプリ', font=('Arial', 16, 'bold'),
                                     bg='#f8f9fa')
        self.header_label.place(x=200, y=20)

        # ファイル参照
        self.file_label = tk.Label(root, text='ファイル参照:', font=('Arial', 11), bg='#f8f9fa')
        self.file_label.place(x=20, y=80)

        self.file_path_display = tk.Entry(root, textvariable=self.input_file_path, width=50, state='readonly',
                                          font=('Arial', 11))
        self.file_path_display.place(x=120, y=80)

        self.browse_button = tk.Button(root, text='参照', command=self.browse_file, font=('Arial', 11), padx=6)
        self.browse_button.place(x=600, y=76)

        # 未翻訳エントリ出力ファイル名
        self.untranslated_output_label = tk.Label(root, text='未翻訳エントリ出力ファイル名:', font=('Arial', 11),
                                                  bg='#f8f9fa')
        self.untranslated_output_label.place(x=20, y=130)

        self.untranslated_output_entry = tk.Entry(root, textvariable=self.untranslated_output_file_name, width=50,
                                                  font=('Arial', 11))
        self.untranslated_output_entry.place(x=240, y=130)

        # 翻訳済みエントリ出力ファイル名
        self.translated_output_label = tk.Label(root, text='翻訳済みエントリ出力ファイル名:', font=('Arial', 11),
                                                bg='#f8f9fa')
        self.translated_output_label.place(x=20, y=180)

        self.translated_output_entry = tk.Entry(root, textvariable=self.translated_output_file_name, width=50,
                                                font=('Arial', 11))
        self.translated_output_entry.place(x=240, y=180)

        # 未翻訳エントリの抽出ボタン
        self.extract_untranslated_button = tk.Button(root, text='未翻訳エントリの抽出',
                                                     command=self.extract_untranslated_entries, font=('Arial', 11),
                                                     padx=10, pady=5)
        self.extract_untranslated_button.place(x=150, y=250)

        # 翻訳済みエントリの抽出ボタン
        self.extract_translated_button = tk.Button(root, text='翻訳済みエントリの抽出',
                                                   command=self.extract_translated_entries, font=('Arial', 11), padx=10,
                                                   pady=5)
        self.extract_translated_button.place(x=400, y=250)

        # 情報ラベル
        self.info_label = tk.Label(root, text='', font=('Arial', 10), bg='#f8f9fa')
        self.info_label.place(x=20, y=330)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[('PO Files', '*.po')])
        if file_path:
            self.input_file_path.set(file_path)
            folder_path = os.path.dirname(file_path)
            default_untranslated_output_name = os.path.join(folder_path, os.path.splitext(os.path.basename(file_path))[
                0] + '_未翻訳エントリ.po')
            default_translated_output_name = os.path.join(folder_path, os.path.splitext(os.path.basename(file_path))[
                0] + '_翻訳済みエントリ.po')
            self.untranslated_output_file_name.set(default_untranslated_output_name)
            self.translated_output_file_name.set(default_translated_output_name)

    def extract_untranslated_entries(self):
        input_path = self.input_file_path.get()
        output_path = self.untranslated_output_file_name.get()

        if not input_path:
            messagebox.showerror('エラー', '入力ファイルを選択してください')
            return

        try:
            # POファイルを読み込み
            po = polib.pofile(input_path)

            # 未翻訳のエントリを抽出
            untranslated_entries = [entry for entry in po if not entry.translated()]

            # 未翻訳エントリを新しいPOファイルに書き込み
            untranslated_po = polib.POFile()
            untranslated_po.metadata = po.metadata
            untranslated_po.extend(untranslated_entries)
            untranslated_po.save(output_path)

            self.info_label.config(text=f'未翻訳エントリを抽出しました: {output_path}', foreground='green')
        except Exception as e:
            messagebox.showerror('エラー', f'エラーが発生しました: {e}')

    def extract_translated_entries(self):
        input_path = self.input_file_path.get()
        output_path = self.translated_output_file_name.get()

        if not input_path:
            messagebox.showerror('エラー', '入力ファイルを選択してください')
            return

        try:
            # POファイルを読み込み
            po = polib.pofile(input_path)

            # 翻訳済みのエントリを抽出
            translated_entries = [entry for entry in po if entry.translated()]

            # 翻訳済みエントリを新しいPOファイルに書き込み
            translated_po = polib.POFile()
            translated_po.metadata = po.metadata
            translated_po.extend(translated_entries)
            translated_po.save(output_path)

            self.info_label.config(text=f'翻訳済みエントリを抽出しました: {output_path}', foreground='green')
        except Exception as e:
            messagebox.showerror('エラー', f'エラーが発生しました: {e}')


if __name__ == '__main__':
    root = tk.Tk()
    app = UntranslatedEntryExtractorApp(root)
    root.mainloop()