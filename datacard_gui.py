#!/usr/bin/env python3
"""
datacard_gui — Graphical interface for datacard-gen

Launch with:
    datacard-gen-gui        (after ``pip install -e .``)
    python datacard_gui.py
    datacard-gen --gui
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Allow running as a standalone script alongside datacard_gen.py.
try:
    from datacard_gen import DataCard, DatacardGenerator, __version__
except ImportError:
    import pathlib as _pathlib
    sys.path.insert(0, str(_pathlib.Path(__file__).parent))
    from datacard_gen import DataCard, DatacardGenerator, __version__


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
_BG = "#f5f5f5"
_HEADER_BG = "#2c3e50"
_HEADER_FG = "#ecf0f1"
_ACCENT = "#2980b9"
_BTN_FG = "#ffffff"
_ENTRY_BG = "#ffffff"
_PREVIEW_BG = "#1e1e1e"
_PREVIEW_FG = "#d4d4d4"
_FONT_BODY = ("Segoe UI", 10) if sys.platform == "win32" else ("Helvetica", 11)
_FONT_MONO = ("Consolas", 10) if sys.platform == "win32" else ("Courier", 11)
_FONT_TITLE = ("Segoe UI Bold", 13) if sys.platform == "win32" else ("Helvetica", 13, "bold")


class _LabelledEntry(ttk.Frame):
    """Label + Entry composite widget."""

    def __init__(self, parent: tk.Widget, label: str, **entry_kw: object) -> None:
        super().__init__(parent)
        ttk.Label(self, text=label, width=14, anchor="e").pack(side=tk.LEFT, padx=(0, 6))
        self._var = tk.StringVar()
        ttk.Entry(self, textvariable=self._var, **entry_kw).pack(  # type: ignore[arg-type]
            side=tk.LEFT, fill=tk.X, expand=True
        )

    @property
    def var(self) -> tk.StringVar:
        return self._var

    def get(self) -> str:
        return self._var.get()

    def set(self, value: str) -> None:
        self._var.set(value)


class DatacardApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"datacard-gen {__version__} — Dataset Card Generator")
        self.configure(bg=_BG)
        self.minsize(780, 640)
        self.resizable(True, True)
        self._card: DataCard | None = None
        self._build_ui()
        self._bind_shortcuts()

    # ------------------------------------------------------------------
    # UI construction

    def _build_ui(self) -> None:
        self._build_header()
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        self._build_file_row(main)
        self._build_metadata_frame(main)
        self._build_options_row(main)
        self._build_action_row(main)
        self._build_preview(main)
        self._build_statusbar()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=_HEADER_BG, height=48)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="  datacard-gen",
            bg=_HEADER_BG, fg=_HEADER_FG,
            font=_FONT_TITLE,
        ).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(
            header,
            text="Automated Dataset Documentation",
            bg=_HEADER_BG, fg="#95a5a6",
            font=_FONT_BODY,
        ).pack(side=tk.LEFT, pady=8)

    def _build_file_row(self, parent: ttk.Frame) -> None:
        row = ttk.LabelFrame(parent, text="Dataset File", padding=8)
        row.pack(fill=tk.X, pady=(0, 8))
        self._file_var = tk.StringVar()
        ttk.Entry(row, textvariable=self._file_var, font=_FONT_BODY).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
        )
        ttk.Button(row, text="Browse…", command=self._browse).pack(side=tk.LEFT)

    def _build_metadata_frame(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Metadata", padding=8)
        frame.pack(fill=tk.X, pady=(0, 8))

        self._name_entry = _LabelledEntry(frame, "Name:")
        self._name_entry.pack(fill=tk.X, pady=2)

        # Multi-line description
        desc_row = ttk.Frame(frame)
        desc_row.pack(fill=tk.X, pady=2)
        ttk.Label(desc_row, text="Description:", width=14, anchor="ne").pack(
            side=tk.LEFT, padx=(0, 6)
        )
        self._desc_text = tk.Text(
            desc_row, height=3, wrap=tk.WORD, font=_FONT_BODY, relief=tk.FLAT,
            bd=1, highlightthickness=1, highlightbackground="#cccccc",
        )
        self._desc_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._license_entry = _LabelledEntry(frame, "License:")
        self._license_entry.set("cc-by-4.0")
        self._license_entry.pack(fill=tk.X, pady=2)

        self._source_entry = _LabelledEntry(frame, "Source URL:")
        self._source_entry.pack(fill=tk.X, pady=2)

        self._version_entry = _LabelledEntry(frame, "Version:")
        self._version_entry.set("1.0.0")
        self._version_entry.pack(fill=tk.X, pady=2)

        self._tags_entry = _LabelledEntry(frame, "Tags:")
        self._tags_entry.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="(comma-separated)", foreground="#888888", font=("", 9)).pack(
            anchor="e"
        )

    def _build_options_row(self, parent: ttk.Frame) -> None:
        row = ttk.LabelFrame(parent, text="Output Format", padding=8)
        row.pack(fill=tk.X, pady=(0, 8))
        self._format_var = tk.StringVar(value="markdown")
        ttk.Radiobutton(row, text="Markdown (.md)", variable=self._format_var,
                        value="markdown", command=self._on_format_change).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(row, text="JSON (.json)", variable=self._format_var,
                        value="json", command=self._on_format_change).pack(side=tk.LEFT)

    def _build_action_row(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(
            row, text="Generate Card (Ctrl+Return)",
            command=self._generate,
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Save to File… (Ctrl+S)", command=self._save).pack(side=tk.RIGHT)

    def _build_preview(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Preview", padding=4)
        frame.pack(fill=tk.BOTH, expand=True)
        self._preview = scrolledtext.ScrolledText(
            frame,
            wrap=tk.NONE,
            font=_FONT_MONO,
            bg=_PREVIEW_BG,
            fg=_PREVIEW_FG,
            insertbackground=_PREVIEW_FG,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self._preview.pack(fill=tk.BOTH, expand=True)
        # Horizontal scroll
        xbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self._preview.xview)
        xbar.pack(fill=tk.X)
        self._preview.configure(xscrollcommand=xbar.set)

    def _build_statusbar(self) -> None:
        self._status_var = tk.StringVar(value="Ready.")
        bar = tk.Label(
            self, textvariable=self._status_var,
            anchor="w", bg="#dde3ea", fg="#333333",
            font=("", 9), padx=8, pady=3,
        )
        bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-Return>", lambda _e: self._generate())
        self.bind("<Control-s>", lambda _e: self._save())
        self.bind("<Control-o>", lambda _e: self._browse())

    # ------------------------------------------------------------------
    # Callbacks

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select dataset file",
            filetypes=[
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self._file_var.set(path)
        if not self._name_entry.get():
            self._name_entry.set(Path(path).stem)
        self._set_status(f"Loaded: {path}")

    def _generate(self) -> None:
        path_str = self._file_var.get().strip()
        if not path_str:
            messagebox.showerror("No file selected", "Please select a dataset file first.")
            return
        path = Path(path_str)
        if not path.is_file():
            messagebox.showerror("File not found", f"Cannot find file:\n{path_str}")
            return

        tags = [t.strip() for t in self._tags_entry.get().split(",") if t.strip()]
        desc = self._desc_text.get("1.0", tk.END).strip() or "A dataset."
        gen = DatacardGenerator(
            name=self._name_entry.get() or path.stem,
            description=desc,
            license=self._license_entry.get() or "unknown",
            source=self._source_entry.get(),
            tags=tags,
            version=self._version_entry.get() or "1.0.0",
        )

        self._set_status("Generating…")
        self.update_idletasks()
        try:
            self._card = gen.generate(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Generation failed", str(exc))
            self._set_status("Error.")
            return

        output = (
            self._card.to_json()
            if self._format_var.get() == "json"
            else self._card.to_markdown()
        )
        self._set_preview(output)
        self._set_status(
            f"Generated — {self._card.num_rows:,} rows × {self._card.num_cols} columns."
        )

    def _on_format_change(self) -> None:
        if self._card is None:
            return
        output = (
            self._card.to_json()
            if self._format_var.get() == "json"
            else self._card.to_markdown()
        )
        self._set_preview(output)

    def _clear(self) -> None:
        self._file_var.set("")
        self._name_entry.set("")
        self._desc_text.delete("1.0", tk.END)
        self._license_entry.set("cc-by-4.0")
        self._source_entry.set("")
        self._version_entry.set("1.0.0")
        self._tags_entry.set("")
        self._set_preview("")
        self._card = None
        self._set_status("Cleared.")

    def _save(self) -> None:
        if self._card is None:
            messagebox.showwarning("Nothing to save", "Generate a card first.")
            return
        fmt = self._format_var.get()
        ext = ".json" if fmt == "json" else ".md"
        default_name = (self._card.name or "datacard").replace(" ", "_") + ext
        path = filedialog.asksaveasfilename(
            title="Save datacard",
            initialfile=default_name,
            defaultextension=ext,
            filetypes=[
                ("Markdown", "*.md"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        content = self._preview.get("1.0", tk.END)
        Path(path).write_text(content, encoding="utf-8")
        self._set_status(f"Saved to {path}")
        messagebox.showinfo("Saved", f"Datacard saved to:\n{path}")

    # ------------------------------------------------------------------
    # Helpers

    def _set_preview(self, text: str) -> None:
        self._preview.configure(state=tk.NORMAL)
        self._preview.delete("1.0", tk.END)
        if text:
            self._preview.insert("1.0", text)
        self._preview.configure(state=tk.DISABLED)

    def _set_status(self, message: str) -> None:
        self._status_var.set(message)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Launch the datacard-gen GUI."""
    app = DatacardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
