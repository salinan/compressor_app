# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running Scripts

All scripts use the local venv. Run them directly:

```bash
venv/Scripts/python.exe compress_mijn_boeken/calibre_epub_compressie.py
venv/Scripts/python.exe compress_mijn_boeken/calibre_jpg_compressie.py
venv/Scripts/python.exe compress_mijn_boeken/calibre_pdf_compressie.py
venv/Scripts/python.exe compress_mijn_boeken/calibre_een_bestandstype.py
```

There are no tests and no build steps.

## Key Dependencies (installed in venv)

- `Pillow` — image compression
- **Ghostscript** (external, Windows): `C:\Program Files (x86)\gs\gs10.04.0\bin\gswin32c.exe` — required for PDF compression

## Architecture

This is a personal-use collection of standalone Windows file-management scripts for compressing a Calibre ebook library. Scripts are not importable modules — each has a `main()` function with **hardcoded source/target paths** that must be edited before use.

### `compress_mijn_boeken/`
Four independent scripts, each following the same pattern:
- `calibre_epub_compressie.py` — unpacks EPUB (ZIP), compresses internal JPG/PNG images with Pillow (target height 450px, quality 65), repacks; replaces original only if smaller.
- `calibre_jpg_compressie.py` — compresses standalone JPEG cover thumbnails (target 180×270px, quality 70).
- `calibre_pdf_compressie.py` — compresses PDFs via Ghostscript (`-dPDFSETTINGS=/ebook`).
- `calibre_een_bestandstype.py` — deduplicates books: when a directory contains the same book in multiple formats, keeps the preferred format (epub/mobi > azw3 > pdf) and deletes the rest.

### Shared Pattern: Marker Files
All compression scripts track processed files using a sidecar marker file (`<filename>.compressed`). If the marker exists, the file is skipped. The marker is created even when no compression was achievable (to avoid re-scanning). Delete `.compressed` files to force reprocessing.

### Logging
Each script creates a timestamped `.log` file in `compress_mijn_boeken/` (e.g. `epub_compress_YYYYMMDD_HHMMSS.log`). Logs are also streamed to stdout.
