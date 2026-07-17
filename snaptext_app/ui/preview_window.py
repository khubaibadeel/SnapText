from __future__ import annotations

import threading
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from ..core.clipboard import copy_to_clipboard
from ..core.history import history
from ..core.logger import logger
from ..core.notifications import notify
from ..core.ocr import OCREngineUnavailable, perform_ocr
from ..core.paths import resource_path
from ..core.screenshot import save_screenshot
from ..core.system import open_path
from .theme import COLORS, MONO_FONT, font, primary_button, secondary_button


class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, img: Image.Image, text: str, screenshot_path=None, entry_id: str | None = None):
        super().__init__(parent)
        self.parent = parent
        self.img = img
        self.text = text or ""
        self.screenshot_path = str(screenshot_path) if screenshot_path else ""
        self.entry_id = entry_id
        self._preview_image = None

        self.title("Capture Preview — SnapText")
        self.geometry("760x690")
        self.minsize(660, 600)
        self.transient(parent)
        self.configure(fg_color=COLORS["window"])
        self._set_icon()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Control-Shift-C>", lambda _e: self.copy_text())
        self.bind("<Control-a>", self.select_all)
        self.after(100, lambda: self.attributes("-topmost", False))

    def _set_icon(self):
        try:
            self.iconbitmap(str(resource_path("icon.ico")))
        except Exception:
            pass

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 12))
        ctk.CTkLabel(header, text="Capture preview", font=font(24, "bold"), text_color=COLORS["text"]).pack(side="left")
        self.feedback_label = ctk.CTkLabel(header, text="", font=font(11, "bold"), text_color=COLORS["success"])
        self.feedback_label.pack(side="right")

        image_card = ctk.CTkFrame(self, fg_color=COLORS["surface"], border_width=1, border_color=COLORS["border"], corner_radius=12)
        image_card.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 14))
        preview = self.img.copy()
        preview.thumbnail((690, 215), Image.Resampling.LANCZOS)
        self._preview_image = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        ctk.CTkLabel(image_card, image=self._preview_image, text="").pack(padx=12, pady=12)

        text_card = ctk.CTkFrame(self, fg_color=COLORS["surface"], border_width=1, border_color=COLORS["border"], corner_radius=12)
        text_card.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 12))
        text_card.grid_columnconfigure(0, weight=1)
        text_card.grid_rowconfigure(2, weight=1, minsize=210)

        text_header = ctk.CTkFrame(text_card, fg_color="transparent")
        text_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        ctk.CTkLabel(text_header, text="Extracted text", font=font(14, "bold"), text_color=COLORS["text"]).pack(side="left")
        self.count_label = ctk.CTkLabel(text_header, text="", font=font(10), text_color=COLORS["muted"])
        self.count_label.pack(side="right")

        self.empty_label = ctk.CTkLabel(
            text_card,
            text="No readable text was found. Try Accurate mode, select a tighter area, or confirm the OCR language.",
            font=font(11), text_color=COLORS["muted"], wraplength=610, justify="left",
        )
        self.text_area = ctk.CTkTextbox(
            text_card,
            font=font(13, family=MONO_FONT),
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            wrap="word",
            height=220,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        )
        self.text_area.grid(row=2, column=0, sticky="nsew", padx=16, pady=(6, 12))
        self.text_area.bind("<KeyRelease>", lambda _e: self._update_count())
        self._set_text(self.text)

        progress_row = ctk.CTkFrame(text_card, fg_color="transparent")
        progress_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.progress = ctk.CTkProgressBar(progress_row, mode="indeterminate", height=4)
        self.progress.pack(fill="x")
        self.progress.pack_forget()

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 22))
        ctk.CTkButton(actions, text="Copy Text", command=self.copy_text, **primary_button(width=125)).pack(side="left")
        ctk.CTkButton(actions, text="Run OCR Again", command=self.retry_ocr, **secondary_button(width=135)).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="Save Image", command=self.save_image, **secondary_button(width=105)).pack(side="left")
        self.open_button = ctk.CTkButton(actions, text="Open Image", command=self.open_image, **secondary_button(width=105))
        self.open_button.pack(side="left", padx=8)
        self.open_button.configure(state="normal" if self.screenshot_path else "disabled")
        ctk.CTkButton(actions, text="New Capture", command=self.new_capture, **secondary_button(width=115)).pack(side="right")

    def _set_text(self, text: str):
        self.text_area.delete("1.0", "end")
        if text:
            self.empty_label.grid_forget()
            self.text_area.insert("1.0", text)
        else:
            self.empty_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 0))
        self.text = text
        self._update_count()

    def _update_count(self):
        text = self.text_area.get("1.0", "end-1c")
        words = len(text.split()) if text.strip() else 0
        self.count_label.configure(text=f"{words} words  •  {len(text)} characters")

    def _feedback(self, message: str, color=None):
        self.feedback_label.configure(text=message, text_color=color or COLORS["success"])
        self.after(2200, lambda: self.feedback_label.configure(text="") if self.winfo_exists() else None)

    def copy_text(self):
        text = self.text_area.get("1.0", "end-1c").strip()
        if not text:
            self._feedback("Nothing to copy", COLORS["warning"])
            return
        if not copy_to_clipboard(text):
            self._feedback("Clipboard unavailable", COLORS["warning"])
            self.parent.update_status("Clipboard copy failed", "warning", 0)
            return
        self.text = text
        if self.entry_id:
            history.update_entry(self.entry_id, text=text)
        self.parent.refresh_recent_capture()
        self.parent.update_status("Text copied to clipboard", "success")
        self._feedback("Copied")
        notify("SnapText", "Extracted text copied to the clipboard.")
        if self.parent.config.get("close_preview_after_copy", False):
            self.destroy()

    def save_image(self):
        if not self.screenshot_path:
            try:
                path = save_screenshot(self.img)
                self.screenshot_path = str(path)
                if self.entry_id:
                    history.update_entry(self.entry_id, screenshot_path=self.screenshot_path)
                self.open_button.configure(state="normal")
                self.parent.refresh_recent_capture()
                self._feedback("Image saved")
            except Exception as exc:
                self._feedback(str(exc), COLORS["danger"])
        else:
            self._feedback("Image already saved", COLORS["muted"])

    def open_image(self):
        if not self.screenshot_path or not open_path(self.screenshot_path):
            self._feedback("Image file not found", COLORS["danger"])

    def retry_ocr(self):
        self.progress.pack(fill="x")
        self.progress.start()
        self._feedback("Recognizing text…", COLORS["muted"])
        def worker():
            try:
                text = perform_ocr(self.img)
                self.after(0, lambda: self._finish_retry(text, None))
            except Exception as exc:
                self.after(0, lambda error=exc: self._finish_retry("", error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_retry(self, text: str, error: Exception | None):
        self.progress.stop()
        self.progress.pack_forget()
        if error:
            logger.error("Retry OCR failed: %s", error)
            if isinstance(error, OCREngineUnavailable):
                self._feedback("OCR unavailable — check Settings", COLORS["warning"])
                self.parent.update_status("OCR unavailable — open Settings", "warning", 0)
            else:
                self._feedback("Text recognition failed", COLORS["danger"])
            return
        self._set_text(text)
        if self.entry_id:
            history.update_entry(self.entry_id, text=text)
        self.parent.refresh_recent_capture()
        self._feedback("OCR updated" if text else "No text found", COLORS["success"] if text else COLORS["warning"])

    def select_all(self, _event=None):
        self.text_area.tag_add("sel", "1.0", "end-1c")
        return "break"

    def new_capture(self):
        self.destroy()
        self.parent.start_snipping()
