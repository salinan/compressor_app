import threading
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from core.shared import format_bytes


# ─── Helper ──────────────────────────────────────────────────────────────────

def _dutch(n: int) -> str:
    """Formats an integer with Dutch thousands separator (period)."""
    return f"{n:,}".replace(",", ".")


# ─── PathSelector ─────────────────────────────────────────────────────────────

class PathSelector(ctk.CTkFrame):
    """
    A row widget: label + text entry + browse button.
    mode='directory' (default) or 'file' (for executables).
    on_change(path) is called whenever the path changes.
    """

    def __init__(self, parent, label: str, initial_value: str = "",
                 mode: str = "directory", on_change=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_change = on_change
        self._mode = mode

        ctk.CTkLabel(self, text=label, width=100, anchor="w").pack(side="left", padx=(0, 6))

        self._entry = ctk.CTkEntry(
            self,
            placeholder_text="Selecteer een map..." if mode == "directory" else "Pad naar bestand...",
        )
        if initial_value:
            self._entry.insert(0, initial_value)
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(self, text="...", width=36, command=self._browse).pack(side="left")

        self._entry.bind("<FocusOut>", self._notify)

    def _browse(self):
        if self._mode == "file":
            path = filedialog.askopenfilename(
                filetypes=[("Uitvoerbare bestanden", "*.exe"), ("Alle bestanden", "*.*")]
            )
        else:
            path = filedialog.askdirectory()

        if path:
            self._entry.delete(0, "end")
            self._entry.insert(0, path)
            self._notify()

    def _notify(self, _event=None):
        if self._on_change:
            self._on_change(self._entry.get())

    def get(self) -> str:
        return self._entry.get()

    def set(self, value: str):
        self._entry.delete(0, "end")
        self._entry.insert(0, value)


# ─── LogViewer ────────────────────────────────────────────────────────────────

class LogViewer(ctk.CTkFrame):
    """Scrollable monospace log area with a Clear button."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self._text = ctk.CTkTextbox(
            self,
            font=("Courier New", 11),
            wrap="word",
            state="disabled",
        )
        self._text.pack(fill="both", expand=True, padx=6, pady=(6, 0))

        ctk.CTkButton(
            self, text="Wis log", height=24, command=self.clear
        ).pack(anchor="e", padx=6, pady=3)

    def append(self, text: str):
        """Thread-safe via after() — adds a timestamped line and auto-scrolls."""
        ts = datetime.now().strftime("%H:%M:%S")
        self._text.configure(state="normal")
        self._text.insert("end", f"{ts} — {text}\n")
        self._text.see("end")
        self._text.configure(state="disabled")

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")


# ─── ProgressBar ──────────────────────────────────────────────────────────────

class ProgressBar(ctk.CTkFrame):
    """Progress bar + 'X / Y bestanden' label below it."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._bar = ctk.CTkProgressBar(self, height=12)
        self._bar.pack(fill="x", padx=6, pady=(3, 1))
        self._bar.set(0)

        self._label = ctk.CTkLabel(self, text="0 / 0 bestanden", font=("", 11))
        self._label.pack(anchor="center", pady=(0, 1))

    def update(self, current: int, total: int):
        """Thread-safe via after() — updates bar and label."""
        if total > 0:
            self._bar.set(current / total)
        else:
            self._bar.set(0)
        self._label.configure(
            text=f"{_dutch(current)} / {_dutch(total)} bestanden"
        )

    def reset(self):
        self._bar.set(0)
        self._label.configure(text="0 / 0 bestanden")


# ─── StatsPanel ───────────────────────────────────────────────────────────────

class StatsPanel(ctk.CTkFrame):
    """2×2 grid showing Succesvol / Overgeslagen / Mislukt / Bespaard."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        g = {"padx": (10, 4), "pady": 4, "sticky": "w"}
        gv = {"padx": (0, 10), "pady": 4, "sticky": "w"}

        ctk.CTkLabel(self, text="Succesvol:").grid(row=0, column=0, **g)
        self._lbl_ok = ctk.CTkLabel(self, text="—", width=45, anchor="w")
        self._lbl_ok.grid(row=0, column=1, **gv)

        ctk.CTkLabel(self, text="Overgeslagen:").grid(row=0, column=2, **g)
        self._lbl_skip = ctk.CTkLabel(self, text="—", width=45, anchor="w")
        self._lbl_skip.grid(row=0, column=3, **gv)

        ctk.CTkLabel(self, text="Mislukt:").grid(row=0, column=4, **g)
        self._lbl_fail = ctk.CTkLabel(self, text="—", width=45, anchor="w")
        self._lbl_fail.grid(row=0, column=5, **gv)

        ctk.CTkLabel(self, text="Bespaard:").grid(row=0, column=6, **g)
        self._lbl_saved = ctk.CTkLabel(self, text="—", width=60, anchor="w")
        self._lbl_saved.grid(row=0, column=7, **gv)

    def update(self, successful: int, skipped: int, failed: int, bytes_saved: int):
        """Thread-safe via after()."""
        self._lbl_ok.configure(text=_dutch(successful))
        self._lbl_skip.configure(text=_dutch(skipped))
        self._lbl_fail.configure(text=_dutch(failed))
        self._lbl_saved.configure(text=format_bytes(bytes_saved))

    def reset(self):
        for lbl in (self._lbl_ok, self._lbl_skip, self._lbl_fail, self._lbl_saved):
            lbl.configure(text="—")


# ─── StartStopButton ──────────────────────────────────────────────────────────

class StartStopButton(ctk.CTkButton):
    """Toggles between green 'Start' and red 'Stop' states."""

    _COLOR_START = ("#2ecc71", "#27ae60")
    _COLOR_START_HOVER = ("#27ae60", "#1e8449")
    _COLOR_STOP = ("#e74c3c", "#c0392b")
    _COLOR_STOP_HOVER = ("#c0392b", "#922b21")

    def __init__(self, parent, on_start, on_stop, **kwargs):
        super().__init__(
            parent,
            text="Start verwerking",
            fg_color=self._COLOR_START,
            hover_color=self._COLOR_START_HOVER,
            command=self._click,
            **kwargs,
        )
        self._on_start = on_start
        self._on_stop = on_stop
        self._running = False

    def _click(self):
        if self._running:
            self._on_stop()
        else:
            self._on_start()

    def set_running(self, running: bool):
        self._running = running
        if running:
            self.configure(
                text="Stop verwerking",
                fg_color=self._COLOR_STOP,
                hover_color=self._COLOR_STOP_HOVER,
            )
        else:
            self.configure(
                text="Start verwerking",
                fg_color=self._COLOR_START,
                hover_color=self._COLOR_START_HOVER,
            )


# ─── BaseTab ──────────────────────────────────────────────────────────────────

class BaseTab(ctk.CTkFrame):
    """
    Common base for all compressor tabs.

    Subclasses must implement:
      _build_settings(frame)   — adds setting widgets to the given CTkFrame
      _get_run_kwargs() -> dict — returns kwargs for the compressor main()
      _get_compressor_main()   — returns the compressor main function
    """

    def __init__(self, parent, config: dict, tab_name: str, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.config = config
        self.tab_name = tab_name
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(6, 0))

        # Path selector
        self.path_selector = PathSelector(
            top,
            label="Map:",
            initial_value=self.config.get(self.tab_name, {}).get("path", ""),
            on_change=lambda p: self.config[self.tab_name].update({"path": p}),
        )
        self.path_selector.pack(fill="x", pady=(0, 4))

        # Settings (tab-specific)
        settings = ctk.CTkFrame(top)
        settings.pack(fill="x", pady=(0, 4))
        self._build_settings(settings)

        # Start/stop button
        self.start_stop_btn = StartStopButton(
            top, on_start=self.start, on_stop=self.stop, height=30
        )
        self.start_stop_btn.pack(fill="x", pady=(0, 4))

        # Progress
        self.progress_bar = ProgressBar(top)
        self.progress_bar.pack(fill="x", pady=(0, 2))

        # Stats
        self.stats_panel = StatsPanel(top)
        self.stats_panel.pack(fill="x", pady=(0, 4))

        # Log (takes remaining space)
        self.log_viewer = LogViewer(self)
        self.log_viewer.pack(fill="both", expand=True, padx=10, pady=(0, 6))

    def _build_settings(self, frame: ctk.CTkFrame):
        raise NotImplementedError

    # ── Subclass interface ────────────────────────────────────────────────────

    def _get_run_kwargs(self) -> dict:
        raise NotImplementedError

    def _get_compressor_main(self):
        raise NotImplementedError

    # ── Control ───────────────────────────────────────────────────────────────

    def start(self):
        path = self.path_selector.get()
        if not path:
            self.log_viewer.append("Fout: geen map geselecteerd")
            return

        self._stop_event = threading.Event()
        self.progress_bar.reset()
        self.stats_panel.reset()
        self.start_stop_btn.set_running(True)

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._stop_event:
            self._stop_event.set()

    def force_stop(self):
        """Called by app on window close."""
        if self._stop_event:
            self._stop_event.set()

    # ── Worker ────────────────────────────────────────────────────────────────

    def _run(self):
        try:
            kwargs = self._get_run_kwargs()
            kwargs["stop_event"] = self._stop_event
            kwargs["progress_callback"] = self._on_progress
            kwargs["log_callback"] = self._on_log
            kwargs["stats_callback"] = self._on_stats

            stats = self._get_compressor_main()(**kwargs)
        except Exception as e:
            self.after(0, self.log_viewer.append, f"Onverwachte fout: {e}")
            stats = {"total": 0, "successful": 0, "skipped": 0, "failed": 0, "bytes_saved": 0}
        finally:
            self.after(0, self._on_done, stats)

    # ── Callbacks (called from worker thread → schedule on main thread) ───────

    def _on_progress(self, current: int, total: int, filename: str):
        self.after(0, self.progress_bar.update, current, total)

    def _on_log(self, message: str):
        self.after(0, self.log_viewer.append, message)

    def _on_stats(self, successful: int, skipped: int, failed: int, bytes_saved: int):
        self.after(0, self.stats_panel.update, successful, skipped, failed, bytes_saved)

    def _on_done(self, stats: dict):
        self.progress_bar.update(stats["total"], stats["total"])
        self.stats_panel.update(
            stats["successful"], stats["skipped"],
            stats["failed"], stats["bytes_saved"]
        )
        self.start_stop_btn.set_running(False)


# ─── Shared helper: quality slider row ───────────────────────────────────────

def make_quality_row(frame, row: int, default_value: int) -> ctk.CTkSlider:
    """
    Adds a 'Kwaliteit' label + slider + value label to a grid frame.
    Returns the slider widget.
    """
    ctk.CTkLabel(frame, text="Kwaliteit:", anchor="w").grid(
        row=row, column=0, padx=(10, 6), pady=3, sticky="w"
    )

    val_lbl = ctk.CTkLabel(frame, text=str(default_value), width=30)
    val_lbl.grid(row=row, column=2, padx=(4, 10), pady=3)

    slider = ctk.CTkSlider(
        frame,
        from_=50, to=95,
        number_of_steps=45,
        command=lambda v: val_lbl.configure(text=str(int(v))),
    )
    slider.set(default_value)
    slider.grid(row=row, column=1, padx=6, pady=3, sticky="ew")
    frame.columnconfigure(1, weight=1)

    return slider
