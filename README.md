# Calibre Compressor

A Windows desktop app that bundles four file compression tools in one interface, aimed at large Calibre ebook libraries (300,000+ files).

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## Tools

| Tab | What it does |
|-----|-------------|
| **JPG** | Resizes and compresses standalone JPEG cover images |
| **EPUB** | Recompresses images inside EPUB archives |
| **PDF** | Compresses PDFs via Ghostscript |
| **CBZ/CBR** | Recompresses images inside comic archives |

All tools:
- Skip already-processed files using a `.compressed` marker sidecar
- Run in a background thread so the UI stays responsive
- Show live progress, stats and a scrollable log

## Requirements

- Python 3.10+
- [Ghostscript](https://www.ghostscript.com/) (for PDF compression) — default path: `C:\Program Files (x86)\gs\gs10.04.0\bin\gswin32c.exe`
- `rar.exe` in PATH (optional, for CBR output)

## Installation

```bash
git clone https://github.com/your-username/calibre_compressor.git
cd calibre_compressor

python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

## Usage

```bash
venv\Scripts\python main.py
```

Select a folder per tab, adjust the settings, press **Start verwerking**.
Press **Stop** to halt after the current file finishes.

Settings are saved automatically to `config.json` (excluded from git).

## Project structure

```
├── main.py                  # Entry point
├── requirements.txt
├── core/
│   ├── shared.py            # Marker files, logging, formatting
│   ├── jpg_compressor.py
│   ├── epub_compressor.py
│   ├── pdf_compressor.py
│   └── cbz_compressor.py
└── ui/
    ├── app.py               # Main window + config I/O
    ├── components.py        # Reusable widgets + BaseTab
    └── tabs/
        ├── jpg_tab.py
        ├── epub_tab.py
        ├── pdf_tab.py
        └── cbz_tab.py
```

## Original scripts

The standalone scripts in `compress_mijn_boeken/` are the originals this app was built from. They still work independently with hardcoded paths.
