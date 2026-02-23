from pathlib import Path
from datetime import datetime
import logging


def should_process_file(file_path: Path) -> bool:
    """Returns True if the file should be processed (no .compressed marker exists)."""
    return not Path(str(file_path) + '.compressed').exists()


def mark_as_processed(file_path: Path) -> None:
    """Creates a .compressed marker file with current datetime."""
    try:
        Path(str(file_path) + '.compressed').write_text(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception:
        pass


def setup_logging(tool_name: str) -> logging.Logger:
    """Configures a logger with console + timestamped log file in compress_mijn_boeken/."""
    logger = logging.getLogger(tool_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent.parent / "compress_mijn_boeken"
    log_dir.mkdir(exist_ok=True)
    fh = logging.FileHandler(log_dir / f"{tool_name}_{timestamp}.log", encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def format_bytes(num_bytes: int) -> str:
    """Converts a byte count to a human-readable string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
