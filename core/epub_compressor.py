import os
import zipfile
import tempfile
import shutil
import threading
from pathlib import Path
from PIL import Image

from core.shared import should_process_file, mark_as_processed


def _compress_image_in_epub(img_path: Path, target_height: int, quality: int) -> int:
    """Compresses an image file in the extracted EPUB directory. Returns bytes saved."""
    temp_output = None
    try:
        with Image.open(img_path) as img:
            original_size = os.path.getsize(img_path)

            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            orig_w, orig_h = img.size

            if orig_h > target_height:
                ratio = orig_w / orig_h
                new_w = int(target_height * ratio)
                img = img.resize((new_w, target_height), Image.Resampling.LANCZOS)

            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                temp_output = f.name

            img.save(temp_output, 'JPEG', quality=quality, optimize=True, progressive=True)

        compressed_size = os.path.getsize(temp_output)

        if compressed_size < original_size:
            shutil.move(temp_output, img_path)
            return original_size - compressed_size
        else:
            os.unlink(temp_output)
            return 0

    except Exception:
        if temp_output and os.path.exists(temp_output):
            try:
                os.unlink(temp_output)
            except Exception:
                pass
        return 0


def _process_epub(
    epub_path: Path,
    target_height: int,
    quality: int,
    force: bool,
    log_callback,
) -> tuple:
    """
    Processes one EPUB: extracts, compresses images, repacks.
    Returns ('success', bytes_saved), ('skipped', 0), ('no_gain', 0), or ('failed', 0).
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    if not should_process_file(epub_path) and not force:
        return 'skipped', 0

    try:
        original_size = os.path.getsize(epub_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            extract_dir = os.path.join(temp_dir, 'book')
            os.makedirs(extract_dir)

            with zipfile.ZipFile(epub_path, 'r') as zf:
                zf.extractall(extract_dir)

            images_processed = 0

            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        saved = _compress_image_in_epub(
                            Path(root) / file, target_height, quality
                        )
                        if saved > 0:
                            images_processed += 1

            # Repack as EPUB (ZIP)
            temp_epub = os.path.join(temp_dir, 'compressed.epub')
            with zipfile.ZipFile(temp_epub, 'w', zipfile.ZIP_DEFLATED) as zf:
                # mimetype must be first and uncompressed
                mimetype_path = os.path.join(extract_dir, 'mimetype')
                if os.path.exists(mimetype_path):
                    zf.write(mimetype_path, 'mimetype', zipfile.ZIP_STORED)

                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, extract_dir)
                        if file != 'mimetype':
                            zf.write(file_path, arcname)

            new_size = os.path.getsize(temp_epub)

            if new_size < original_size:
                shutil.move(temp_epub, epub_path)
                mark_as_processed(epub_path)
                saved = original_size - new_size
                pct = saved / original_size * 100
                log(
                    f"Gecomprimeerd: {epub_path.name} "
                    f"— {images_processed} afb. — bespaard: {pct:.1f}%"
                )
                return 'success', saved
            else:
                mark_as_processed(epub_path)
                log(f"Geen winst: {epub_path.name}")
                return 'no_gain', 0

    except Exception as e:
        log(f"Fout bij {epub_path.name}: {e}")
        return 'failed', 0


def main(
    path,
    target_height=450,
    quality=65,
    force=False,
    stop_event: threading.Event = None,
    progress_callback=None,
    log_callback=None,
    stats_callback=None,
):
    """
    Compresses all EPUB files recursively under path.

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

    files = list(start_dir.rglob('*.epub'))
    stats["total"] = len(files)
    log(f"Start verwerking — {stats['total']} EPUB bestanden gevonden")

    for i, epub_file in enumerate(files):
        if stop_event and stop_event.is_set():
            log("Verwerking gestopt door gebruiker")
            break

        if progress_callback:
            progress_callback(i, stats["total"], epub_file.name)

        status, saved = _process_epub(epub_file, target_height, quality, force, log_callback)

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
