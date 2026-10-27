from __future__ import annotations

import datetime as dt
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from ..core.clipboard import copy_to_clipboard
from ..core.history import history
from ..core.notifications import notify
from ..core.paths import resource_path
from ..core.system import open_path
from .preview_window import PreviewWindow
from .theme import COLORS, font, primary_button, secondary_button


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._thumbnails: list[ctk.CTkImage] = []
        self.title("Capture History — SnapText")
        self.geometry("820x680")
        self.minsize(700, 560)
        self.transient(parent)
        self.configure(fg_color=COLORS["window"])
        self._set_icon()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

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
        title_group = ctk.CTkFrame(header, fg_color="transparent")
        title_group.pack(side="left")
        ctk.CTkLabel(title_group, text="Capture history", font=font(24, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(title_group, text="Search, copy, and reopen previous OCR results.", font=font(11), text_color=COLORS["muted"]).pack(anchor="w")
        ctk.CTkButton(header, text="Clear All", command=self.clear_history, fg_color="transparent", hover_color=("#FEE2E2", "#451A1A"), border_width=1, border_color=COLORS["danger"], text_color=COLORS["danger"], corner_radius=9, height=36, width=90, font=font(11, "bold")).pack(side="right")

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(0, weight=1)
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(filters, textvariable=self.search_var, placeholder_text="Search extracted text…", height=38, corner_radius=9, border_color=COLORS["border"], font=font(11))
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.search_var.trace_add("write", lambda *_: self.refresh_history())
        self.date_filter = ctk.CTkSegmentedButton(filters, values=["Today", "This Week", "All"], command=lambda _value: self.refresh_history(), selected_color=COLORS["accent"], selected_hover_color=COLORS["accent_hover"], font=font(10, "bold"))
        self.date_filter.set("All")
        self.date_filter.grid(row=0, column=1)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.refresh_history()

    def _filtered_entries(self):
        query = self.search_var.get().strip().lower()
        period = self.date_filter.get()
        now = dt.datetime.now()
        results = []
        for entry in history.get_all():
            text = entry.get("text", "") or ""
            if query and query not in text.lower():
                continue
            try:
                created = dt.datetime.fromisoformat(entry.get("timestamp", ""))
            except Exception:
                created = now
            if period == "Today" and created.date() != now.date():
                continue
            if period == "This Week" and created < now - dt.timedelta(days=7):
                continue
            results.append(entry)
        return results

    def refresh_history(self):
        if not hasattr(self, "scroll_frame"):
            return
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self._thumbnails.clear()
        entries = self._filtered_entries()
        if not entries:
            empty = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["surface"], border_width=1, border_color=COLORS["border"], corner_radius=14)
            empty.grid(row=0, column=0, sticky="ew", padx=6, pady=18)
            ctk.CTkLabel(empty, text="No captures found", font=font(18, "bold"), text_color=COLORS["text"]).pack(pady=(34, 6))
            message = "Your extracted text will appear here." if not history.get_all() else "Try changing the search or date filter."
            ctk.CTkLabel(empty, text=message, font=font(11), text_color=COLORS["muted"]).pack(pady=(0, 34))
            return
        for row, entry in enumerate(entries):
            self._create_entry(entry, row)

    def _create_entry(self, entry: dict, row: int):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["surface"], border_width=1, border_color=COLORS["border"], corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", padx=6, pady=6)
        card.grid_columnconfigure(1, weight=1)

        path = entry.get("screenshot_path")
        thumbnail_label = ctk.CTkLabel(card, text="Text", width=104, height=78, fg_color=COLORS["surface_alt"], corner_radius=8, text_color=COLORS["muted"], font=font(10, "bold"))
        thumbnail_label.grid(row=0, column=0, rowspan=2, padx=(14, 12), pady=14, sticky="nw")
        image_available = bool(path and Path(path).exists())
        if image_available:
            try:
                with Image.open(path) as image:
                    thumb = image.convert("RGB")
                    thumb.thumbnail((100, 74), Image.Resampling.LANCZOS)
                    ctk_image = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
                    self._thumbnails.append(ctk_image)
                    thumbnail_label.configure(image=ctk_image, text="")
            except Exception:
                image_available = False

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=(13, 4))
        timestamp = entry.get("timestamp", "").replace("T", " ")[:16]
        source = (entry.get("source") or "screen").title()
        ctk.CTkLabel(content, text=f"{timestamp}  •  {source}", font=font(10, "bold"), text_color=COLORS["muted"]).pack(anchor="w")
        text = (entry.get("text") or "").strip()
        snippet = text[:320] + ("…" if len(text) > 320 else "") if text else "No readable text was detected."
        ctk.CTkLabel(content, text=snippet, font=font(11), text_color=COLORS["text"] if text else COLORS["muted"], justify="left", anchor="nw", wraplength=560).pack(anchor="w", fill="x", pady=(5, 0))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=(4, 13))
        copy_button = ctk.CTkButton(actions, text="Copy", command=lambda value=text: self.copy_text(value), **secondary_button(width=70, height=30))
        copy_button.pack(side="left")
        copy_button.configure(state="normal" if text else "disabled")
        preview_button = ctk.CTkButton(actions, text="Open Preview", command=lambda item=entry: self.open_preview(item), **secondary_button(width=102, height=30))
        preview_button.pack(side="left", padx=7)
        preview_button.configure(state="normal" if image_available else "disabled")
        open_button = ctk.CTkButton(actions, text="Open Image", command=lambda value=path: self.open_image(value), **secondary_button(width=92, height=30))
        open_button.pack(side="left")
        open_button.configure(state="normal" if image_available else "disabled")
        ctk.CTkButton(actions, text="Delete", command=lambda item_id=entry.get("id"): self.delete_entry(item_id), fg_color="transparent", hover_color=("#FEE2E2", "#451A1A"), text_color=COLORS["danger"], width=66, height=30, corner_radius=8, font=font(10, "bold")).pack(side="right")

    def copy_text(self, text: str):
        if not text:
            return
        if not copy_to_clipboard(text):
            self.parent.update_status("Clipboard copy failed", "warning", 0)
            return
        self.parent.update_status("Text copied from history", "success")
        notify("SnapText", "History text copied to the clipboard.")

    def open_preview(self, entry: dict):
        path = entry.get("screenshot_path")
        if not path or not Path(path).exists():
            self.parent.update_status("The screenshot file is missing", "warning")
            return
        try:
            with Image.open(path) as image:
                PreviewWindow(self.parent, image.convert("RGB"), entry.get("text", ""), path, entry.get("id"))
        except Exception as exc:
            self.parent.update_status(f"Could not open preview: {exc}", "danger")

    def open_image(self, path):
        if not path or not open_path(path):
            self.parent.update_status("The screenshot file is missing", "warning")

    def delete_entry(self, entry_id: str):
        if not messagebox.askyesno("Delete capture", "Delete this capture from history? The screenshot file will not be deleted.", parent=self):
            return
        history.delete_entry(entry_id)
        self.parent.refresh_recent_capture()
        self.refresh_history()

    def clear_history(self):
        if not history.get_all():
            return
        if not messagebox.askyesno("Clear history", "Clear all SnapText history? Saved screenshot files will remain on disk.", parent=self, icon="warning"):
            return
        history.clear()
        self.parent.refresh_recent_capture()
        self.refresh_history()
