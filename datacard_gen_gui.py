#!/usr/bin/env python3
"""
datacard_gen_gui.py — Tkinter GUI for datacard-gen

Provides a point-and-click interface for generating Hugging Face-compatible
dataset datacards from CSV or JSON files.  Requires only the Python standard
library (tkinter is included in the CPython distribution).
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Ensure the top-level module is importable when running from the repo root.
sys.path.insert(0, str(Path(__file__).parent))
from datacard_gen import DatacardGenerator  # noqa: E402


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class DatacardGenApp:
    _LICENSES = [
        "cc-by-4.0", "cc-by-sa-4.0", "cc0-1.0", "mit", "apache-2.0",
        "gpl-3.0", "lgpl-3.0", "openrail", "other", "unknown",
    ]

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("datacard-gen — Dataset Datacard Generator")
        self.root.resizable(True, True)
        self._build_ui()
        self.root.minsize(860, 560)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── top bar: file picker ───────────────────────────────────────
        top = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        top.pack(fill=tk.X)

        ttk.Label(top, text="Input file (CSV / JSON):").pack(side=tk.LEFT)
        self.file_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.file_var, width=55).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Browse…", command=self._browse_file).pack(side=tk.LEFT)

        # ── middle: left settings pane + right output pane ────────────
        mid = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        left = ttk.LabelFrame(mid, text="Metadata", padding=10)
        right = ttk.LabelFrame(mid, text="Generated Datacard", padding=10)
        mid.add(left, weight=1)
        mid.add(right, weight=3)

        self._build_metadata_form(left)
        self._build_output_pane(right)

        # ── status bar ────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self.root, textvariable=self.status_var, anchor=tk.W,
                  relief=tk.SUNKEN).pack(fill=tk.X, side=tk.BOTTOM)

    def _build_metadata_form(self, parent: ttk.LabelFrame) -> None:
        fields = [
            ("Dataset name:",        "name_var",    "My Dataset"),
            ("Description:",         "desc_var",    "A dataset generated automatically."),
            ("Source URL:",          "source_var",  ""),
            ("Tags (comma-sep.):",   "tags_var",    ""),
            ("Version:",             "version_var", "1.0.0"),
        ]
        for row, (label, attr, default) in enumerate(fields):
            ttk.Label(parent, text=label).grid(row=row * 2, column=0, columnspan=2,
                                               sticky=tk.W, pady=(6, 0))
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            ttk.Entry(parent, textvariable=var, width=32).grid(
                row=row * 2 + 1, column=0, columnspan=2, sticky=tk.EW)

        # License dropdown
        base = len(fields) * 2
        ttk.Label(parent, text="License:").grid(row=base, column=0, columnspan=2,
                                                sticky=tk.W, pady=(6, 0))
        self.license_var = tk.StringVar(value="cc-by-4.0")
        ttk.Combobox(parent, textvariable=self.license_var,
                     values=self._LICENSES, state="normal", width=29).grid(
            row=base + 1, column=0, columnspan=2, sticky=tk.EW)

        # Output format
        ttk.Label(parent, text="Output format:").grid(row=base + 2, column=0, columnspan=2,
                                                      sticky=tk.W, pady=(10, 0))
        self.format_var = tk.StringVar(value="markdown")
        fmt = ttk.Frame(parent)
        fmt.grid(row=base + 3, column=0, columnspan=2, sticky=tk.W)
        ttk.Radiobutton(fmt, text="Markdown", variable=self.format_var, value="markdown").pack(side=tk.LEFT)
        ttk.Radiobutton(fmt, text="JSON",     variable=self.format_var, value="json").pack(side=tk.LEFT, padx=8)

        # Generate button
        ttk.Button(parent, text="⚙  Generate Datacard", command=self._generate).grid(
            row=base + 4, column=0, columnspan=2, pady=14, sticky=tk.EW)

        parent.columnconfigure(0, weight=1)

    def _build_output_pane(self, parent: ttk.LabelFrame) -> None:
        self.output_text = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD, font=("Courier", 10), state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btn_row, text="Copy to clipboard", command=self._copy).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Save to file…",     command=self._save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Clear",             command=self._clear).pack(side=tk.RIGHT, padx=4)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select dataset file",
            filetypes=[
                ("CSV files",  "*.csv"),
                ("JSON files", "*.json"),
                ("All files",  "*.*"),
            ],
        )
        if path:
            self.file_var.set(path)
            # Pre-fill dataset name from the filename stem if still default
            if self.name_var.get() in ("", "My Dataset"):
                self.name_var.set(Path(path).stem)
            self.status_var.set(f"Loaded: {path}")

    def _generate(self) -> None:
        file_path = self.file_var.get().strip()
        if not file_path:
            messagebox.showerror("No file selected", "Please browse to a CSV or JSON file first.")
            return
        path = Path(file_path)
        if not path.is_file():
            messagebox.showerror("File not found", f"Cannot find: {file_path}")
            return

        tags = [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
        gen = DatacardGenerator(
            name=self.name_var.get() or path.stem,
            description=self.desc_var.get(),
            license=self.license_var.get(),
            source=self.source_var.get(),
            tags=tags,
            version=self.version_var.get(),
        )
        try:
            card = gen.generate(path)
        except Exception as exc:
            messagebox.showerror("Generation failed", str(exc))
            return

        output = card.to_json() if self.format_var.get() == "json" else card.to_markdown()
        self._set_output(output)
        self.status_var.set(
            f"Generated: {card.num_rows:,} rows × {card.num_cols} columns — "
            f"{len(output):,} characters"
        )

    def _set_output(self, text: str) -> None:
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", text)
        self.output_text.config(state=tk.DISABLED)

    def _copy(self) -> None:
        content = self.output_text.get("1.0", tk.END)
        if content.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("Copied to clipboard.")
        else:
            messagebox.showinfo("Nothing to copy", "Generate a datacard first.")

    def _save(self) -> None:
        content = self.output_text.get("1.0", tk.END)
        if not content.strip():
            messagebox.showinfo("Nothing to save", "Generate a datacard first.")
            return
        fmt = self.format_var.get()
        ext = ".md" if fmt == "markdown" else ".json"
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("Markdown", "*.md"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if path:
            Path(path).write_text(content, encoding="utf-8")
            self.status_var.set(f"Saved to {path}")

    def _clear(self) -> None:
        self._set_output("")
        self.status_var.set("Ready.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    root = tk.Tk()

    # Apply a modern theme if available
    style = ttk.Style(root)
    for theme in ("clam", "alt", "default"):
        if theme in style.theme_names():
            style.theme_use(theme)
            break

    app = DatacardGenApp(root)  # noqa: F841
    root.mainloop()


if __name__ == "__main__":
    main()
