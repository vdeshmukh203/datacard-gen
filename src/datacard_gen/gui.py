"""Graphical user interface for datacard-gen (stdlib tkinter, no extra dependencies)."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path
from typing import Optional

from .generator import DataCard, DatacardGenerator
from .schema import DatacardSchema


def launch_gui() -> None:
    """Create and run the GUI application (blocks until the window is closed)."""
    app = _DatacardApp()
    app.run()


class _DatacardApp:
    """Main application window."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("datacard-gen — Dataset Datacard Generator")
        self.root.geometry("960x720")
        self.root.minsize(720, 520)
        self._card: Optional[DataCard] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_input_frame()
        self._build_metadata_frame()
        self._build_action_bar()
        self._build_output_area()
        self._build_status_bar()

    def _build_input_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Input Dataset", padding=8)
        frame.pack(fill="x", padx=10, pady=(8, 4))

        self._csv_var = tk.StringVar()
        ttk.Label(frame, text="CSV file:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(frame, textvariable=self._csv_var, width=70).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ttk.Button(frame, text="Browse…", command=self._browse_csv).grid(
            row=0, column=2, padx=(4, 0)
        )
        frame.columnconfigure(1, weight=1)

    def _build_metadata_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Metadata", padding=8)
        frame.pack(fill="x", padx=10, pady=4)

        _fields = [
            ("Name:",             "_name_var",    "My Dataset"),
            ("Description:",      "_desc_var",    "A dataset generated automatically."),
            ("License (SPDX):",   "_license_var", "cc-by-4.0"),
            ("Source URL:",       "_source_var",  ""),
            ("Tags (comma-sep):", "_tags_var",    ""),
            ("Version:",          "_version_var", "1.0.0"),
        ]
        for i, (label, attr, default) in enumerate(_fields):
            setattr(self, attr, tk.StringVar(value=default))
            row, col_offset = divmod(i, 2)
            lbl_col = col_offset * 3
            ttk.Label(frame, text=label).grid(
                row=row, column=lbl_col, sticky="w", padx=(4, 2), pady=2
            )
            ttk.Entry(frame, textvariable=getattr(self, attr), width=36).grid(
                row=row, column=lbl_col + 1, sticky="ew", padx=(0, 12), pady=2
            )
        # Make entry columns stretchable
        for c in (1, 4):
            frame.columnconfigure(c, weight=1)

    def _build_action_bar(self) -> None:
        frame = ttk.Frame(self.root)
        frame.pack(fill="x", padx=10, pady=4)

        self._format_var = tk.StringVar(value="markdown")
        ttk.Label(frame, text="Format:").pack(side="left")
        ttk.Radiobutton(
            frame, text="Markdown", variable=self._format_var, value="markdown",
            command=self._refresh_output,
        ).pack(side="left", padx=(4, 2))
        ttk.Radiobutton(
            frame, text="JSON", variable=self._format_var, value="json",
            command=self._refresh_output,
        ).pack(side="left", padx=(0, 12))

        ttk.Button(frame, text="Generate", command=self._on_generate, width=14).pack(
            side="left", padx=2
        )
        ttk.Button(frame, text="Validate", command=self._on_validate, width=10).pack(
            side="left", padx=2
        )
        ttk.Separator(frame, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(frame, text="Save…", command=self._on_save, width=8).pack(
            side="left", padx=2
        )
        ttk.Button(frame, text="Clear", command=self._on_clear, width=8).pack(
            side="left", padx=2
        )

    def _build_output_area(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Output", padding=4)
        frame.pack(fill="both", expand=True, padx=10, pady=4)
        self._output = scrolledtext.ScrolledText(
            frame, wrap="word", font=("Courier", 10), state="disabled"
        )
        self._output.pack(fill="both", expand=True)

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Ready.")
        bar = ttk.Label(
            self.root, textvariable=self._status_var,
            relief="sunken", anchor="w", padding=(4, 2),
        )
        bar.pack(fill="x", padx=10, pady=(0, 6))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Open CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self._csv_var.set(path)
        stem = Path(path).stem
        if self._name_var.get() in ("", "My Dataset"):
            self._name_var.set(stem)

    def _make_generator(self) -> DatacardGenerator:
        tags = [t.strip() for t in self._tags_var.get().split(",") if t.strip()]
        return DatacardGenerator(
            name=self._name_var.get() or "dataset",
            description=self._desc_var.get() or "A dataset.",
            license=self._license_var.get() or "unknown",
            source=self._source_var.get(),
            tags=tags,
            version=self._version_var.get() or "1.0.0",
        )

    def _on_generate(self) -> None:
        csv_path = self._csv_var.get().strip()
        if not csv_path:
            messagebox.showerror("No input", "Please select a CSV file first.")
            return
        path = Path(csv_path)
        if not path.is_file():
            messagebox.showerror("File not found", f"Cannot find:\n{csv_path}")
            return
        try:
            self._card = self._make_generator().generate_from_csv(path)
            self._refresh_output()
            self._set_status(
                f"Generated: {self._card.num_rows:,} rows × {self._card.num_cols} columns."
            )
        except Exception as exc:
            messagebox.showerror("Generation error", str(exc))
            self._set_status(f"Error: {exc}")

    def _on_validate(self) -> None:
        if self._card is None:
            messagebox.showinfo("Nothing to validate", "Generate a datacard first.")
            return
        warnings = DatacardSchema.validate(self._card.to_dict())
        if warnings:
            messagebox.showwarning(
                "Validation warnings",
                "\n".join(f"• {w}" for w in warnings),
            )
            self._set_status(f"{len(warnings)} validation warning(s).")
        else:
            messagebox.showinfo("Validation passed", "No schema issues found.")
            self._set_status("Validation passed.")

    def _on_save(self) -> None:
        content = self._output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Nothing to save", "Generate a datacard first.")
            return
        fmt = self._format_var.get()
        ext = ".json" if fmt == "json" else ".md"
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[
                ("Markdown files", "*.md"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        Path(path).write_text(content, encoding="utf-8")
        self._set_status(f"Saved → {path}")

    def _on_clear(self) -> None:
        self._card = None
        self._set_output("")
        self._set_status("Cleared.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_output(self) -> None:
        if self._card is None:
            return
        text = (
            self._card.to_json()
            if self._format_var.get() == "json"
            else self._card.to_markdown()
        )
        self._set_output(text)

    def _set_output(self, text: str) -> None:
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.insert("1.0", text)
        self._output.configure(state="disabled")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    def run(self) -> None:
        self.root.mainloop()
