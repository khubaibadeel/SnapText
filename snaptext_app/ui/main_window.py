from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageGrab

from ..core.clipboard import copy_to_clipboard
from ..core.config import config
from ..core.history import history
from ..core.logger import logger, set_debug_logging
from ..core.notifications import notify
from ..core.ocr import OCREngineUnavailable, configure_detected_ocr, perform_ocr
from ..core.paths import resource_path
from ..core.screenshot import save_screenshot
from ..core.shortcuts import ShortcutManager
from ..core.snipper import SnippingOverlay
from ..core.system import open_path
from ..core.tray import TrayController
from .history_window import HistoryWindow
from .preview_window import PreviewWindow
from .settings_window import SettingsWindow
from .theme import COLORS, apply_theme, font, primary_button, secondary_button


class MainWindow(ctk.CTk):
    def __init__(self):
        self.config = config
        apply_theme(config.get("appearance_mode", "system"))
        super().__init__()

        self.title("SnapText")
        self.configure(fg_color=COLORS["window"])
        self.geometry(config.get("window_geometry", "720x610"))
        self.minsize(680, 570)
        self._center_if_needed()
        self._set_icon()

        self.is_snipping = False
        self.is_processing = False
        self._status_reset_job = None
        self._recent_thumb = None
        self._history_window = None
        self._settings_window = None
        self._preview_windows: list[PreviewWindow] = []
        self.shortcuts = ShortcutManager()
        self.tray = TrayController(self)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Control-o>", lambda _event: self.open_screenshots_folder())
        self.bind("<Control-comma>", lambda _event: self.show_settings())
        self.refresh_recent_capture()
        self.apply_runtime_settings(initial=True)
        self.after(350, self._check_ocr_engine_async)

    @property
    def capture_hotkey(self) -> str:
        return config.get("capture_hotkey", "ctrl+shift+s")

    @property
    def copy_latest_hotkey(self) -> str:
        return config.get("copy_latest_hotkey", "ctrl+shift+c")

    def _center_if_needed(self):
        geometry = config.get("window_geometry", "720x610")
        if "+" in geometry and config.get("remember_window_position", True):
            return
        self.update_idletasks()
        width, height = 720, 610
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _set_icon(self):
        try:
            self.iconbitmap(str(resource_path("icon.ico")))
        except Exception as exc:
            logger.debug("Could not set window icon: %s", exc)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 14))

        try:
            logo_image = Image.open(resource_path("assets/icon.png")).convert("RGBA")
            self.logo = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(44, 44))
            ctk.CTkLabel(header, text="", image=self.logo, width=48).pack(side="left", padx=(0, 12))
        except Exception:
            self.logo = None

        title_group = ctk.CTkFrame(header, fg_color="transparent")
        title_group.pack(side="left")
        ctk.CTkLabel(title_group, text="SnapText", font=font(25, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(
            title_group,
            text="Capture text from anywhere on your screen",
            font=font(11),
            text_color=COLORS["muted"],
        ).pack(anchor="w")
        ctk.CTkButton(header, text="Settings", command=self.show_settings, **secondary_button(width=92, height=34)).pack(side="right")

        capture_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=16,
        )
        capture_card.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 16))
        capture_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(capture_card, text="CAPTURE", font=font(10, "bold"), text_color=COLORS["accent"]).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 4))
        ctk.CTkLabel(capture_card, text="Select an area and extract its text", font=font(19, "bold"), text_color=COLORS["text"]).grid(row=1, column=0, sticky="w", padx=22)
        ctk.CTkLabel(capture_card, text="Drag over any app, image, document, or browser window.", font=font(11), text_color=COLORS["muted"]).grid(row=2, column=0, sticky="w", padx=22, pady=(4, 16))

        action_row = ctk.CTkFrame(capture_card, fg_color="transparent")
        action_row.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 20))
        self.capture_button = ctk.CTkButton(action_row, text="New Capture", command=self.start_snipping, **primary_button(width=150, height=44))
        self.capture_button.pack(side="left")
        self.hotkey_label = ctk.CTkLabel(action_row, text=self._format_hotkey(self.capture_hotkey), font=font(10, "bold"), fg_color=COLORS["surface_alt"], corner_radius=7, text_color=COLORS["muted"], padx=10, height=28)
        self.hotkey_label.pack(side="left", padx=10)
        ctk.CTkButton(action_row, text="From Clipboard", command=self.capture_from_clipboard, **secondary_button(width=128, height=40)).pack(side="right")
        ctk.CTkButton(action_row, text="Open Image", command=self.open_image_for_ocr, **secondary_button(width=104, height=40)).pack(side="right", padx=8)

        recent_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=14,
        )
        recent_card.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 14))
        recent_card.grid_columnconfigure(1, weight=1)
        recent_card.grid_rowconfigure(1, weight=1)

        recent_header = ctk.CTkFrame(recent_card, fg_color="transparent")
        recent_header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(15, 8))
        ctk.CTkLabel(recent_header, text="Latest capture", font=font(14, "bold"), text_color=COLORS["text"]).pack(side="left")
        self.recent_time = ctk.CTkLabel(recent_header, text="", font=font(10), text_color=COLORS["muted"])
        self.recent_time.pack(side="right")

        self.recent_thumbnail = ctk.CTkLabel(recent_card, text="", width=126, height=94, fg_color=COLORS["surface_alt"], corner_radius=8)
        self.recent_thumbnail.grid(row=1, column=0, sticky="nw", padx=(18, 12), pady=(0, 14))

        recent_content = ctk.CTkFrame(recent_card, fg_color="transparent")
        recent_content.grid(row=1, column=1, sticky="nsew", padx=(0, 18), pady=(0, 14))
        recent_content.grid_columnconfigure(0, weight=1)
        self.recent_text = ctk.CTkLabel(recent_content, text="", font=font(12), justify="left", anchor="nw", wraplength=450, text_color=COLORS["text"])
        self.recent_text.grid(row=0, column=0, sticky="nsew")
        self.recent_actions = ctk.CTkFrame(recent_content, fg_color="transparent")
        self.recent_actions.grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.copy_recent_button = ctk.CTkButton(self.recent_actions, text="Copy", command=self.copy_latest_text, **secondary_button(width=74, height=32))
        self.copy_recent_button.pack(side="left")
        self.open_recent_button = ctk.CTkButton(self.recent_actions, text="Open Preview", command=self.open_latest_preview, **secondary_button(width=108, height=32))
        self.open_recent_button.pack(side="left", padx=8)
        ctk.CTkButton(self.recent_actions, text="Capture Again", command=self.start_snipping, **secondary_button(width=108, height=32)).pack(side="left")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 20))
        ctk.CTkButton(footer, text="History", command=self.show_history, **secondary_button(width=90, height=34)).pack(side="left")
        ctk.CTkButton(footer, text="Screenshots", command=self.open_screenshots_folder, **secondary_button(width=105, height=34)).pack(side="left", padx=8)
        self.status_dot = ctk.CTkLabel(footer, text="●", width=18, text_color=COLORS["success"], font=font(12))
        self.status_dot.pack(side="right")
        self.status_label = ctk.CTkLabel(footer, text="Ready", font=font(10), text_color=COLORS["muted"])
        self.status_label.pack(side="right", padx=(0, 4))

    @staticmethod
    def _format_hotkey(hotkey: str) -> str:
        return " + ".join(part.title() for part in hotkey.split("+"))

    def update_status(self, message: str, kind: str | None = None, reset_after: int = 3500):
        color = {
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
            "busy": COLORS["accent"],
        }.get(kind, COLORS["muted"])

        def update():
            self.status_label.configure(text=message)
            self.status_dot.configure(text_color=color)
            if self._status_reset_job:
                self.after_cancel(self._status_reset_job)
                self._status_reset_job = None
            if reset_after:
                self._status_reset_job = self.after(reset_after, lambda: self.update_status("Ready", "success", 0))

        if threading.current_thread() is threading.main_thread():
            update()
        else:
            self.after(0, update)

    def _check_ocr_engine_async(self):
        def worker():
            status = configure_detected_ocr()
            self.after(0, lambda: self._handle_ocr_status(status))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_ocr_status(self, status):
        if status.ready:
            self.update_status(f"{status.engine_label} ready", "success")
            return

        # Keep capture available. A source checkout may only need its one-time
        # dependency setup, and a completed release already contains the WinRT
        # Python bindings. OCR errors are reported inline after processing.
        self.update_status("OCR needs attention", "warning", 0)
        logger.warning("OCR unavailable at startup: %s", status.message)

    def start_snipping(self):
        if self.is_snipping or self.is_processing:
            return
        self.is_snipping = True
        self.update_status("Select an area on screen", "busy", 0)
        self.withdraw()

        def launch_overlay():
            try:
                SnippingOverlay(self.on_snip_done)
            except Exception as exc:
                logger.exception("Could not start capture overlay")
                self.on_snip_done(None)
                self.update_status(f"Capture failed: {exc}", "danger", 0)

        self.after(180, launch_overlay)

    def on_snip_done(self, image: Image.Image | None):
        self.is_snipping = False
        self.show_main_window()
        if image is None:
            self.update_status("Capture cancelled", "warning")
            return
        self.process_image(image, source="screen")

    def capture_from_clipboard(self):
        try:
            clipboard = ImageGrab.grabclipboard()
            if isinstance(clipboard, Image.Image):
                self.process_image(clipboard.copy(), source="clipboard")
                return
            if isinstance(clipboard, list):
                for item in clipboard:
                    try:
                        with Image.open(item) as image:
                            self.process_image(image.convert("RGB"), source="clipboard")
                            return
                    except Exception:
                        continue
            self.update_status("Clipboard does not contain an image", "warning")
        except Exception as exc:
            logger.error("Clipboard image capture failed: %s", exc)
            self.update_status("Could not read an image from the clipboard", "danger")

    def open_image_for_ocr(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose an image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            with Image.open(path) as image:
                self.process_image(image.convert("RGB"), source="file", existing_path=path)
        except Exception as exc:
            logger.error("Could not open image %s: %s", path, exc)
            self.update_status("The selected image could not be opened", "danger")

    def process_image(self, image: Image.Image, source: str, existing_path: str | None = None):
        if self.is_processing:
            self.update_status("A capture is already being processed", "warning")
            return
        self.is_processing = True
        self.capture_button.configure(state="disabled", text="Processing…")
        self.update_status("Recognizing text…", "busy", 0)

        def worker():
            screenshot_path = existing_path
            warnings: list[str] = []
            try:
                if source != "file" and config.get("auto_save_screenshot", True):
                    try:
                        screenshot_path = str(save_screenshot(image))
                    except Exception as save_error:
                        logger.error("Screenshot save failed; continuing with OCR: %s", save_error)
                        warnings.append("screenshot_save_failed")

                try:
                    text = perform_ocr(image)
                    error = None
                except Exception as ocr_error:
                    text = ""
                    error = ocr_error

                entry = history.add_entry(screenshot_path, text, source)
                clipboard_ok = True
                if text and config.get("auto_copy_text", True):
                    clipboard_ok = copy_to_clipboard(text)

                self.after(
                    0,
                    lambda text=text, screenshot_path=screenshot_path, entry=entry, error=error,
                    clipboard_ok=clipboard_ok, warnings=tuple(warnings): self._finish_processing(
                        image, text, screenshot_path, entry, error, clipboard_ok, warnings
                    ),
                )
            except Exception as exc:
                # Last-resort guard for unexpected history/GUI scheduling failures.
                logger.exception("Unexpected image processing failure")
                fallback_entry = history.add_entry(screenshot_path, "", source)
                self.after(
                    0,
                    lambda error=exc, entry=fallback_entry: self._finish_processing(
                        image, "", screenshot_path, entry, error, True, ()
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _finish_processing(self, image, text, screenshot_path, entry, error, clipboard_ok: bool = True, warnings=()):
        self.is_processing = False
        self.capture_button.configure(state="normal", text="New Capture")
        self.refresh_recent_capture()
        self.show_preview(image, text, screenshot_path, entry.get("id"))
        if error:
            logger.error("Image processing failed: %s", error)
            if isinstance(error, OCREngineUnavailable):
                # Avoid a disruptive technical popup. The preview remains open
                # with the captured image and Settings contains the full status.
                self.update_status("OCR unavailable — open Settings", "warning", 0)
            else:
                self.update_status("Text recognition failed", "danger", 0)
            return
        if text:
            if not clipboard_ok:
                self.update_status("Text extracted; clipboard copy failed", "warning", 0)
                return
            if "screenshot_save_failed" in warnings:
                self.update_status("Text copied; screenshot save failed", "warning", 0)
                return
            message = "Text copied to clipboard" if config.get("auto_copy_text", True) else "Text extracted successfully"
            self.update_status(message, "success")
            notify("SnapText", message)
        else:
            self.update_status("No readable text found", "warning")

    def show_preview(self, image, text, screenshot_path=None, entry_id=None):
        window = PreviewWindow(self, image, text, screenshot_path, entry_id)
        self._preview_windows.append(window)
        window.bind("<Destroy>", lambda _event, w=window: self._forget_preview(w), add="+")

    def _forget_preview(self, window):
        if window in self._preview_windows:
            self._preview_windows.remove(window)

    def refresh_recent_capture(self):
        entries = history.get_all()
        if not entries:
            self.recent_text.configure(text="No captures yet.\nYour extracted text will appear here.", text_color=COLORS["muted"])
            self.recent_time.configure(text="")
            self.recent_thumbnail.configure(image=None, text="No preview")
            self.copy_recent_button.configure(state="disabled")
            self.open_recent_button.configure(state="disabled")
            return
        entry = entries[0]
        text = (entry.get("text") or "").strip()
        snippet = text[:360] + ("…" if len(text) > 360 else "") if text else "No readable text was detected in this capture."
        self.recent_text.configure(text=snippet, text_color=COLORS["text"] if text else COLORS["muted"])
        timestamp = entry.get("timestamp", "").replace("T", " ")
        self.recent_time.configure(text=timestamp[:16])
        self.copy_recent_button.configure(state="normal" if text else "disabled")
        screenshot_path = entry.get("screenshot_path")
        can_open = bool(screenshot_path and Path(screenshot_path).exists())
        self.open_recent_button.configure(state="normal" if can_open else "disabled")
        if can_open:
            try:
                with Image.open(screenshot_path) as image:
                    thumb = image.convert("RGB")
                    thumb.thumbnail((122, 90), Image.Resampling.LANCZOS)
                    self._recent_thumb = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
                    self.recent_thumbnail.configure(image=self._recent_thumb, text="")
            except Exception:
                self.recent_thumbnail.configure(image=None, text="Preview unavailable")
        else:
            self.recent_thumbnail.configure(image=None, text="Text capture")

    def copy_latest_text(self):
        entries = history.get_all()
        if not entries or not entries[0].get("text", "").strip():
            self.update_status("No extracted text is available", "warning")
            return
        if not copy_to_clipboard(entries[0]["text"]):
            self.update_status("Clipboard copy failed", "warning", 0)
            return
        self.update_status("Latest text copied", "success")
        notify("SnapText", "Latest extracted text copied to the clipboard.")

    def open_latest_preview(self):
        entries = history.get_all()
        if not entries:
            return
        entry = entries[0]
        path = entry.get("screenshot_path")
        if not path or not Path(path).exists():
            self.update_status("The screenshot file is no longer available", "warning")
            return
        try:
            with Image.open(path) as image:
                self.show_preview(image.convert("RGB"), entry.get("text", ""), path, entry.get("id"))
        except Exception as exc:
            self.update_status(f"Could not open preview: {exc}", "danger")

    def show_history(self):
        if self._history_window and self._history_window.winfo_exists():
            self._history_window.focus_force()
            return
        self._history_window = HistoryWindow(self)

    def show_settings(self):
        if self._settings_window and self._settings_window.winfo_exists():
            self._settings_window.focus_force()
            return
        self._settings_window = SettingsWindow(self)

    def open_screenshots_folder(self):
        path = Path(config.get("save_directory", "")).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.update_status(f"Could not create screenshots folder: {exc}", "danger")
            return
        if not open_path(path):
            self.update_status("Could not open the screenshots folder", "danger")

    def apply_runtime_settings(self, initial: bool = False):
        apply_theme(config.get("appearance_mode", "system"))
        self.hotkey_label.configure(text=self._format_hotkey(self.capture_hotkey))
        set_debug_logging(config.get("debug_mode", False))
        failures = self.shortcuts.register_defaults(self)
        if failures:
            self.update_status("A global shortcut could not be registered", "warning", 0)
        elif not initial:
            self.update_status("Settings applied", "success")
        if config.get("minimize_to_tray", True):
            self.tray.start()
        else:
            self.tray.stop()

    def show_main_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_close(self):
        self._save_geometry()
        if config.get("minimize_to_tray", True) and self.tray.icon is not None:
            self.withdraw()
            self.update_status("Running in the system tray", "success")
            notify("SnapText", "SnapText is still running in the system tray.")
        else:
            self.exit_application()

    def _save_geometry(self):
        if config.get("remember_window_position", True) and self.state() == "normal":
            config.set("window_geometry", self.geometry())

    def exit_application(self):
        self._save_geometry()
        self.shortcuts.clear()
        self.tray.stop()
        self.destroy()
