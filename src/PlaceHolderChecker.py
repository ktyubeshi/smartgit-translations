import tkinter as tk
from tkinter import filedialog, messagebox
import sgpo
import re

class POEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PO Placeholder Checker")

        self.file_path = ""

        # File selection button
        self.select_button = tk.Button(root, text="Select PO File", command=self.select_file)
        self.select_button.grid(row=0, column=0, padx=10, pady=10)

        # File path display
        self.file_path_display = tk.Entry(root, width=50)
        self.file_path_display.grid(row=0, column=1, padx=10, pady=10)

        # Save button
        self.save_button = tk.Button(root, text="Save", command=self.save_file)
        self.save_button.grid(row=1, column=0, columnspan=2, pady=10)

        # Listbox for displaying mismatches
        self.mismatch_listbox = tk.Listbox(root, width=100, height=10)
        self.mismatch_listbox.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    def select_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("PO files", "*.po")])
        if self.file_path:
            self.file_path_display.delete(0, tk.END)
            self.file_path_display.insert(0, self.file_path)

    def save_file(self):
        if not self.file_path:
            messagebox.showwarning("Warning", "Please select a PO file first.")
            return

        try:
            po = sgpo.pofile(self.file_path)
            placeholder_pattern = re.compile(r"\$\d+")
            self.mismatch_listbox.delete(0, tk.END)

            for idx, entry in enumerate(po):
                msgid_placeholders = set(placeholder_pattern.findall(entry.msgid))
                msgstr_placeholders = set(placeholder_pattern.findall(entry.msgstr))

                if msgid_placeholders != msgstr_placeholders:
                    entry.flags.append('fuzzy')
                    if "Placeholder mismatch!" not in entry.comment:
                        entry.comment = (entry.comment + "\n" if entry.comment else "") + "Placeholder mismatch!"
                    self.mismatch_listbox.insert(tk.END, f"Line {idx + 1}: msgid: {entry.msgid} | msgstr: {entry.msgstr}")

            po.format()
            po.save(self.file_path, newline='\n')
            messagebox.showinfo("Success", "File saved successfully with fuzzy flags where needed.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = POEditorApp(root)
    root.mainloop()