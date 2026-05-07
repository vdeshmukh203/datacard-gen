"""
Tkinter GUI for datacard-gen.

Launch with::

    datacard-gen-gui          # installed entry-point
    python -m datacard_gen.gui
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path
from typing import Optional

from .generator import DatacardGenerator
from .schema import DatacardSchema


# ---------------------------------------------------------------------------
# Palette (light & accessible)
# ---------------------------------------------------------------------------
_BG = "#f5f5f5"
_HEADER_BG = "#2563eb"
_HEADER_FG = "#ffffff"
_BTN_BG = "#2563eb"
_BTN_FG = "#ffffff"
_BTN_ACTIVE = "#1d4ed8"
_SAVE_BTN_BG = "#16a34a"
_SAVE_BTN_ACTIVE = "#15803d"
_WARN_FG = "#dc2626"
_MONO = ("Courier", 10) if tk.TkVersion >= 8.5 else ("Courier", 10)


class _LabeledEntry(tk.Frame):
    """A label + entry row."""

    def __init__(self, parent, label: str, default: str = "", width: int = 50, **kw):
        super().__init__(parent, bg=_BG, **kw)
        tk.Label(self, text=label, bg=_BG, width=14, anchor="w").pack(side=tk.LEFT)
        self.var = tk.StringVar(value=default)
        tk.Entry(self, textvariable=self.var, width=width).pack(side=tk.LEFT, fill=tk.X, expand=True)

    @property
    def value(self) -> str:
        return self.var.get().strip()


class DatacardApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("datacard-gen — Dataset Datacard Generator")
        self.resizable(True, True)
        self.configure(bg=_BG)
        self.minsize(700, 580)

        self._card = None
        self._file_path: Optional[Path] = None

        self._build_ui()
        self._center()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_header()
        self._build_file_row()
        self._build_metadata_frame()
        self._build_options_row()
        self._build_button_bar()
        self._build_preview()
        self._build_status_bar()

    def _build_header(self) -> None:
        hdr = tk.Frame(self, bg=_HEADER_BG, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="datacard-gen", font=("Helvetica", 16, "bold"),
                 bg=_HEADER_BG, fg=_HEADER_FG).pack(side=tk.LEFT, padx=16)
        tk.Label(hdr, text="Automated Dataset Documentation Card Generator",
                 bg=_HEADER_BG, fg=_HEADER_FG).pack(side=tk.LEFT)

    def _build_file_row(self) -> None:
        row = tk.Frame(self, bg=_BG, padx=12, pady=6)
        row.pack(fill=tk.X)
        tk.Label(row, text="Dataset file:", bg=_BG, width=14, anchor="w").pack(side=tk.LEFT)
        self._file_var = tk.StringVar()
        tk.Entry(row, textvariable=self._file_var, width=52,
                 state="readonly").pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(row, text="Browse…", command=self._browse,
                  bg=_BTN_BG, fg=_BTN_FG, activebackground=_BTN_ACTIVE,
                  relief=tk.FLAT, padx=8).pack(side=tk.LEFT)

    def _build_metadata_frame(self) -> None:
        frm = tk.LabelFrame(self, text="Metadata", bg=_BG, padx=10, pady=6)
        frm.pack(fill=tk.X, padx=12, pady=(0, 4))

        self._name = _LabeledEntry(frm, "Name", "My Dataset")
        self._name.pack(fill=tk.X, pady=2)

        tk.Label(frm, text="Description", bg=_BG, anchor="w").pack(fill=tk.X)
        self._desc = tk.Text(frm, height=3, wrap=tk.WORD)
        self._desc.insert("1.0", "A dataset generated automatically.")
        self._desc.pack(fill=tk.X, pady=(0, 4))

        self._license = _LabeledEntry(frm, "License", "cc-by-4.0", width=30)
        self._license.pack(fill=tk.X, pady=2)

        self._source = _LabeledEntry(frm, "Source URL", "", width=46)
        self._source.pack(fill=tk.X, pady=2)

        self._tags = _LabeledEntry(frm, "Tags", "", width=46)
        tk.Label(frm, text="  (comma-separated)", bg=_BG, fg="#6b7280",
                 font=("Helvetica", 8)).place(in_=self._tags, relx=1.0, x=-160, rely=0.5, anchor="w")
        self._tags.pack(fill=tk.X, pady=2)

        self._version = _LabeledEntry(frm, "Version", "1.0.0", width=16)
        self._version.pack(fill=tk.X, pady=2)

    def _build_options_row(self) -> None:
        row = tk.Frame(self, bg=_BG, padx=12, pady=4)
        row.pack(fill=tk.X)

        tk.Label(row, text="Output format:", bg=_BG).pack(side=tk.LEFT)
        self._fmt = tk.StringVar(value="markdown")
        for val, lbl in (("markdown", "Markdown"), ("json", "JSON")):
            tk.Radiobutton(row, text=lbl, variable=self._fmt, value=val,
                           bg=_BG).pack(side=tk.LEFT, padx=6)

        tk.Label(row, text="   Example rows:", bg=_BG).pack(side=tk.LEFT)
        self._num_examples = tk.IntVar(value=5)
        ttk.Spinbox(row, from_=0, to=20, textvariable=self._num_examples,
                    width=4).pack(side=tk.LEFT, padx=4)

    def _build_button_bar(self) -> None:
        bar = tk.Frame(self, bg=_BG, padx=12, pady=4)
        bar.pack(fill=tk.X)

        def btn(parent, text, cmd, bg=_BTN_BG, abg=_BTN_ACTIVE):
            return tk.Button(parent, text=text, command=cmd,
                             bg=bg, fg=_BTN_FG, activebackground=abg,
                             relief=tk.FLAT, padx=10, pady=4)

        btn(bar, "Generate", self._generate).pack(side=tk.LEFT, padx=(0, 6))
        btn(bar, "Save…", self._save,
            bg=_SAVE_BTN_BG, abg=_SAVE_BTN_ACTIVE).pack(side=tk.LEFT, padx=(0, 6))
        btn(bar, "Clear", self._clear).pack(side=tk.LEFT)

        self._valid_lbl = tk.Label(bar, text="", bg=_BG, fg=_WARN_FG, font=("Helvetica", 9))
        self._valid_lbl.pack(side=tk.RIGHT, padx=4)

    def _build_preview(self) -> None:
        frm = tk.LabelFrame(self, text="Preview", bg=_BG, padx=6, pady=6)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))
        self._preview = scrolledtext.ScrolledText(
            frm, wrap=tk.NONE, font=_MONO, state=tk.DISABLED,
        )
        self._preview.pack(fill=tk.BOTH, expand=True)
        xscroll = tk.Scrollbar(frm, orient=tk.HORIZONTAL, command=self._preview.xview)
        self._preview.configure(xscrollcommand=xscroll.set)
        xscroll.pack(fill=tk.X)

    def _build_status_bar(self) -> None:
        self._status = tk.Label(self, text="Ready", anchor="w", bd=1,
                                relief=tk.SUNKEN, bg="#e5e7eb", padx=6)
        self._status.pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select dataset file",
            filetypes=[
                ("Supported files", "*.csv *.json *.parquet *.arrow"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._file_path = Path(path)
            self._file_var.set(path)
            stem = self._file_path.stem
            if not self._name.value or self._name.value == "My Dataset":
                self._name.var.set(stem)
            self._set_status(f"Loaded: {self._file_path.name}")

    def _generate(self) -> None:
        if self._file_path is None or not self._file_path.is_file():
            messagebox.showerror("No file", "Please select a valid dataset file first.")
            return
        tags = [t.strip() for t in self._tags.value.split(",") if t.strip()]
        gen = DatacardGenerator(
            name=self._name.value or self._file_path.stem,
            description=self._desc.get("1.0", tk.END).strip(),
            license=self._license.value or "unknown",
            source=self._source.value,
            tags=tags,
            version=self._version.value or "1.0.0",
            num_examples=self._num_examples.get(),
        )
        try:
            self._card = gen.generate(self._file_path)
        except Exception as exc:
            messagebox.showerror("Generation failed", str(exc))
            return

        output = self._card.to_json() if self._fmt.get() == "json" else self._card.to_markdown()
        self._set_preview(output)

        schema = DatacardSchema()
        errs = schema.validate(self._card.to_dict())
        if errs:
            self._valid_lbl.config(
                text=f"⚠ {len(errs)} validation issue(s)",
                fg=_WARN_FG,
            )
            tips = "\n".join(str(e) for e in errs)
            self._set_status(f"Generated with warnings: {tips}")
        else:
            self._valid_lbl.config(text="✓ Valid", fg="#16a34a")
            self._set_status(
                f"Generated card for '{self._card.name}' "
                f"({self._card.num_rows:,} rows × {self._card.num_cols} cols)"
            )

    def _save(self) -> None:
        if self._card is None:
            messagebox.showinfo("Nothing to save", "Generate a datacard first.")
            return
        is_json = self._fmt.get() == "json"
        default_ext = ".json" if is_json else ".md"
        path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=[("JSON", "*.json")] if is_json else [("Markdown", "*.md"), ("Text", "*.txt")],
            initialfile=f"{self._card.name.replace(' ', '_')}_datacard{default_ext}",
        )
        if not path:
            return
        text = self._card.to_json() if is_json else self._card.to_markdown()
        Path(path).write_text(text, encoding="utf-8")
        self._set_status(f"Saved to {path}")

    def _clear(self) -> None:
        self._card = None
        self._file_path = None
        self._file_var.set("")
        self._name.var.set("My Dataset")
        self._desc.delete("1.0", tk.END)
        self._desc.insert("1.0", "A dataset generated automatically.")
        self._license.var.set("cc-by-4.0")
        self._source.var.set("")
        self._tags.var.set("")
        self._version.var.set("1.0.0")
        self._num_examples.set(5)
        self._set_preview("")
        self._valid_lbl.config(text="")
        self._set_status("Ready")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_preview(self, text: str) -> None:
        self._preview.config(state=tk.NORMAL)
        self._preview.delete("1.0", tk.END)
        self._preview.insert(tk.END, text)
        self._preview.config(state=tk.DISABLED)

    def _set_status(self, msg: str) -> None:
        self._status.config(text=msg)

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


def main() -> None:
    """Entry point for the ``datacard-gen-gui`` command."""
    app = DatacardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
