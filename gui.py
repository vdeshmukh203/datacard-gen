#!/usr/bin/env python3
"""
gui.py — Tkinter graphical interface for datacard-gen
======================================================
Launch with:

    python gui.py

or via the installed console script::

    datacard-gen-gui

Requires the Python standard-library ``tkinter`` package.  It is included by
default on macOS and Windows.  On Debian/Ubuntu install it with::

    sudo apt install python3-tk

On Fedora/RHEL::

    sudo dnf install python3-tkinter
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path when run directly.
sys.path.insert(0, str(Path(__file__).parent))

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
except ImportError:
    sys.exit(
        "Error: tkinter is not available.\n"
        "  Debian/Ubuntu : sudo apt install python3-tk\n"
        "  Fedora/RHEL   : sudo dnf install python3-tkinter\n"
    )

import datacard_gen as dcg


class _App(tk.Tk):
    """Root Tk window for the datacard-gen GUI."""

    TITLE = "datacard-gen — Dataset Card Generator"
    MIN_W, MIN_H = 880, 640

    def __init__(self) -> None:
        super().__init__()
        self.title(self.TITLE)
        self.minsize(self.MIN_W, self.MIN_H)
        self._current_card: dcg.DataCard | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 5}

        # --- File selection -------------------------------------------
        file_frame = ttk.LabelFrame(self, text="Input File", padding=6)
        file_frame.pack(fill=tk.X, **pad)

        self._file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self._file_var, width=68).pack(
            side=tk.LEFT, padx=(0, 6), fill=tk.X, expand=True
        )
        ttk.Button(file_frame, text="Browse…", command=self._browse).pack(
            side=tk.LEFT
        )

        # --- Metadata -------------------------------------------------
        meta_frame = ttk.LabelFrame(self, text="Metadata", padding=6)
        meta_frame.pack(fill=tk.X, **pad)
        meta_frame.columnconfigure(1, weight=1)
        meta_frame.columnconfigure(3, weight=1)

        _fields = [
            ("Name",                   "name",        ""),
            ("Description",            "description", "A dataset generated automatically."),
            ("License (SPDX)",         "license",     "cc-by-4.0"),
            ("Source URL",             "source",      ""),
            ("Tags (comma-separated)", "tags",        ""),
            ("Version",                "version",     "1.0.0"),
        ]
        self._meta: dict[str, tk.StringVar] = {}
        for i, (label, key, default) in enumerate(_fields):
            row, col = divmod(i, 2)
            ttk.Label(meta_frame, text=label + ":").grid(
                row=row, column=col * 2, sticky=tk.E, padx=(6, 2), pady=3
            )
            var = tk.StringVar(value=default)
            self._meta[key] = var
            ttk.Entry(meta_frame, textvariable=var, width=34).grid(
                row=row, column=col * 2 + 1, sticky=tk.EW, padx=(0, 12), pady=3
            )

        # --- Controls -------------------------------------------------
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, **pad)

        ttk.Label(ctrl_frame, text="Output format:").pack(side=tk.LEFT)
        self._fmt_var = tk.StringVar(value="markdown")
        ttk.Combobox(
            ctrl_frame,
            textvariable=self._fmt_var,
            values=["markdown", "json"],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=(4, 20))

        for text, cmd in (
            ("Generate",    self._generate),
            ("Save…",  self._save),
            ("Clear",       self._clear),
        ):
            ttk.Button(ctrl_frame, text=text, command=cmd).pack(
                side=tk.LEFT, padx=(0, 6)
            )

        # --- Status bar -----------------------------------------------
        self._status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self._status_var, anchor=tk.W).pack(
            fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 4)
        )

        # --- Preview --------------------------------------------------
        out_frame = ttk.LabelFrame(self, text="Preview", padding=6)
        out_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self._preview = scrolledtext.ScrolledText(
            out_frame,
            wrap=tk.NONE,
            font=("Courier New", 10),
            state=tk.DISABLED,
        )
        self._preview.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Open dataset file",
            filetypes=[
                ("CSV files",  "*.csv"),
                ("JSON files", "*.json"),
                ("All files",  "*.*"),
            ],
        )
        if path:
            self._file_var.set(path)
            if not self._meta["name"].get():
                self._meta["name"].set(Path(path).stem)
            self._status_var.set(f"File selected: {path}")

    def _make_generator(self) -> dcg.DatacardGenerator:
        tags = [t.strip() for t in self._meta["tags"].get().split(",") if t.strip()]
        return dcg.DatacardGenerator(
            name=self._meta["name"].get() or "dataset",
            description=self._meta["description"].get(),
            license=self._meta["license"].get(),
            source=self._meta["source"].get(),
            tags=tags,
            version=self._meta["version"].get(),
        )

    def _generate(self) -> None:
        path_str = self._file_var.get().strip()
        if not path_str:
            messagebox.showwarning(
                "No file selected", "Please select an input CSV or JSON file."
            )
            return
        path = Path(path_str)
        if not path.is_file():
            messagebox.showerror("File not found", f"Cannot open:\n{path}")
            return
        try:
            card = self._make_generator().generate(path)
            self._current_card = card
            output = (
                card.to_json()
                if self._fmt_var.get() == "json"
                else card.to_markdown()
            )
            self._set_preview(output)
            self._status_var.set(
                f"Generated card for ‘{card.name}’  "
                f"({card.num_rows:,} rows × {card.num_cols} columns)."
            )
        except Exception as exc:
            messagebox.showerror("Generation failed", str(exc))
            self._status_var.set("Error during generation — see dialog for details.")

    def _save(self) -> None:
        content = self._get_preview()
        if not content:
            messagebox.showwarning("Nothing to save", "Generate a card first.")
            return
        ext = ".json" if self._fmt_var.get() == "json" else ".md"
        path = filedialog.asksaveasfilename(
            title="Save datacard",
            defaultextension=ext,
            filetypes=[
                ("Markdown", "*.md"),
                ("JSON",     "*.json"),
                ("All files","*.*"),
            ],
        )
        if path:
            Path(path).write_text(content, encoding="utf-8")
            self._status_var.set(f"Saved to {path}")
            messagebox.showinfo("Saved", f"Datacard saved to:\n{path}")

    def _clear(self) -> None:
        self._set_preview("")
        self._current_card = None
        self._status_var.set("Cleared.")

    # ------------------------------------------------------------------
    # Preview helpers
    # ------------------------------------------------------------------

    def _set_preview(self, text: str) -> None:
        self._preview.configure(state=tk.NORMAL)
        self._preview.delete("1.0", tk.END)
        self._preview.insert(tk.END, text)
        self._preview.configure(state=tk.DISABLED)

    def _get_preview(self) -> str:
        return self._preview.get("1.0", tk.END).strip()


def launch() -> None:
    """Launch the datacard-gen GUI (blocking until the window is closed)."""
    app = _App()
    app.mainloop()


if __name__ == "__main__":
    launch()
