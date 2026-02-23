import copy
import json
from pathlib import Path

import customtkinter as ctk

from ui.tabs.jpg_tab import JpgTab
from ui.tabs.epub_tab import EpubTab
from ui.tabs.pdf_tab import PdfTab
from ui.tabs.cbz_tab import CbzTab
from core.pdf_compressor import DEFAULT_GS_PATH


_CONFIG_FILE = Path(__file__).parent.parent / "config.json"

DEFAULT_CONFIG = {
    "jpg": {
        "path": "",
        "target_width": 180,
        "target_height": 270,
        "quality": 70,
        "force": False,
    },
    "epub": {
        "path": "",
        "target_height": 450,
        "quality": 65,
        "force": False,
    },
    "pdf": {
        "path": "",
        "gs_path": DEFAULT_GS_PATH,
        "pdf_settings": "/ebook",
        "force": False,
    },
    "cbz": {
        "path": "",
        "target_width": 1200,
        "quality": 70,
        "force": False,
    },
}


class CompressorApp(ctk.CTk):
    """Main application window with 4 compressor tabs."""

    def __init__(self):
        super().__init__()
        self.title("Calibre Compressor")
        self.minsize(900, 560)

        self.config_data = self._load_config()

        # Tab view
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)

        for name in ("JPG", "EPUB", "PDF", "CBZ/CBR"):
            tabview.add(name)

        self.jpg_tab = JpgTab(tabview.tab("JPG"), self.config_data)
        self.jpg_tab.pack(fill="both", expand=True)

        self.epub_tab = EpubTab(tabview.tab("EPUB"), self.config_data)
        self.epub_tab.pack(fill="both", expand=True)

        self.pdf_tab = PdfTab(tabview.tab("PDF"), self.config_data)
        self.pdf_tab.pack(fill="both", expand=True)

        self.cbz_tab = CbzTab(tabview.tab("CBZ/CBR"), self.config_data)
        self.cbz_tab.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        config = copy.deepcopy(DEFAULT_CONFIG)
        if _CONFIG_FILE.exists():
            try:
                with open(_CONFIG_FILE, encoding="utf-8") as f:
                    loaded = json.load(f)
                for key in config:
                    if key in loaded and isinstance(loaded[key], dict):
                        config[key].update(loaded[key])
            except Exception:
                pass
        return config

    def _save_config(self):
        try:
            with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ── Close ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        for tab in (self.jpg_tab, self.epub_tab, self.pdf_tab, self.cbz_tab):
            tab.force_stop()
        self._save_config()
        self.destroy()
