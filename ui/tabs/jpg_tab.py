import customtkinter as ctk

from core import jpg_compressor
from ui.components import BaseTab, make_quality_row


class JpgTab(BaseTab):
    """Tab for compressing standalone JPEG cover images."""

    def __init__(self, parent, config: dict, **kwargs):
        super().__init__(parent, config, tab_name="jpg", **kwargs)

    def _build_settings(self, frame: ctk.CTkFrame):
        cfg = self.config["jpg"]

        # Width
        ctk.CTkLabel(frame, text="Breedte (px):", anchor="w").grid(
            row=0, column=0, padx=(10, 6), pady=3, sticky="w"
        )
        self._width_entry = ctk.CTkEntry(frame, width=80)
        self._width_entry.insert(0, str(cfg.get("target_width", 180)))
        self._width_entry.grid(row=0, column=1, padx=6, pady=3, sticky="w")

        # Height
        ctk.CTkLabel(frame, text="Hoogte (px):", anchor="w").grid(
            row=1, column=0, padx=(10, 6), pady=3, sticky="w"
        )
        self._height_entry = ctk.CTkEntry(frame, width=80)
        self._height_entry.insert(0, str(cfg.get("target_height", 270)))
        self._height_entry.grid(row=1, column=1, padx=6, pady=3, sticky="w")

        # Quality slider
        self._quality_slider = make_quality_row(frame, row=2, default_value=cfg.get("quality", 70))

        # Force checkbox
        self._force_var = ctk.BooleanVar(value=cfg.get("force", False))
        ctk.CTkCheckBox(
            frame,
            text="Force (herverwerk al verwerkte bestanden)",
            variable=self._force_var,
        ).grid(row=3, column=0, columnspan=3, padx=10, pady=3, sticky="w")

    def _get_run_kwargs(self) -> dict:
        try:
            width = int(self._width_entry.get())
        except ValueError:
            width = 180
        try:
            height = int(self._height_entry.get())
        except ValueError:
            height = 270

        quality = int(self._quality_slider.get())
        force = bool(self._force_var.get())

        # Persist to config
        self.config["jpg"].update({
            "path": self.path_selector.get(),
            "target_width": width,
            "target_height": height,
            "quality": quality,
            "force": force,
        })

        return {
            "path": self.path_selector.get(),
            "target_width": width,
            "target_height": height,
            "quality": quality,
            "force": force,
        }

    def _get_compressor_main(self):
        return jpg_compressor.main
