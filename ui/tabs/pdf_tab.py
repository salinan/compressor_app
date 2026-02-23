import os

import customtkinter as ctk

from core import pdf_compressor
from ui.components import BaseTab, PathSelector


_PDF_SETTINGS = ["/screen", "/ebook", "/printer", "/prepress"]


class PdfTab(BaseTab):
    """Tab for compressing PDFs via Ghostscript."""

    def __init__(self, parent, config: dict, **kwargs):
        super().__init__(parent, config, tab_name="pdf", **kwargs)

    def _build_settings(self, frame: ctk.CTkFrame):
        cfg = self.config["pdf"]

        # Ghostscript path
        ctk.CTkLabel(frame, text="Ghostscript pad:", anchor="w").grid(
            row=0, column=0, padx=(10, 6), pady=3, sticky="w"
        )

        gs_row = ctk.CTkFrame(frame, fg_color="transparent")
        gs_row.grid(row=0, column=1, columnspan=2, padx=(0, 10), pady=3, sticky="ew")
        frame.columnconfigure(1, weight=1)

        self._gs_entry = ctk.CTkEntry(gs_row)
        self._gs_entry.insert(0, cfg.get("gs_path", pdf_compressor.DEFAULT_GS_PATH))
        self._gs_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._gs_entry.bind("<FocusOut>", self._check_gs_path)

        ctk.CTkButton(
            gs_row, text="...", width=36, command=self._browse_gs
        ).pack(side="left")

        # Warning label (hidden until GS path is invalid)
        self._gs_warning = ctk.CTkLabel(
            frame,
            text="Ghostscript niet gevonden op dit pad!",
            text_color="#e74c3c",
        )
        self._gs_warning.grid(row=1, column=0, columnspan=3, padx=10, sticky="w")
        self._gs_warning.grid_remove()

        # PDF settings dropdown
        ctk.CTkLabel(frame, text="PDF instelling:", anchor="w").grid(
            row=2, column=0, padx=(10, 6), pady=3, sticky="w"
        )
        current = cfg.get("pdf_settings", "/ebook")
        self._settings_var = ctk.StringVar(value=current)
        ctk.CTkOptionMenu(
            frame,
            values=_PDF_SETTINGS,
            variable=self._settings_var,
        ).grid(row=2, column=1, padx=6, pady=3, sticky="w")

        # Force checkbox
        self._force_var = ctk.BooleanVar(value=cfg.get("force", False))
        ctk.CTkCheckBox(
            frame,
            text="Force (herverwerk al verwerkte bestanden)",
            variable=self._force_var,
        ).grid(row=3, column=0, columnspan=3, padx=10, pady=3, sticky="w")

        # Validate GS path on startup
        self.after(100, self._check_gs_path)

    def _browse_gs(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("Uitvoerbare bestanden", "*.exe"), ("Alle bestanden", "*.*")]
        )
        if path:
            self._gs_entry.delete(0, "end")
            self._gs_entry.insert(0, path)
            self._check_gs_path()

    def _check_gs_path(self, _event=None):
        gs_path = self._gs_entry.get()
        if gs_path and not os.path.exists(gs_path):
            self._gs_warning.grid()
        else:
            self._gs_warning.grid_remove()

    def _get_run_kwargs(self) -> dict:
        gs_path = self._gs_entry.get()
        pdf_settings = self._settings_var.get()
        force = bool(self._force_var.get())

        self.config["pdf"].update({
            "path": self.path_selector.get(),
            "gs_path": gs_path,
            "pdf_settings": pdf_settings,
            "force": force,
        })

        return {
            "path": self.path_selector.get(),
            "gs_path": gs_path,
            "pdf_settings": pdf_settings,
            "force": force,
        }

    def _get_compressor_main(self):
        return pdf_compressor.main
