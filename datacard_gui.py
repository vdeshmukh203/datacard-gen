#!/usr/bin/env python3
"""
datacard_gui — Tkinter GUI for datacard-gen

Launch with:
    python datacard_gui.py
    datacard-gen --gui
    datacard-gen-gui
"""

from __future__ import annotations

import sys
import pathlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import datacard_gen as dcg


# ---------------------------------------------------------------------------
# Colour / style constants
# ---------------------------------------------------------------------------
_BG = "#1e1e2e"
_FG = "#cdd6f4"
_ACCENT = "#89b4fa"
_BTN_BG = "#313244"
_BTN_ACT = "#45475a"
_ENTRY_BG = "#181825"
_TAB_BG = "#11111b"
_MONO = ("Courier New", 10) if sys.platform == "win32" else ("Monospace", 10)
_SANS = ("Segoe UI", 10) if sys.platform == "win32" else ("Sans", 10)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _styled_button(parent, text: str, command, width: int = 14) -> tk.Button:
    return tk.Button(
        parent, text=text, command=command,
        bg=_BTN_BG, fg=_FG, activebackground=_BTN_ACT, activeforeground=_FG,
        relief="flat", padx=8, pady=4, cursor="hand2", width=width,
        font=_SANS,
    )


def _labeled_entry(parent, label: str, row: int, default: str = "") -> tk.Entry:
    tk.Label(parent, text=label, bg=_BG, fg=_FG, font=_SANS, anchor="w").grid(
        row=row, column=0, sticky="w", padx=(0, 8), pady=3
    )
    var = tk.StringVar(value=default)
    e = tk.Entry(parent, textvariable=var, bg=_ENTRY_BG, fg=_FG,
                 insertbackground=_FG, relief="flat", font=_SANS)
    e.grid(row=row, column=1, sticky="ew", pady=3)
    return e


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class DatacardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("datacard-gen  —  Dataset Documentation Generator")
        self.configure(bg=_BG)
        self.minsize(900, 620)
        self.resizable(True, True)

        self._csv_path: pathlib.Path | None = None
        self._card: dcg.DataCard | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_body()
        self._build_statusbar()

    def _build_topbar(self):
        bar = tk.Frame(self, bg="#11111b", pady=6)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        tk.Label(bar, text=" datacard-gen", bg="#11111b", fg=_ACCENT,
                 font=("Sans", 13, "bold")).grid(row=0, column=0, padx=10)

        file_frame = tk.Frame(bar, bg="#11111b")
        file_frame.grid(row=0, column=1, sticky="ew", padx=10)
        file_frame.columnconfigure(0, weight=1)

        self._file_var = tk.StringVar(value="No file selected")
        tk.Entry(file_frame, textvariable=self._file_var, state="readonly",
                 bg=_ENTRY_BG, fg=_FG, readonlybackground=_ENTRY_BG,
                 relief="flat", font=_SANS).grid(row=0, column=0, sticky="ew")

        _styled_button(bar, "Browse CSV…", self._browse_csv, width=12).grid(
            row=0, column=2, padx=(0, 10)
        )

    def _build_body(self):
        body = tk.Frame(self, bg=_BG)
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent):
        left = tk.Frame(parent, bg=_BG, width=260)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left.columnconfigure(1, weight=1)
        left.grid_propagate(False)

        tk.Label(left, text="Dataset Metadata", bg=_BG, fg=_ACCENT,
                 font=("Sans", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        self._name_e = _labeled_entry(left, "Name:", 1, "My Dataset")
        self._license_e = _labeled_entry(left, "License:", 2, "cc-by-4.0")
        self._version_e = _labeled_entry(left, "Version:", 3, "1.0.0")
        self._source_e = _labeled_entry(left, "Source:", 4, "")
        self._tags_e = _labeled_entry(left, "Tags:", 5, "")
        tk.Label(left, text="(comma-separated)", bg=_BG, fg="#585b70",
                 font=("Sans", 8)).grid(row=6, column=1, sticky="w")

        tk.Label(left, text="Description:", bg=_BG, fg=_FG,
                 font=_SANS, anchor="nw").grid(row=7, column=0, sticky="nw", pady=(8, 0))
        self._desc_t = tk.Text(left, height=5, bg=_ENTRY_BG, fg=_FG,
                               insertbackground=_FG, relief="flat", font=_SANS, wrap="word")
        self._desc_t.grid(row=7, column=1, sticky="ew", pady=(8, 0))
        self._desc_t.insert("1.0", "A dataset generated automatically.")

        btn_frame = tk.Frame(left, bg=_BG)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(16, 0), sticky="ew")

        _styled_button(btn_frame, "Generate", self._generate, width=12).pack(
            side="left", padx=(0, 6)
        )
        _styled_button(btn_frame, "Clear", self._clear_output, width=8).pack(side="left")

    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg=_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        tk.Label(right, text="Output", bg=_BG, fg=_ACCENT,
                 font=("Sans", 11, "bold")).grid(row=0, column=0, sticky="w")

        nb = ttk.Notebook(right)
        nb.grid(row=1, column=0, sticky="nsew")
        right.rowconfigure(1, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=_TAB_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=_BTN_BG, foreground=_FG,
                        padding=[10, 4])
        style.map("TNotebook.Tab", background=[("selected", _BG)])

        self._md_text = self._make_text_tab(nb, "Markdown")
        self._json_text = self._make_text_tab(nb, "JSON")

        btn_row = tk.Frame(right, bg=_BG)
        btn_row.grid(row=2, column=0, sticky="e", pady=(6, 0))

        _styled_button(btn_row, "Copy", self._copy_output, width=8).pack(
            side="left", padx=(0, 6)
        )
        _styled_button(btn_row, "Save…", self._save_output, width=8).pack(side="left")

        self._nb = nb

    def _make_text_tab(self, nb: ttk.Notebook, label: str) -> tk.Text:
        frame = tk.Frame(nb, bg=_TAB_BG)
        nb.add(frame, text=label)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        sb = tk.Scrollbar(frame, orient="vertical")
        sb.grid(row=0, column=1, sticky="ns")

        t = tk.Text(
            frame, bg=_TAB_BG, fg=_FG, insertbackground=_FG,
            relief="flat", font=_MONO, wrap="none",
            yscrollcommand=sb.set,
        )
        t.grid(row=0, column=0, sticky="nsew")
        sb.config(command=t.yview)
        return t

    def _build_statusbar(self):
        bar = tk.Frame(self, bg="#11111b", pady=3)
        bar.grid(row=2, column=0, sticky="ew")
        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(bar, textvariable=self._status_var, bg="#11111b", fg="#585b70",
                 font=("Sans", 9), anchor="w").pack(side="left", padx=10)
        tk.Label(bar, text=f"datacard-gen v{dcg.__version__}",
                 bg="#11111b", fg="#585b70", font=("Sans", 9)).pack(side="right", padx=10)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self._csv_path = pathlib.Path(path)
            self._file_var.set(str(self._csv_path))
            self._status_var.set(f"Loaded: {self._csv_path.name}")
            if not self._name_e.get().strip() or self._name_e.get() == "My Dataset":
                self._name_e.delete(0, "end")
                self._name_e.insert(0, self._csv_path.stem)

    def _generate(self):
        if self._csv_path is None or not self._csv_path.is_file():
            messagebox.showerror("No file", "Please select a valid CSV file first.")
            return

        tags = [t.strip() for t in self._tags_e.get().split(",") if t.strip()]
        gen = dcg.DatacardGenerator(
            name=self._name_e.get().strip() or self._csv_path.stem,
            description=self._desc_t.get("1.0", "end-1c").strip(),
            license=self._license_e.get().strip() or "unknown",
            source=self._source_e.get().strip(),
            tags=tags,
            version=self._version_e.get().strip() or "1.0.0",
        )
        try:
            self._card = gen.generate_from_csv(self._csv_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to generate datacard:\n{exc}")
            return

        md = self._card.to_markdown()
        js = self._card.to_json()

        for widget, text in ((self._md_text, md), (self._json_text, js)):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", text)
            widget.config(state="disabled")

        self._status_var.set(
            f"Generated — {self._card.num_rows:,} rows × {self._card.num_cols} columns"
        )

    def _clear_output(self):
        for widget in (self._md_text, self._json_text):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.config(state="disabled")
        self._card = None
        self._status_var.set("Cleared.")

    def _current_output(self) -> str:
        tab_idx = self._nb.index(self._nb.select())
        widget = self._md_text if tab_idx == 0 else self._json_text
        return widget.get("1.0", "end-1c")

    def _copy_output(self):
        text = self._current_output()
        if not text:
            messagebox.showinfo("Nothing to copy", "Generate a datacard first.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status_var.set("Copied to clipboard.")

    def _save_output(self):
        text = self._current_output()
        if not text:
            messagebox.showinfo("Nothing to save", "Generate a datacard first.")
            return
        tab_idx = self._nb.index(self._nb.select())
        is_md = tab_idx == 0
        default_ext = ".md" if is_md else ".json"
        default_name = (
            f"{(self._csv_path.stem if self._csv_path else 'datacard')}{default_ext}"
        )
        path = filedialog.asksaveasfilename(
            title="Save datacard",
            defaultextension=default_ext,
            initialfile=default_name,
            filetypes=[
                ("Markdown", "*.md"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if path:
            pathlib.Path(path).write_text(text, encoding="utf-8")
            self._status_var.set(f"Saved to {pathlib.Path(path).name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def launch_gui():
    """Start the Tkinter GUI event loop."""
    app = DatacardApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
