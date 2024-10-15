import tkinter as tk
from tkinter import filedialog, messagebox
import polib

class FuzzyFlagApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fuzzy Flag Setter")

        # File path display
        self.file_path_var = tk.StringVar()
        self.file_path_label = tk.Label(root, textvariable=self.file_path_var, width=50)
        self.file_path_label.grid(row=0, column=0, padx=10, pady=10)

        # Browse button
        self.browse_button = tk.Button(root, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=0, column=1, padx=10, pady=10)

        # Keyword input
        self.keyword_label = tk.Label(root, text="Keyword:")
        self.keyword_label.grid(row=1, column=0, padx=10, pady=5, sticky='e')
        self.keyword_entry = tk.Entry(root, width=30)
        self.keyword_entry.grid(row=1, column=1, padx=10, pady=5)

        # Save button
        self.save_button = tk.Button(root, text="Save", command=self.save_file)
        self.save_button.grid(row=2, column=0, columnspan=2, pady=10)

        # Placeholder for the PO file path
        self.po_file_path = None

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PO files", "*.po")])
        if file_path:
            self.po_file_path = file_path
            self.file_path_var.set(file_path)

    def save_file(self):
        if not self.po_file_path:
            messagebox.showwarning("Warning", "Please select a PO file first.")
            return

        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("Warning", "Please enter a keyword.")
            return

        try:
            po = polib.pofile(self.po_file_path)

            for entry in po:
                if keyword in entry.msgstr:
                    entry.flags.append('fuzzy')

            po.save()  # Overwrite the existing PO file
            messagebox.showinfo("Success", "File saved successfully with Fuzzy flags updated.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FuzzyFlagApp(root)
    root.mainloop()