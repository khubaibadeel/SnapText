from __future__ import annotations

import sys
import time
import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageEnhance, ImageGrab, ImageTk

from .logger import logger
from .system import enable_dpi_awareness


class SnippingOverlay:
    """A DPI-aware, multi-monitor screen-region selector."""

    MIN_SELECTION = 8

    def __init__(self, on_snip_done: Callable[[Image.Image | None], None]):
        self.on_snip_done = on_snip_done
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.start_x = 0
        self.start_y = 0
        self.selection_image_id = None
        self.selection_photo = None
        self.border_id = None
        self.size_label_id = None
        self.instruction_id = None
        self.virtual_left = 0
        self.virtual_top = 0
        self.screen_image: Image.Image | None = None
        self._completed = False
        self._last_render = 0.0
        self._create_overlay()

    def _virtual_screen_geometry(self) -> tuple[int, int, int, int]:
        if sys.platform == "win32":
            try:
                import ctypes

                user32 = ctypes.windll.user32
                return (
                    user32.GetSystemMetrics(76),
                    user32.GetSystemMetrics(77),
                    user32.GetSystemMetrics(78),
                    user32.GetSystemMetrics(79),
                )
            except Exception as exc:
                logger.debug("Virtual screen metrics unavailable: %s", exc)
        assert self.root is not None
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def _create_overlay(self) -> None:
        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(cursor="cross")

        left, top, width, height = self._virtual_screen_geometry()
        self.virtual_left, self.virtual_top = left, top
        try:
            self.screen_image = ImageGrab.grab(all_screens=True)
        except TypeError:
            self.screen_image = ImageGrab.grab()
        except Exception:
            self.root.destroy()
            raise

        # Trust the actual captured image size; Windows virtual metrics can differ under scaling.
        width, height = self.screen_image.size
        self.root.geometry(f"{width}x{height}+{left}+{top}")
        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            cursor="cross",
        )
        self.canvas.pack(fill="both", expand=True)

        dimmed = ImageEnhance.Brightness(self.screen_image).enhance(0.32)
        self.dim_photo = ImageTk.PhotoImage(dimmed)
        self.canvas.create_image(0, 0, image=self.dim_photo, anchor="nw")
        self.instruction_id = self.canvas.create_text(
            width // 2,
            34,
            text="Drag to capture  •  Esc to cancel",
            fill="white",
            font=("Segoe UI", 14, "bold"),
        )
        self.canvas.create_text(
            width // 2,
            60,
            text="Release the mouse to extract text from the selected area",
            fill="#CBD5E1",
            font=("Segoe UI", 10),
        )
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind("<Escape>", lambda _event: self.cancel())
        self.root.bind("<ButtonPress-3>", lambda _event: self.cancel())
        self.root.deiconify()
        self.root.focus_force()
        self.root.mainloop()

    def on_button_press(self, event) -> None:
        self.start_x, self.start_y = event.x, event.y
        self._delete_selection_items()

    def _delete_selection_items(self) -> None:
        assert self.canvas is not None
        for item in (self.selection_image_id, self.border_id, self.size_label_id):
            if item:
                self.canvas.delete(item)
        self.selection_image_id = self.border_id = self.size_label_id = None
        self.selection_photo = None

    def on_move_press(self, event) -> None:
        assert self.canvas is not None and self.screen_image is not None
        now = time.monotonic()
        if now - self._last_render < 0.018:
            return
        self._last_render = now
        x1, x2 = sorted((self.start_x, max(0, min(event.x, self.screen_image.width))))
        y1, y2 = sorted((self.start_y, max(0, min(event.y, self.screen_image.height))))
        if x2 <= x1 or y2 <= y1:
            return
        self._delete_selection_items()
        crop = self.screen_image.crop((x1, y1, x2, y2))
        self.selection_photo = ImageTk.PhotoImage(crop)
        self.selection_image_id = self.canvas.create_image(
            x1, y1, image=self.selection_photo, anchor="nw"
        )
        self.border_id = self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="#3B82F6", width=3
        )
        label_y = y1 - 17 if y1 > 28 else y2 + 17
        self.size_label_id = self.canvas.create_text(
            x1 + 6,
            label_y,
            text=f"{x2 - x1} × {y2 - y1}",
            fill="white",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )

    def on_button_release(self, event) -> None:
        assert self.screen_image is not None
        x1, x2 = sorted((self.start_x, max(0, min(event.x, self.screen_image.width))))
        y1, y2 = sorted((self.start_y, max(0, min(event.y, self.screen_image.height))))
        if x2 - x1 < self.MIN_SELECTION or y2 - y1 < self.MIN_SELECTION:
            self._delete_selection_items()
            return
        image = self.screen_image.crop((x1, y1, x2, y2)).copy()
        self._finish(image)

    def cancel(self) -> None:
        self._finish(None)

    def _finish(self, image: Image.Image | None) -> None:
        if self._completed:
            return
        self._completed = True
        if self.root:
            self.root.withdraw()
            self.root.destroy()
        self.on_snip_done(image)
