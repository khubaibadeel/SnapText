"""Shared visual tokens for SnapText's CustomTkinter interface."""

from __future__ import annotations

import customtkinter as ctk

APP_FONT = "Segoe UI"
MONO_FONT = "Consolas"

COLORS = {
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "accent_soft": ("#EAF1FF", "#172554"),
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
    "danger_hover": "#B91C1C",
    "window": ("#F4F7FB", "#0B1120"),
    "surface": ("#FFFFFF", "#111827"),
    "surface_alt": ("#F8FAFC", "#172033"),
    "border": ("#DDE4EE", "#29354D"),
    "text": ("#0F172A", "#F8FAFC"),
    "muted": ("#64748B", "#94A3B8"),
    "selection": "#3B82F6",
}


def font(size: int, weight: str = "normal", family: str = APP_FONT) -> ctk.CTkFont:
    return ctk.CTkFont(family=family, size=size, weight=weight)


def apply_theme(appearance: str = "system") -> None:
    ctk.set_appearance_mode(appearance)
    ctk.set_default_color_theme("blue")


def primary_button(**kwargs):
    defaults = {
        "fg_color": COLORS["accent"],
        "hover_color": COLORS["accent_hover"],
        "corner_radius": 10,
        "font": font(13, "bold"),
        "height": 40,
    }
    defaults.update(kwargs)
    return defaults


def secondary_button(**kwargs):
    defaults = {
        "fg_color": "transparent",
        "hover_color": COLORS["accent_soft"],
        "border_width": 1,
        "border_color": COLORS["border"],
        "text_color": COLORS["text"],
        "corner_radius": 10,
        "font": font(12, "bold"),
        "height": 38,
    }
    defaults.update(kwargs)
    return defaults
