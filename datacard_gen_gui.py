#!/usr/bin/env python3
"""
datacard_gen_gui.py — Tkinter GUI for the Datacard Generator.

Run with::

    python datacard_gen_gui.py
    python -m datacard_gen.gui   # when installed as a package

Stdlib-only; no external dependencies required.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional

# Allow running directly alongside datacard_gen.py.
sys.path.insert(0, str(Path(__file__).parent))
from datacard_gen import DatacardGenerator


_LICENSES = [
    "cc-by-4.0",
    "cc-by-sa-4.0",
    "cc-by-nc-4.0",
    "cc0-1.0",
    "apache-2.0",
    "mit",
    "gpl-3.0",
    "other",
    "unknown",
]


class _App:
    """Main application window for the Datacard Generator GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Datacard Generator")
        self.root.minsize(780, 640)
        self._csv_path: Optional[Path] = None
        self._last_output: str = ""
        self._build_ui()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=12)
        main.grid(sticky="nsew")
        main.columnconfigure(1, weight=1)

        row = self._file_row(main, 0)
        row = self._separator(main, row)
        row = self._metadata_rows(main, row)
        row = self._separator(main, row)
        row = self._format_row(main, row)
        row = self._button_row(main, row)
        row = self._preview_area(main, row)
        self._status_bar(main, row)

    def _file_row(self, parent: ttk.Frame, row: int) -> int:
        ttk.Label(parent, text="CSV file:").grid(row=row, column=0, sticky="w", pady=3)
        self._file_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self._file_var, state="readonly").grid(
            row=row, column=1, sticky="ew", padx=4
        )
        ttk.Button(parent, text="Browse…", command=self._browse).grid(row=row, column=2)
        return row + 1

    def _separator(self, parent: ttk.Frame, row: int) -> int:
        ttk.Separator(parent, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=8
        )
        return row + 1

    def _metadata_rows(self, parent: ttk.Frame, row: int) -> int:
        meta = [
            ("Dataset name:", "_name_var", "My Dataset"),
            ("Description:", "_desc_var", "A dataset generated automatically."),
            ("Source URL:", "_source_var", ""),
            ("Tags (comma-sep):", "_tags_var", ""),
            ("Version:", "_version_var", "1.0.0"),
        ]
        for label, attr, default in meta:
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            ttk.Entry(parent, textvariable=var).grid(
                row=row, column=1, columnspan=2, sticky="ew", padx=4
            )
            row += 1

        # License drop-down
        ttk.Label(parent, text="License:").grid(row=row, column=0, sticky="w", pady=2)
        self._license_var = tk.StringVar(value="cc-by-4.0")
        ttk.Combobox(
            parent,
            textvariable=self._license_var,
            values=_LICENSES,
            state="normal",
        ).grid(row=row, column=1, columnspan=2, sticky="ew", padx=4)
        return row + 1

    def _format_row(self, parent: ttk.Frame, row: int) -> int:
        ttk.Label(parent, text="Output format:").grid(row=row, column=0, sticky="w")
        self._format_var = tk.StringVar(value="markdown")
        rf = ttk.Frame(parent)
        rf.grid(row=row, column=1, sticky="w", padx=4)
        ttk.Radiobutton(rf, text="Markdown", variable=self._format_var, value="markdown").pack(
            side="left"
        )
        ttk.Radiobutton(rf, text="JSON", variable=self._format_var, value="json").pack(
            side="left", padx=(12, 0)
        )
        return row + 1

    def _button_row(self, parent: ttk.Frame, row: int) -> int:
        bf = ttk.Frame(parent)
        bf.grid(row=row, column=0, columnspan=3, pady=10)
        ttk.Button(bf, text="Generate", command=self._generate).pack(side="left", padx=4)
        ttk.Button(bf, text="Save…", command=self._save).pack(side="left", padx=4)
        ttk.Button(bf, text="Clear", command=self._clear).pack(side="left", padx=4)
        return row + 1

    def _preview_area(self, parent: ttk.Frame, row: int) -> int:
        ttk.Label(parent, text="Preview:").grid(row=row, column=0, sticky="w")
        row += 1
        self._preview = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD, height=18, font=("Courier New", 10)
        )
        self._preview.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        parent.rowconfigure(row, weight=1)
        return row + 1

    def _status_bar(self, parent: ttk.Frame, row: int) -> None:
        self._status_var = tk.StringVar(value="Ready — select a CSV file and click Generate.")
        ttk.Label(parent, textvariable=self._status_var, foreground="gray").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

    # ------------------------------------------------------------------ #
    #  Callbacks                                                           #
    # ------------------------------------------------------------------ #

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self._csv_path = Path(path)
        self._file_var.set(path)
        if self._name_var.get() in ("", "My Dataset"):
            self._name_var.set(self._csv_path.stem)
        self._status_var.set(f"Loaded: {path}")

    def _make_generator(self) -> DatacardGenerator:
        tags = [t.strip() for t in self._tags_var.get().split(",") if t.strip()]
        return DatacardGenerator(
            name=self._name_var.get() or "dataset",
            description=self._desc_var.get(),
            license=self._license_var.get(),
            source=self._source_var.get(),
            tags=tags,
            version=self._version_var.get(),
        )

    def _generate(self) -> None:
        if not self._csv_path or not self._csv_path.is_file():
            messagebox.showwarning("No file", "Please select a CSV file first.")
            return
        try:
            card = self._make_generator().generate_from_csv(self._csv_path)
            self._last_output = (
                card.to_json() if self._format_var.get() == "json" else card.to_markdown()
            )
            self._preview.delete("1.0", tk.END)
            self._preview.insert(tk.END, self._last_output)
            self._status_var.set(
                f"Generated — {self._csv_path.name}: "
                f"{card.num_rows:,} rows, {card.num_cols} columns"
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self._status_var.set(f"Error: {exc}")

    def _save(self) -> None:
        if not self._last_output:
            messagebox.showwarning("Nothing to save", "Generate a datacard first.")
            return
        ext = ".md" if self._format_var.get() == "markdown" else ".json"
        path = filedialog.asksaveasfilename(
            title="Save datacard",
            defaultextension=ext,
            filetypes=[("Markdown", "*.md"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if path:
            Path(path).write_text(self._last_output, encoding="utf-8")
            self._status_var.set(f"Saved to {path}")

    def _clear(self) -> None:
        self._preview.delete("1.0", tk.END)
        self._last_output = ""
        self._status_var.set("Cleared.")


# ── Entry point ───────────────────────────────────────────────────────────── #

def main() -> None:
    """Launch the Datacard Generator GUI."""
    root = tk.Tk()
    _App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
