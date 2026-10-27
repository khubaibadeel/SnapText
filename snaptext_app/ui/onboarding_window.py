from __future__ import annotations

import threading

import customtkinter as ctk

from ..core.config import config
from ..core.ocr import available_language_options, configure_detected_ocr
from ..core.paths import resource_path
from .theme import COLORS, font, primary_button, secondary_button


class OCRStatusWindow(ctk.CTkToplevel):
    """Non-blocking OCR status window retained for extension compatibility."""

    def __init__(self, parent, on_ready=None):
        super().__init__(parent)
        self.parent = parent
        self.on_ready = on_ready
        self.title("OCR status — SnapText")
        self.geometry("600x390")
        self.minsize(560, 360)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLORS["window"])
        self._set_icon()
        self._build()
        self.after(100, self.detect)

    def _set_icon(self):
        try:
            self.iconbitmap(str(resource_path("icon.ico")))
        except Exception:
            pass

    def _build(self):
        container = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=14,
        )
        container.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            container,
            text="Local OCR",
            font=font(25, "bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=26, pady=(25, 4))
        ctk.CTkLabel(
            container,
            text=(
                "SnapText uses Windows' built-in offline OCR for English. "
                "No OCR executable needs to be downloaded or selected."
            ),
            font=font(12),
            text_color=COLORS["muted"],
            justify="left",
            wraplength=510,
        ).pack(anchor="w", padx=26, pady=(0, 18))

        self.status_frame = ctk.CTkFrame(container, fg_color=COLORS["surface_alt"], corner_radius=10)
        self.status_frame.pack(fill="x", padx=26, pady=(10, 12))
        self.status_dot = ctk.CTkLabel(
            self.status_frame,
            text="●",
            width=24,
            font=font(15),
            text_color=COLORS["warning"],
        )
        self.status_dot.pack(side="left", padx=(14, 4), pady=14)
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Checking local OCR…",
            font=font(11),
            text_color=COLORS["text"],
            justify="left",
            wraplength=430,
        )
        self.status_label.pack(side="left", fill="x", expand=True, pady=14)

        ctk.CTkLabel(
            container,
            text=(
                "Optional Urdu profiles appear automatically when Windows or a detected "
                "Tesseract installation provides Urdu recognition data."
            ),
            font=font(10),
            text_color=COLORS["muted"],
            justify="left",
            wraplength=510,
        ).pack(anchor="w", padx=26, pady=(2, 14))

        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.pack(fill="x", padx=26, pady=(4, 24))
        ctk.CTkButton(
            buttons,
            text="Check Again",
            command=self.detect,
            **secondary_button(width=115),
        ).pack(side="left")
        self.continue_button = ctk.CTkButton(
            buttons,
            text="Continue",
            command=self.finish,
            **primary_button(width=110),
        )
        self.continue_button.pack(side="right")

    def detect(self):
        self.status_dot.configure(text_color=COLORS["warning"])
        self.status_label.configure(text="Checking local OCR…")

        def worker():
            status = configure_detected_ocr()
            profiles = ", ".join(available_language_options())
            self.after(0, lambda: self._show_status(status, profiles))

        threading.Thread(target=worker, daemon=True).start()

    def _show_status(self, status, profiles: str):
        if status.ready:
            self.status_dot.configure(text_color=COLORS["success"])
            self.status_label.configure(
                text=f"Ready — {status.engine_label}\nAvailable profiles: {profiles}"
            )
        else:
            self.status_dot.configure(text_color=COLORS["warning"])
            self.status_label.configure(text=f"{status.message}\nAvailable profiles: {profiles}")

    def finish(self):
        config.set("first_run_complete", True)
        if self.on_ready:
            self.on_ready()
        self.destroy()


# Older builds and plugins may still import this name.
TesseractSetupWindow = OCRStatusWindow
