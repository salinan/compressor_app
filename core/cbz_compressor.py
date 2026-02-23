import os
import zipfile
import subprocess
import tempfile
import shutil
import threading
from pathlib import Path
from io import BytesIO
from PIL import Image

from core.shared import should_process_file, mark_as_processed

SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}


def _compress_image_data(
    image_data: bytes,
    filename: str,
    target_width: int,
    quality: int,
) -> tuple:
    """
    Compresses image bytes in memory.
    Returns (compressed_bytes, orig_size, new_size, new_filename).
    Falls back to original data on error.
    """
    try:
        with Image.open(BytesIO(image_data)) as img:
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')

            orig_w, orig_h = img.size

            if orig_w > target_width:
                ratio = orig_h / orig_w
                new_h = int(target_width * ratio)
                img = img.resize((target_width, new_h), Image.Resampling.LANCZOS)

            # Always output as JPEG
            out_filename = str(Path(filename).with_suffix('.jpg'))
            buf = BytesIO()
            img.save(buf, 'JPEG', quality=quality, optimize=True, progressive=True)
            compressed = buf.getvalue()
            return compressed, len(image_data), len(compressed), out_filename

    except Exception:
        return image_data, len(image_data), len(image_data), filename


def _extract_cbz(archive_path: Path, extract_dir: Path) -> bool:
    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(extract_dir)
        return True
    except Exception:
        return False


def _extract_cbr(archive_path: Path, extract_dir: Path) -> bool:
    try:
        import rarfile
        with rarfile.RarFile(archive_path, 'r') as rf:
            rf.extractall(extract_dir)
        return True
    except ImportError:
        return False
    except Exception:
        return False


def _pack_cbz(source_dir: Path, output_path: str) -> bool:
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
            files = []
            for root, _, filenames in os.walk(source_dir):
                for fn in filenames:
                    fp = Path(root) / fn
                    if fp.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                        files.append((fp, os.path.relpath(fp, source_dir)))
            files.sort(key=lambda x: x[1].lower())
            for fp, arcname in files:
                zf.write(fp, arcname)
        return True
    except Exception:
        return False


def _pack_cbr(source_dir: Path, output_path: str) -> bool:
    """Requires rar.exe in PATH."""
    try:
        files = []
        for root, _, filenames in os.walk(source_dir):
            for fn in filenames:
                fp = Path(root) / fn
                if fp.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                    files.append(str(fp))
        files.sort(key=lambda x: Path(x).name.lower())

        cmd = ['rar', 'a', '-ep1', '-m0', output_path] + files
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(source_dir))
        return result.returncode == 0
    except Exception:
        return False


def _process_archive(
    archive_path: Path,
    target_width: int,
    quality: int,
    force: bool,
    log_callback,
) -> tuple:
    """
    Processes one CBZ or CBR archive.
    Returns ('success', bytes_saved), ('skipped', 0), ('no_gain', 0), or ('failed', 0).
    CBR output requires rar.exe in PATH; falls back to failed if unavailable.
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    if not should_process_file(archive_path) and not force:
        return 'skipped', 0

    ext = archive_path.suffix.lower()
    temp_dir = None
    temp_output = None

    try:
        original_size = os.path.getsize(archive_path)

        temp_dir = tempfile.mkdtemp()
        extract_dir = Path(temp_dir) / 'extracted'
        extract_dir.mkdir()

        if ext == '.cbz':
            ok = _extract_cbz(archive_path, extract_dir)
        elif ext == '.cbr':
            ok = _extract_cbr(archive_path, extract_dir)
        else:
            return 'failed', 0

        if not ok:
            log(f"Kan niet uitpakken: {archive_path.name}")
            return 'failed', 0

        images_processed = 0

        for root, _, files in os.walk(extract_dir):
            for fn in sorted(files):
                fp = Path(root) / fn
                if fp.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                    try:
                        original_data = fp.read_bytes()
                        comp_data, _, _, new_fn = _compress_image_data(
                            original_data, fn, target_width, quality
                        )
                        if new_fn != fn:
                            new_fp = fp.parent / new_fn
                            fp.unlink()
                            fp = new_fp
                        fp.write_bytes(comp_data)
                        images_processed += 1
                    except Exception as e:
                        log(f"Afbeelding fout {fn}: {e}")

        # Repack
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            temp_output = f.name

        if ext == '.cbz':
            packed = _pack_cbz(extract_dir, temp_output)
        else:
            packed = _pack_cbr(extract_dir, temp_output)
            if not packed:
                log(f"CBR inpakken mislukt (rar.exe in PATH?): {archive_path.name}")
                return 'failed', 0

        if not packed:
            log(f"Kan archief niet aanmaken: {archive_path.name}")
            return 'failed', 0

        new_size = os.path.getsize(temp_output)

        if new_size < original_size:
            backup = str(archive_path) + '.backup'
            shutil.copy2(archive_path, backup)
            try:
                shutil.copy2(temp_output, archive_path)
                os.remove(backup)
                mark_as_processed(archive_path)
                saved = original_size - new_size
                pct = saved / original_size * 100
                log(
                    f"Gecomprimeerd: {archive_path.name} "
                    f"— {images_processed} afb. — bespaard: {pct:.1f}%"
                )
                return 'success', saved
            except Exception as e:
                if os.path.exists(backup):
                    shutil.copy2(backup, archive_path)
                    os.remove(backup)
                log(f"Fout bij vervangen, backup hersteld: {archive_path.name}: {e}")
                return 'failed', 0
        else:
            mark_as_processed(archive_path)
            log(f"Geen winst: {archive_path.name}")
            return 'no_gain', 0

    except Exception as e:
        log(f"Fout bij {archive_path.name}: {e}")
        return 'failed', 0

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if temp_output and os.path.exists(temp_output):
            try:
                os.unlink(temp_output)
            except Exception:
                pass


def main(
    path,
    target_width=1200,
    quality=70,
    force=False,
    stop_event: threading.Event = None,
    progress_callback=None,
    log_callback=None,
    stats_callback=None,
):
    """
    Compresses all CBZ (and CBR if rarfile is installed) files recursively under path.

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

    extensions = ['*.cbz']
    try:
        import rarfile  # noqa: F401
        extensions.append('*.cbr')
    except ImportError:
        log("rarfile niet beschikbaar — CBR bestanden worden overgeslagen")

    files = []
    for ext in extensions:
        files.extend(start_dir.rglob(ext))

    stats["total"] = len(files)
    log(f"Start verwerking — {stats['total']} comic bestanden gevonden")

    for i, comic_file in enumerate(files):
        if stop_event and stop_event.is_set():
            log("Verwerking gestopt door gebruiker")
            break

        if progress_callback:
            progress_callback(i, stats["total"], comic_file.name)

        status, saved = _process_archive(
            comic_file, target_width, quality, force, log_callback
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
