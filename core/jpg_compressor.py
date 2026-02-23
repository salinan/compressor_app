import os
import tempfile
import shutil
import threading
from pathlib import Path
from PIL import Image

from core.shared import should_process_file, mark_as_processed


def _compress_one(
    input_path: Path,
    target_width: int,
    target_height: int,
    quality: int,
    force: bool,
    log_callback,
) -> tuple:
    """
    Compresses a single JPG file in-place.
    Returns ('success', bytes_saved), ('skipped', 0), ('no_gain', 0), or ('failed', 0).
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    if not should_process_file(input_path) and not force:
        return 'skipped', 0

    temp_output = None
    try:
        original_size = os.path.getsize(input_path)

        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            orig_w, orig_h = img.size

            if orig_h > target_height:
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                temp_output = f.name

            img.save(temp_output, 'JPEG', quality=quality, optimize=True, progressive=True)

        compressed_size = os.path.getsize(temp_output)

        if compressed_size < original_size:
            shutil.copy2(temp_output, input_path)
            os.unlink(temp_output)
            mark_as_processed(input_path)
            saved = original_size - compressed_size
            pct = saved / original_size * 100
            log(f"Gecomprimeerd: {input_path.name} — bespaard: {pct:.1f}%")
            return 'success', saved
        else:
            os.unlink(temp_output)
            mark_as_processed(input_path)
            log(f"Geen winst: {input_path.name}")
            return 'no_gain', 0

    except Exception as e:
        if temp_output and os.path.exists(temp_output):
            try:
                os.unlink(temp_output)
            except Exception:
                pass
        log(f"Fout bij {input_path.name}: {e}")
        return 'failed', 0


def main(
    path,
    target_width=180,
    target_height=270,
    quality=70,
    force=False,
    stop_event: threading.Event = None,
    progress_callback=None,
    log_callback=None,
    stats_callback=None,
):
    """
    Compresses all JPG/JPEG files recursively under path.

    Callbacks:
      progress_callback(current, total, filename)
      log_callback(message)
      stats_callback(successful, skipped, failed, bytes_saved)

    Returns dict: {total, successful, skipped, failed, bytes_saved}
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    start_dir = Path(path)
    stats = {"total": 0, "successful": 0, "skipped": 0, "failed": 0, "bytes_saved": 0}

    files = []
    for ext in ('*.jpg', '*.jpeg'):
        files.extend(start_dir.rglob(ext))
    # Remove duplicates that rglob might find on case-insensitive FS
    seen = set()
    unique_files = []
    for f in files:
        key = str(f).lower()
        if key not in seen:
            seen.add(key)
            unique_files.append(f)
    files = unique_files

    stats["total"] = len(files)
    log(f"Start verwerking — {stats['total']} JPG bestanden gevonden")

    for i, img_file in enumerate(files):
        if stop_event and stop_event.is_set():
            log("Verwerking gestopt door gebruiker")
            break

        if progress_callback:
            progress_callback(i, stats["total"], img_file.name)

        status, saved = _compress_one(
            img_file, target_width, target_height, quality, force, log_callback
        )

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
