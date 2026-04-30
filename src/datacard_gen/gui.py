#!/usr/bin/env python3
"""
Tkinter GUI for datacard-gen.

Launch with:
    datacard-gen-gui
or from Python:
    from datacard_gen.gui import launch_gui; launch_gui()
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .generator import DatacardGenerator
from .schema import DatacardSchema


class _MetaFrame(ttk.LabelFrame):
    """Left panel: dataset file picker + metadata fields."""

    FIELDS = [
        ("Name", "_name", "My Dataset"),
        ("Description", "_desc", "A dataset."),
        ("License", "_lic", "cc-by-4.0"),
        ("Source / URL", "_src", ""),
        ("Tags (comma-sep)", "_tags", ""),
        ("Version", "_ver", "1.0.0"),
    ]

    def __init__(self, master, **kw):
        super().__init__(master, text="Dataset & Metadata", padding=10, **kw)
        self.columnconfigure(1, weight=1)
        self._build()

    def _build(self):
        ttk.Label(self, text="File:").grid(row=0, column=0, sticky="w", pady=3)
        self.file_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.file_var).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Button(self, text="Browse…", command=self._browse).grid(row=0, column=2, padx=(6, 0))

        self._vars: dict[str, tk.StringVar] = {}
        for i, (label, attr, default) in enumerate(self.FIELDS, start=1):
            ttk.Label(self, text=f"{label}:").grid(row=i, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=default)
            self._vars[attr] = var
            ttk.Entry(self, textvariable=var).grid(row=i, column=1, columnspan=2, sticky="ew", padx=(6, 0))

        row = len(self.FIELDS) + 1
        ttk.Label(self, text="Format:").grid(row=row, column=0, sticky="w", pady=3)
        self.fmt_var = tk.StringVar(value="markdown")
        fmt_frame = ttk.Frame(self)
        fmt_frame.grid(row=row, column=1, sticky="w", padx=(6, 0))
        ttk.Radiobutton(fmt_frame, text="Markdown", variable=self.fmt_var, value="markdown").pack(side="left")
        ttk.Radiobutton(fmt_frame, text="JSON", variable=self.fmt_var, value="json").pack(
            side="left", padx=(12, 0)
        )

        self.validate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Validate card", variable=self.validate_var).grid(
            row=row + 1, column=1, sticky="w", padx=(6, 0), pady=(6, 0)
        )

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select dataset file",
            filetypes=[
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.file_var.set(path)
            stem = Path(path).stem
            if self._vars["_name"].get() in ("My Dataset", ""):
                self._vars["_name"].set(stem)

    # ------------------------------------------------------------------ #
    # Public accessors
    # ------------------------------------------------------------------ #

    @property
    def file_path(self) -> str:
        return self.file_var.get().strip()

    def build_generator(self) -> DatacardGenerator:
        tags = [t.strip() for t in self._vars["_tags"].get().split(",") if t.strip()]
        return DatacardGenerator(
            name=self._vars["_name"].get() or "dataset",
            description=self._vars["_desc"].get() or "A dataset.",
            license=self._vars["_lic"].get() or "unknown",
            source=self._vars["_src"].get(),
            tags=tags,
            version=self._vars["_ver"].get() or "1.0.0",
        )


class DatacardApp(tk.Tk):
    """Main application window."""

    _MIN_W, _MIN_H = 900, 660

    def __init__(self):
        super().__init__()
        self.title("datacard-gen  ·  Dataset Documentation Card Generator")
        self.minsize(self._MIN_W, self._MIN_H)
        self.geometry(f"{self._MIN_W}x{self._MIN_H}")
        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── metadata panel ──────────────────────────────────────────────
        self._meta = _MetaFrame(self)
        self._meta.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        # ── button toolbar ───────────────────────────────────────────────
        toolbar = ttk.Frame(self)
        toolbar.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        ttk.Button(toolbar, text="⚡  Generate", command=self._generate).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="💾  Save…", command=self._save).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="✕  Clear", command=self._clear).pack(side="left")
        ttk.Button(toolbar, text="Copy", command=self._copy).pack(side="right")

        # ── output area ──────────────────────────────────────────────────
        out_frame = ttk.LabelFrame(self, text="Generated Card", padding=4)
        out_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=1)

        self._output = scrolledtext.ScrolledText(
            out_frame, wrap=tk.WORD, font=("Courier New", 10), state="disabled"
        )
        self._output.grid(row=0, column=0, sticky="nsew")

        # ── status bar ───────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(
            self, textvariable=self._status_var,
            relief="sunken", anchor="w", padding=(6, 2),
        )
        status_bar.grid(row=3, column=0, sticky="ew")

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def _generate(self):
        file_path = self._meta.file_path
        if not file_path:
            messagebox.showerror("No file selected", "Please select a CSV or JSON file.")
            return

        path = Path(file_path)
        if not path.is_file():
            messagebox.showerror("File not found", f"Cannot find:\n{file_path}")
            return

        gen = self._meta.build_generator()
        try:
            card = gen.generate(path)
        except Exception as exc:
            messagebox.showerror("Error reading file", str(exc))
            return

        if self._meta.validate_var.get():
            result = DatacardSchema().validate(card)
            if not result.valid:
                messagebox.showwarning(
                    "Validation errors",
                    "The card has errors that should be fixed:\n\n"
                    + "\n".join(f"• {e}" for e in result.errors),
                )
            elif result.warnings:
                messagebox.showinfo(
                    "Validation warnings",
                    "Consider addressing these quality warnings:\n\n"
                    + "\n".join(f"• {w}" for w in result.warnings),
                )

        text = card.to_json() if self._meta.fmt_var.get() == "json" else card.to_markdown()
        self._set_output(text)
        self._status_var.set(
            f"✔  Generated card for '{card.name}'  "
            f"({card.num_rows:,} rows · {card.num_cols} columns)"
        )

    def _save(self):
        content = self._output.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Nothing to save", "Generate a card first.")
            return
        ext = ".json" if self._meta.fmt_var.get() == "json" else ".md"
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("Markdown", "*.md"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if path:
            Path(path).write_text(content, encoding="utf-8")
            self._status_var.set(f"Saved → {path}")

    def _clear(self):
        self._set_output("")
        self._status_var.set("Cleared.")

    def _copy(self):
        content = self._output.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self._status_var.set("Copied to clipboard.")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _set_output(self, text: str):
        self._output.configure(state="normal")
        self._output.delete("1.0", tk.END)
        if text:
            self._output.insert(tk.END, text)
        self._output.configure(state="disabled")


def launch_gui() -> None:
    """Entry point for the ``datacard-gen-gui`` command."""
    app = DatacardApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
