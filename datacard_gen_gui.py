#!/usr/bin/env python3
"""
datacard_gen_gui — Tkinter GUI for DataCard Generator

Launch with:
    python datacard_gen_gui.py
    datacard-gen-gui          # after pip install
    datacard-gen --gui
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_generator():
    """Import DatacardGenerator; search the script's directory if needed."""
    try:
        from datacard_gen import DatacardGenerator
        return DatacardGenerator
    except ImportError:
        import importlib.util
        candidate = Path(__file__).parent / "datacard_gen.py"
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("datacard_gen", candidate)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.DatacardGenerator
        raise ImportError(
            "datacard_gen module not found. "
            "Run this script from the project root or install the package."
        )


# ---------------------------------------------------------------------------
# Labelled entry helper
# ---------------------------------------------------------------------------

def _labelled_entry(parent, label: str, default: str = "", width: int = 30) -> tk.StringVar:
    ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(6, 0))
    var = tk.StringVar(value=default)
    ttk.Entry(parent, textvariable=var, width=width).pack(fill=tk.X)
    return var


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class DataCardApp(tk.Tk):
    """Main GUI window for the DataCard Generator."""

    _PADX = 8
    _PADY = 6
    _LEFT_WIDTH = 330

    def __init__(self):
        super().__init__()
        self.title("DataCard Generator")
        self.geometry("1100x700")
        self.minsize(820, 520)
        self.resizable(True, True)
        self._card = None
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._apply_theme()

        outer = ttk.Frame(self, padding=self._PADX)
        outer.pack(fill=tk.BOTH, expand=True)

        pane = ttk.PanedWindow(outer, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(pane, width=self._LEFT_WIDTH)
        left_frame.pack_propagate(False)
        pane.add(left_frame, weight=0)

        right_frame = ttk.Frame(pane)
        pane.add(right_frame, weight=1)

        self._build_left(left_frame)
        self._build_right(right_frame)

    def _apply_theme(self):
        style = ttk.Style(self)
        available = style.theme_names()
        for preferred in ("clam", "alt", "default"):
            if preferred in available:
                style.theme_use(preferred)
                break
        style.configure("Generate.TButton", font=("", 10, "bold"), padding=6)
        style.configure("Status.TLabel", foreground="#555555")

    # ------------------------------------------------------------------
    # Left panel — inputs
    # ------------------------------------------------------------------

    def _build_left(self, parent):
        canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = ttk.Frame(canvas, padding=(self._PADX, self._PADY))
        win_id = canvas.create_window((0, 0), window=inner, anchor=tk.NW)

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(win_id, width=event.width)

        inner.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        self._build_file_section(inner)
        ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=self._PADY)
        self._build_metadata_section(inner)
        ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=self._PADY)
        self._build_format_section(inner)
        ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=self._PADY)
        self._build_action_section(inner)

    def _build_file_section(self, parent):
        ttk.Label(parent, text="Input CSV File", font=("", 9, "bold")).pack(anchor=tk.W)
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=(4, 0))
        self.file_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.file_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Browse…", command=self._browse).pack(side=tk.LEFT, padx=(4, 0))

    def _build_metadata_section(self, parent):
        ttk.Label(parent, text="Metadata", font=("", 9, "bold")).pack(anchor=tk.W)

        self.name_var = _labelled_entry(parent, "Dataset Name", "My Dataset")
        self.license_var = _labelled_entry(parent, "License (SPDX)", "cc-by-4.0")
        self.source_var = _labelled_entry(parent, "Source URL / Citation", "")
        self.tags_var = _labelled_entry(parent, "Tags (comma-separated)", "")
        self.version_var = _labelled_entry(parent, "Version", "1.0.0")

        ttk.Label(parent, text="Description").pack(anchor=tk.W, pady=(6, 0))
        desc_frame = ttk.Frame(parent)
        desc_frame.pack(fill=tk.X)
        self.desc_text = tk.Text(
            desc_frame, height=4, wrap=tk.WORD,
            font=("", 9), relief=tk.SOLID, borderwidth=1,
        )
        desc_scroll = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_scroll.set)
        desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.desc_text.pack(fill=tk.X)
        self.desc_text.insert("1.0", "A dataset generated automatically.")

    def _build_format_section(self, parent):
        ttk.Label(parent, text="Output Format", font=("", 9, "bold")).pack(anchor=tk.W)
        self.format_var = tk.StringVar(value="markdown")
        row = ttk.Frame(parent)
        row.pack(anchor=tk.W, pady=(4, 0))
        ttk.Radiobutton(row, text="Markdown", variable=self.format_var, value="markdown").pack(side=tk.LEFT)
        ttk.Radiobutton(row, text="JSON", variable=self.format_var, value="json").pack(side=tk.LEFT, padx=8)

    def _build_action_section(self, parent):
        ttk.Button(
            parent, text="Generate DataCard",
            command=self._generate, style="Generate.TButton",
        ).pack(fill=tk.X, pady=(4, 0))

        self.status_var = tk.StringVar(value="Ready — select a CSV file and click Generate.")
        ttk.Label(
            parent, textvariable=self.status_var,
            style="Status.TLabel", wraplength=self._LEFT_WIDTH - 24,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 0))

    # ------------------------------------------------------------------
    # Right panel — preview
    # ------------------------------------------------------------------

    def _build_right(self, parent):
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(header, text="Preview", font=("", 10, "bold")).pack(side=tk.LEFT)

        btn_row = ttk.Frame(header)
        btn_row.pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Save As…", command=self._save).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Copy", command=self._copy).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(btn_row, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=(4, 0))

        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.preview = tk.Text(
            text_frame,
            wrap=tk.NONE,
            font=("Courier", 10),
            relief=tk.FLAT,
            bg="#f9f9f9",
            state=tk.DISABLED,
            cursor="arrow",
        )
        vsb = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.preview.yview)
        hsb = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.preview.xview)
        self.preview.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.preview.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.file_var.set(path)
        stem = Path(path).stem
        if self.name_var.get() in ("", "My Dataset"):
            self.name_var.set(stem)

    def _generate(self):
        try:
            DatacardGenerator = _load_generator()
        except ImportError as exc:
            messagebox.showerror("Import Error", str(exc))
            return

        path_str = self.file_var.get().strip()
        if not path_str:
            messagebox.showwarning("No File Selected", "Please select a CSV file first.")
            return

        path = Path(path_str)
        if not path.is_file():
            messagebox.showerror("File Not Found", f"Cannot find:\n{path}")
            return

        tags = [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
        gen = DatacardGenerator(
            name=self.name_var.get().strip() or path.stem,
            description=self.desc_text.get("1.0", tk.END).strip() or "A dataset.",
            license=self.license_var.get().strip() or "unknown",
            source=self.source_var.get().strip(),
            tags=tags,
            version=self.version_var.get().strip() or "1.0.0",
        )

        try:
            self._card = gen.generate_from_csv(path)
        except Exception as exc:
            messagebox.showerror("Generation Error", str(exc))
            self.status_var.set(f"Error: {exc}")
            return

        output = (
            self._card.to_json()
            if self.format_var.get() == "json"
            else self._card.to_markdown()
        )
        self._set_preview(output)
        self.status_var.set(
            f"Done — {self._card.num_rows:,} rows × {self._card.num_cols} columns  "
            f"({self._card.num_cols} fields profiled)"
        )

    def _save(self):
        text = self._get_preview()
        if not text:
            messagebox.showinfo("Nothing to Save", "Generate a datacard first.")
            return
        fmt = self.format_var.get()
        ext = ".json" if fmt == "json" else ".md"
        default_name = (self.name_var.get() or "datacard").replace(" ", "_") + ext
        path = filedialog.asksaveasfilename(
            title="Save DataCard",
            defaultextension=ext,
            initialfile=default_name,
            filetypes=[("Markdown", "*.md"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(text, encoding="utf-8")
        self.status_var.set(f"Saved to {Path(path).name}")

    def _copy(self):
        text = self._get_preview()
        if not text:
            self.status_var.set("Nothing to copy — generate a datacard first.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Copied to clipboard.")

    def _clear(self):
        self._set_preview("")
        self._card = None
        self.status_var.set("Ready — select a CSV file and click Generate.")

    # ------------------------------------------------------------------
    # Preview helpers
    # ------------------------------------------------------------------

    def _set_preview(self, text: str):
        self.preview.config(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        if text:
            self.preview.insert("1.0", text)
        self.preview.config(state=tk.DISABLED)

    def _get_preview(self) -> str:
        return self.preview.get("1.0", tk.END).strip()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Launch the DataCard Generator GUI."""
    app = DataCardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
