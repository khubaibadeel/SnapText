from __future__ import annotations

import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..core.config import config
from ..core.logger import set_debug_logging
from ..core.ocr import (
    LANGUAGE_LABELS,
    LANGUAGE_OPTIONS,
    available_language_options,
    configure_detected_ocr,
)
from ..core.paths import resource_path
from ..core.system import open_logs_folder, set_launch_at_startup
from .theme import COLORS, font, primary_button, secondary_button


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Settings — SnapText")
        self.geometry("720x650")
        self.minsize(660, 600)
        self.transient(parent)
        self.configure(fg_color=COLORS["window"])
        self._set_icon()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.save_and_close)
        self.after(150, self.test_ocr_engine)

    def _set_icon(self):
        try:
            self.iconbitmap(str(resource_path("icon.ico")))
        except Exception:
            pass

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 12))
        ctk.CTkLabel(header, text="Settings", font=font(24, "bold"), text_color=COLORS["text"]).pack(side="left")
        self.save_feedback = ctk.CTkLabel(header, text="", font=font(10, "bold"), text_color=COLORS["success"])
        self.save_feedback.pack(side="right")

        self.tabs = ctk.CTkTabview(
            self,
            fg_color=COLORS["surface"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=14,
        )
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 14))
        self.tab_contents = {}
        for name in ("General", "Capture", "OCR", "Appearance"):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            content = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            content.grid(row=0, column=0, sticky="nsew")
            content.grid_columnconfigure(0, weight=1)
            self.tab_contents[name] = content

        self._build_general()
        self._build_capture()
        self._build_ocr()
        self._build_appearance()

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 20))
        ctk.CTkButton(footer, text="Cancel", command=self.destroy, **secondary_button(width=90)).pack(side="right")
        ctk.CTkButton(footer, text="Save Changes", command=self.save_settings, **primary_button(width=130)).pack(side="right", padx=8)

    def _section_title(self, parent, title, description, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=18, pady=(16, 8))
        ctk.CTkLabel(frame, text=title, font=font(15, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(
            frame,
            text=description,
            font=font(10),
            text_color=COLORS["muted"],
            wraplength=600,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def _switch_row(self, parent, row, title, description, variable):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["surface_alt"], corner_radius=10)
        frame.grid(row=row, column=0, sticky="ew", padx=18, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        text_group = ctk.CTkFrame(frame, fg_color="transparent")
        text_group.grid(row=0, column=0, sticky="w", padx=14, pady=11)
        ctk.CTkLabel(text_group, text=title, font=font(12, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(text_group, text=description, font=font(9), text_color=COLORS["muted"]).pack(anchor="w")
        ctk.CTkSwitch(frame, text="", variable=variable, width=42).grid(row=0, column=1, padx=14)

    def _build_general(self):
        tab = self.tab_contents["General"]
        self._section_title(tab, "Application behavior", "Choose what SnapText does after a successful capture.", 0)
        self.auto_copy_var = ctk.BooleanVar(value=config.get("auto_copy_text"))
        self.auto_save_var = ctk.BooleanVar(value=config.get("auto_save_screenshot"))
        self.close_after_copy_var = ctk.BooleanVar(value=config.get("close_preview_after_copy"))
        self.notifications_var = ctk.BooleanVar(value=config.get("show_notifications"))
        self.tray_var = ctk.BooleanVar(value=config.get("minimize_to_tray"))
        self.startup_var = ctk.BooleanVar(value=config.get("launch_at_startup"))
        self._switch_row(tab, 1, "Copy text automatically", "Place recognized text on the clipboard immediately.", self.auto_copy_var)
        self._switch_row(tab, 2, "Save screen captures", "Store screen and clipboard captures in the selected folder.", self.auto_save_var)
        self._switch_row(tab, 3, "Close preview after copying", "Return to the main window after Copy Text is used.", self.close_after_copy_var)
        self._switch_row(tab, 4, "Show notifications", "Display compact success notifications.", self.notifications_var)
        self._switch_row(tab, 5, "Minimize to system tray", "Keep SnapText available without occupying the taskbar.", self.tray_var)
        self._switch_row(tab, 6, "Launch with Windows", "Start SnapText when you sign in to Windows.", self.startup_var)

    def _build_capture(self):
        tab = self.tab_contents["Capture"]
        self._section_title(tab, "Storage and shortcuts", "Set the screenshot folder and global keyboard shortcuts.", 0)

        folder = ctk.CTkFrame(tab, fg_color=COLORS["surface_alt"], corner_radius=10)
        folder.grid(row=1, column=0, sticky="ew", padx=18, pady=5)
        folder.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(folder, text="Screenshot folder", font=font(12, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))
        self.directory_var = ctk.StringVar(value=config.get("save_directory"))
        ctk.CTkEntry(folder, textvariable=self.directory_var, font=font(10), height=34).grid(row=1, column=0, sticky="ew", padx=14, pady=(2, 12))
        ctk.CTkButton(folder, text="Browse", command=self.browse_directory, **secondary_button(width=86, height=34)).grid(row=1, column=1, padx=(0, 14), pady=(2, 12))

        hotkeys = ctk.CTkFrame(tab, fg_color=COLORS["surface_alt"], corner_radius=10)
        hotkeys.grid(row=2, column=0, sticky="ew", padx=18, pady=5)
        hotkeys.grid_columnconfigure(1, weight=1)
        self.capture_hotkey_var = ctk.StringVar(value=config.get("capture_hotkey"))
        self.copy_hotkey_var = ctk.StringVar(value=config.get("copy_latest_hotkey"))
        ctk.CTkLabel(hotkeys, text="New capture", font=font(11, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=(13, 7))
        ctk.CTkEntry(hotkeys, textvariable=self.capture_hotkey_var, font=font(11), height=34).grid(row=0, column=1, sticky="ew", padx=14, pady=(13, 7))
        ctk.CTkLabel(hotkeys, text="Copy latest text", font=font(11, "bold"), text_color=COLORS["text"]).grid(row=1, column=0, sticky="w", padx=14, pady=(7, 13))
        ctk.CTkEntry(hotkeys, textvariable=self.copy_hotkey_var, font=font(11), height=34).grid(row=1, column=1, sticky="ew", padx=14, pady=(7, 13))
        ctk.CTkLabel(
            tab,
            text="Examples: ctrl+shift+s, alt+shift+x. Avoid shortcuts already used by other applications.",
            font=font(9),
            text_color=COLORS["muted"],
        ).grid(row=3, column=0, sticky="w", padx=22, pady=5)

    def _build_ocr(self):
        tab = self.tab_contents["OCR"]
        self._section_title(
            tab,
            "Local recognition",
            "English uses Windows' built-in offline OCR. SnapText automatically uses Tesseract when it is present for optional Urdu support.",
            0,
        )

        choices = ctk.CTkFrame(tab, fg_color=COLORS["surface_alt"], corner_radius=10)
        choices.grid(row=1, column=0, sticky="ew", padx=18, pady=5)
        choices.grid_columnconfigure(1, weight=1)
        current_label = LANGUAGE_LABELS.get(config.get("ocr_language", "eng"), "English")
        self.language_var = ctk.StringVar(value=current_label)
        self.ocr_mode_var = ctk.StringVar(value=config.get("ocr_mode", "balanced").title())
        ctk.CTkLabel(choices, text="Language", font=font(11, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=(13, 7))
        self.language_menu = ctk.CTkOptionMenu(
            choices,
            values=list(LANGUAGE_OPTIONS),
            variable=self.language_var,
            height=34,
        )
        self.language_menu.grid(row=0, column=1, sticky="e", padx=14, pady=(13, 7))
        ctk.CTkLabel(choices, text="Recognition mode", font=font(11, "bold"), text_color=COLORS["text"]).grid(row=1, column=0, sticky="w", padx=14, pady=(7, 13))
        ctk.CTkOptionMenu(choices, values=["Fast", "Balanced", "Accurate"], variable=self.ocr_mode_var, height=34).grid(row=1, column=1, sticky="e", padx=14, pady=(7, 13))

        engine = ctk.CTkFrame(tab, fg_color=COLORS["surface_alt"], corner_radius=10)
        engine.grid(row=2, column=0, sticky="ew", padx=18, pady=5)
        engine.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(engine, text="OCR engine status", font=font(11, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 3))
        ctk.CTkLabel(
            engine,
            text=(
                "No OCR executable is required for English. Available language choices are "
                "detected automatically, so unsupported profiles cannot be selected."
            ),
            font=font(9),
            text_color=COLORS["muted"],
            justify="left",
            wraplength=540,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))
        status_row = ctk.CTkFrame(engine, fg_color="transparent")
        status_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.ocr_status_dot = ctk.CTkLabel(status_row, text="●", width=20, text_color=COLORS["warning"], font=font(13))
        self.ocr_status_dot.pack(side="left")
        self.ocr_status_label = ctk.CTkLabel(
            status_row,
            text="Checking local OCR…",
            font=font(9),
            text_color=COLORS["muted"],
            justify="left",
            wraplength=470,
        )
        self.ocr_status_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(status_row, text="Retest", command=self.test_ocr_engine, **secondary_button(width=72, height=30)).pack(side="right")

    def _build_appearance(self):
        tab = self.tab_contents["Appearance"]
        self._section_title(tab, "Interface and diagnostics", "Control the visual theme and troubleshooting options.", 0)
        appearance = ctk.CTkFrame(tab, fg_color=COLORS["surface_alt"], corner_radius=10)
        appearance.grid(row=1, column=0, sticky="ew", padx=18, pady=5)
        appearance.grid_columnconfigure(1, weight=1)
        self.appearance_var = ctk.StringVar(value=config.get("appearance_mode", "system").title())
        ctk.CTkLabel(appearance, text="Theme", font=font(11, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=14, pady=13)
        ctk.CTkOptionMenu(appearance, values=["System", "Light", "Dark"], variable=self.appearance_var, height=34).grid(row=0, column=1, sticky="e", padx=14, pady=13)

        self.remember_position_var = ctk.BooleanVar(value=config.get("remember_window_position"))
        self.debug_var = ctk.BooleanVar(value=config.get("debug_mode"))
        self._switch_row(tab, 2, "Remember window position", "Restore the main window where you last used it.", self.remember_position_var)
        self._switch_row(tab, 3, "Debug logging", "Record additional technical details for troubleshooting.", self.debug_var)

        tools = ctk.CTkFrame(tab, fg_color="transparent")
        tools.grid(row=4, column=0, sticky="ew", padx=18, pady=14)
        ctk.CTkButton(tools, text="Open Logs Folder", command=open_logs_folder, **secondary_button(width=125)).pack(side="left")
        ctk.CTkButton(
            tools,
            text="Reset Settings",
            command=self.reset_settings,
            fg_color="transparent",
            hover_color=("#FEE2E2", "#451A1A"),
            border_width=1,
            border_color=COLORS["danger"],
            text_color=COLORS["danger"],
            corner_radius=10,
            font=font(11, "bold"),
            height=38,
            width=115,
        ).pack(side="right")

    def browse_directory(self):
        path = filedialog.askdirectory(parent=self, initialdir=self.directory_var.get() or None)
        if path:
            self.directory_var.set(path)

    def test_ocr_engine(self):
        self.ocr_status_dot.configure(text_color=COLORS["warning"])
        self.ocr_status_label.configure(text="Checking local OCR…")
        selected_code = LANGUAGE_OPTIONS.get(self.language_var.get(), "eng")

        def worker():
            options = available_language_options()
            status = configure_detected_ocr(selected_code)
            self.after(0, lambda: self._show_ocr_status(status, options))

        threading.Thread(target=worker, daemon=True).start()

    # Compatibility with automation or extensions that used the older method.
    test_tesseract = test_ocr_engine

    def _show_ocr_status(self, status, options: dict[str, str]):
        labels = list(options)
        self.language_menu.configure(values=labels)
        if self.language_var.get() not in labels:
            self.language_var.set("English" if "English" in labels else labels[0])

        profile_text = ", ".join(labels)
        if status.ready:
            self.ocr_status_dot.configure(text_color=COLORS["success"])
            self.ocr_status_label.configure(
                text=f"Ready — {status.engine_label}\nAvailable profiles: {profile_text}"
            )
        else:
            self.ocr_status_dot.configure(text_color=COLORS["warning"])
            self.ocr_status_label.configure(
                text=f"{status.message}\nAvailable profiles: {profile_text}"
            )

    def _validate(self) -> bool:
        capture = self.capture_hotkey_var.get().strip().lower()
        copy_latest = self.copy_hotkey_var.get().strip().lower()
        if not capture or not copy_latest:
            messagebox.showerror("Invalid shortcuts", "Both global shortcuts must contain a value.", parent=self)
            self.tabs.set("Capture")
            return False
        if capture == copy_latest:
            messagebox.showerror("Invalid shortcuts", "New Capture and Copy Latest Text cannot use the same shortcut.", parent=self)
            self.tabs.set("Capture")
            return False
        if not self.directory_var.get().strip():
            messagebox.showerror("Invalid folder", "Choose a screenshot folder.", parent=self)
            self.tabs.set("Capture")
            return False
        if self.language_var.get() not in LANGUAGE_OPTIONS:
            self.language_var.set("English")
        return True

    def save_settings(self):
        if not self._validate():
            return
        startup_requested = self.startup_var.get()
        startup_ok, startup_message = set_launch_at_startup(startup_requested)
        if startup_requested and not startup_ok:
            self.startup_var.set(False)
            messagebox.showwarning("Startup setting", startup_message, parent=self)

        values = {
            "auto_copy_text": self.auto_copy_var.get(),
            "auto_save_screenshot": self.auto_save_var.get(),
            "close_preview_after_copy": self.close_after_copy_var.get(),
            "show_notifications": self.notifications_var.get(),
            "minimize_to_tray": self.tray_var.get(),
            "launch_at_startup": startup_requested and startup_ok,
            "save_directory": self.directory_var.get().strip(),
            "capture_hotkey": self.capture_hotkey_var.get().strip().lower(),
            "copy_latest_hotkey": self.copy_hotkey_var.get().strip().lower(),
            "ocr_language": LANGUAGE_OPTIONS[self.language_var.get()],
            "ocr_mode": self.ocr_mode_var.get().lower(),
            "appearance_mode": self.appearance_var.get().lower(),
            "remember_window_position": self.remember_position_var.get(),
            "debug_mode": self.debug_var.get(),
            "first_run_complete": True,
        }
        config.set_many(values)
        set_debug_logging(values["debug_mode"])
        self.parent.apply_runtime_settings()
        self.parent._check_ocr_engine_async()
        self.save_feedback.configure(text="Saved")
        self.after(1200, lambda: self.save_feedback.configure(text="") if self.winfo_exists() else None)

    def save_and_close(self):
        if self._validate():
            self.save_settings()
            self.destroy()

    def reset_settings(self):
        if not messagebox.askyesno(
            "Reset settings",
            "Restore all SnapText settings to their defaults?",
            parent=self,
            icon="warning",
        ):
            return
        set_launch_at_startup(False)
        config.reset()
        self.destroy()
        self.parent.apply_runtime_settings()
        self.parent.show_settings()
