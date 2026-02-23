import os
import subprocess
import tempfile
import threading
from pathlib import Path

from core.shared import should_process_file, mark_as_processed

DEFAULT_GS_PATH = r'C:\Program Files (x86)\gs\gs10.04.0\bin\gswin32c.exe'


def _compress_pdf(
    pdf_path: Path,
    gs_path: str,
    pdf_settings: str,
    force: bool,
    log_callback,
) -> tuple:
    """
    Compresses a single PDF via Ghostscript.
    Returns ('success', bytes_saved), ('skipped', 0), ('no_gain', 0), or ('failed', 0).
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    if not should_process_file(pdf_path) and not force:
        return 'skipped', 0

    temp_output = None
    try:
        original_size = os.path.getsize(pdf_path)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_output = f.name

        cmd = [
            gs_path,
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS={pdf_settings}',
            '-dEmbedAllFonts=true',
            '-dSubsetFonts=true',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={temp_output}',
            str(pdf_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if os.path.exists(temp_output):
                os.unlink(temp_output)
            log(f"GS fout bij {pdf_path.name}: {result.stderr.strip()[:200]}")
            return 'failed', 0

        compressed_size = os.path.getsize(temp_output)

        if compressed_size < original_size:
            os.replace(temp_output, pdf_path)
            mark_as_processed(pdf_path)
            saved = original_size - compressed_size
            pct = saved / original_size * 100
            log(f"Gecomprimeerd: {pdf_path.name} — bespaard: {pct:.1f}%")
            return 'success', saved
        else:
            os.unlink(temp_output)
            mark_as_processed(pdf_path)
            log(f"Geen winst: {pdf_path.name}")
            return 'no_gain', 0

    except Exception as e:
        if temp_output and os.path.exists(temp_output):
            try:
                os.unlink(temp_output)
            except Exception:
                pass
        log(f"Fout bij {pdf_path.name}: {e}")
        return 'failed', 0


def main(
    path,
    gs_path=DEFAULT_GS_PATH,
    pdf_settings='/ebook',
    force=False,
    stop_event: threading.Event = None,
    progress_callback=None,
    log_callback=None,
    stats_callback=None,
):
    """
    Compresses all PDF files recursively under path using Ghostscript.

    Callbacks:
      progress_callback(current, total, filename)
      log_callback(message)
      stats_callback(successful, skipped, failed, bytes_saved)

    Returns dict: {total, successful, skipped, failed, bytes_saved}
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    empty_stats = {"total": 0, "successful": 0, "skipped": 0, "failed": 0, "bytes_saved": 0}

    if not os.path.exists(gs_path):
        log(f"Ghostscript niet gevonden op: {gs_path}")
        return empty_stats

    start_dir = Path(path)
    stats = {"total": 0, "successful": 0, "skipped": 0, "failed": 0, "bytes_saved": 0}

    files = list(start_dir.rglob('*.pdf'))
    stats["total"] = len(files)
    log(f"Start verwerking — {stats['total']} PDF bestanden gevonden")

    for i, pdf_file in enumerate(files):
        if stop_event and stop_event.is_set():
            log("Verwerking gestopt door gebruiker")
            break

        if progress_callback:
            progress_callback(i, stats["total"], pdf_file.name)

        status, saved = _compress_pdf(pdf_file, gs_path, pdf_settings, force, log_callback)

        if status == 'success':
            stats["successful"] += 1
            stats["bytes_saved"] += saved
        elif status in ('skipped', 'no_gain'):
            stats["skipped"] += 1
        else:
            stats["failed"] += 1

        if stats_callback:
            stats_callback(
                stats["successful"], stats["skipped"],
                stats["failed"], stats["bytes_saved"]
            )

    if progress_callback:
        progress_callback(stats["total"], stats["total"], "")

    log(
        f"Klaar — Succesvol: {stats['successful']}, "
        f"Overgeslagen: {stats['skipped']}, "
        f"Mislukt: {stats['failed']}, "
        f"Bespaard: {stats['bytes_saved'] / (1024 * 1024):.1f} MB"
    )
    return stats
