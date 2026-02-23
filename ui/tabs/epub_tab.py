import customtkinter as ctk

from core import epub_compressor
from ui.components import BaseTab, make_quality_row


class EpubTab(BaseTab):
    """Tab for compressing images inside EPUB archives."""

    def __init__(self, parent, config: dict, **kwargs):
        super().__init__(parent, config, tab_name="epub", **kwargs)

    def _build_settings(self, frame: ctk.CTkFrame):
        cfg = self.config["epub"]

        # Target height
        ctk.CTkLabel(frame, text="Doelhoogte (px):", anchor="w").grid(
            row=0, column=0, padx=(10, 6), pady=3, sticky="w"
        )
        self._height_entry = ctk.CTkEntry(frame, width=80)
        self._height_entry.insert(0, str(cfg.get("target_height", 450)))
        self._height_entry.grid(row=0, column=1, padx=6, pady=3, sticky="w")

        # Quality slider
        self._quality_slider = make_quality_row(frame, row=1, default_value=cfg.get("quality", 65))

        # Force checkbox
        self._force_var = ctk.BooleanVar(value=cfg.get("force", False))
        ctk.CTkCheckBox(
            frame,
            text="Force (herverwerk al verwerkte bestanden)",
            variable=self._force_var,
        ).grid(row=2, column=0, columnspan=3, padx=10, pady=3, sticky="w")

    def _get_run_kwargs(self) -> dict:
        try:
            height = int(self._height_entry.get())
        except ValueError:
            height = 450

        quality = int(self._quality_slider.get())
        force = bool(self._force_var.get())

        self.config["epub"].update({
            "path": self.path_selector.get(),
            "target_height": height,
            "quality": quality,
            "force": force,
        })

        return {
            "path": self.path_selector.get(),
            "target_height": height,
            "quality": quality,
            "force": force,
        }

    def _get_compressor_main(self):
        return epub_compressor.main
