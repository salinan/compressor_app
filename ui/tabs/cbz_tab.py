import customtkinter as ctk

from core import cbz_compressor
from ui.components import BaseTab, make_quality_row


class CbzTab(BaseTab):
    """Tab for compressing CBZ and CBR comic archives."""

    def __init__(self, parent, config: dict, **kwargs):
        super().__init__(parent, config, tab_name="cbz", **kwargs)

    def _build_settings(self, frame: ctk.CTkFrame):
        cfg = self.config["cbz"]

        # Target width
        ctk.CTkLabel(frame, text="Doelbreedte (px):", anchor="w").grid(
            row=0, column=0, padx=(10, 6), pady=3, sticky="w"
        )
        self._width_entry = ctk.CTkEntry(frame, width=80)
        self._width_entry.insert(0, str(cfg.get("target_width", 1200)))
        self._width_entry.grid(row=0, column=1, padx=6, pady=3, sticky="w")

        # Quality slider
        self._quality_slider = make_quality_row(frame, row=1, default_value=cfg.get("quality", 70))

        # Force checkbox
        self._force_var = ctk.BooleanVar(value=cfg.get("force", False))
        ctk.CTkCheckBox(
            frame,
            text="Force (herverwerk al verwerkte bestanden)",
            variable=self._force_var,
        ).grid(row=2, column=0, columnspan=3, padx=10, pady=3, sticky="w")

        # Info label about CBR
        ctk.CTkLabel(
            frame,
            text="Opmerking: CBR compressie vereist rar.exe in PATH.",
            text_color="gray60",
            font=("", 11),
        ).grid(row=3, column=0, columnspan=3, padx=10, pady=(2, 6), sticky="w")

    def _get_run_kwargs(self) -> dict:
        try:
            width = int(self._width_entry.get())
        except ValueError:
            width = 1200

        quality = int(self._quality_slider.get())
        force = bool(self._force_var.get())

        self.config["cbz"].update({
            "path": self.path_selector.get(),
            "target_width": width,
            "quality": quality,
            "force": force,
        })

        return {
            "path": self.path_selector.get(),
            "target_width": width,
            "quality": quality,
            "force": force,
        }

    def _get_compressor_main(self):
        return cbz_compressor.main
