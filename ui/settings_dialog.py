import sys
import winreg

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

APP_NAME = "OpenXSPaper"
APP_PATH = None  # set at runtime from main


DIALOG_STYLE = """
    QDialog {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    QGroupBox {
        background-color: #2b2b2b;
        border: 1px solid #444;
        border-radius: 6px;
        margin-top: 10px;
        padding: 8px;
        color: #ffffff;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }
    QCheckBox {
        color: #ffffff;
        spacing: 10px;
        min-height: 36px;
        padding: 4px 8px;
        background-color: #2e2e2e;
        border-radius: 5px;
    }
    QCheckBox::indicator {
        width: 18px; height: 18px;
        border: 1px solid #666;
        border-radius: 3px;
        background: #333;
    }
    QCheckBox::indicator:checked {
        background: #888;
        border-color: #aaa;
    }
    QLabel { color: #cccccc; min-height: 24px; padding: 2px 8px; }
    QComboBox {
        background-color: #333;
        color: #fff;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 4px 8px;
    }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView {
        background-color: #2b2b2b;
        color: #fff;
        selection-background-color: #555;
    }
    QDialogButtonBox QPushButton {
        background-color: #3a3a3a;
        color: #ffffff;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 6px 18px;
        min-width: 70px;
    }
    QDialogButtonBox QPushButton:hover { background-color: #505050; }
    QDialogButtonBox QPushButton:pressed { background-color: #222; }
"""


def _get_autostart() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


def _set_autostart(enable: bool, exe_path: str):
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE,
    )
    if enable:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
    else:
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)


class SettingsDialog(QDialog):
    def __init__(self, config: dict, exe_path: str, parent=None):
        super().__init__(parent)
        self.config = config
        self.exe_path = exe_path

        self.setWindowTitle("Settings")
        self.setFixedSize(420, 680)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Startup ──────────────────────────────────────────────────
        startup_group = QGroupBox("Startup")
        startup_form = QFormLayout(startup_group)
        startup_form.setSpacing(6)
        startup_form.setContentsMargins(8, 8, 8, 8)

        self.autostart_cb = QCheckBox("Launch with Windows")
        self.autostart_cb.setChecked(_get_autostart())
        startup_form.addRow(self.autostart_cb)

        self.restore_cb = QCheckBox("Restore last wallpaper on startup")
        self.restore_cb.setChecked(config.get("restore_on_startup", True))
        startup_form.addRow(self.restore_cb)

        layout.addWidget(startup_group)

        # ── Multi-Monitor ─────────────────────────────────────────────
        monitor_group = QGroupBox("Multi-Monitor")
        monitor_form = QFormLayout(monitor_group)
        monitor_form.setSpacing(6)
        monitor_form.setContentsMargins(8, 8, 8, 8)

        self.multi_monitor_cb = QCheckBox("Span wallpaper across all monitors")
        self.multi_monitor_cb.setChecked(config.get("multi_monitor", False))
        monitor_form.addRow(self.multi_monitor_cb)

        monitor_form.addRow(QLabel("Monitor target:"))
        self.monitor_combo = QComboBox()
        self.monitor_combo.addItems(["All Monitors", "Primary Only", "Secondary Only"])
        saved = config.get("monitor_target", "All Monitors")
        idx = self.monitor_combo.findText(saved)
        self.monitor_combo.setCurrentIndex(idx if idx >= 0 else 0)
        monitor_form.addRow(self.monitor_combo)

        layout.addWidget(monitor_group)

        # ── Playback ──────────────────────────────────────────────────
        playback_group = QGroupBox("Playback")
        playback_form = QFormLayout(playback_group)
        playback_form.setSpacing(6)
        playback_form.setContentsMargins(8, 8, 8, 8)

        self.mute_cb = QCheckBox("Start muted")
        self.mute_cb.setChecked(config.get("mute", False))
        playback_form.addRow(self.mute_cb)

        self.loop_cb = QCheckBox("Loop video")
        self.loop_cb.setChecked(config.get("loop", True))
        playback_form.addRow(self.loop_cb)

        layout.addWidget(playback_group)

        # ── Desktop ───────────────────────────────────────────────────
        desktop_group = QGroupBox("Desktop")
        desktop_form = QFormLayout(desktop_group)
        desktop_form.setSpacing(6)
        desktop_form.setContentsMargins(8, 8, 8, 8)

        self.all_desktops_cb = QCheckBox("Enable wallpaper on all virtual desktops")
        self.all_desktops_cb.setChecked(config.get("all_desktops", True))
        desktop_form.addRow(self.all_desktops_cb)

        self.hide_taskbar_cb = QCheckBox("Hide app icon from taskbar && Alt+Tab")
        self.hide_taskbar_cb.setChecked(config.get("hide_taskbar", False))
        desktop_form.addRow(self.hide_taskbar_cb)

        layout.addWidget(desktop_group)

        # ── Buttons ───────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self):
        _set_autostart(self.autostart_cb.isChecked(), self.exe_path)

        self.config["restore_on_startup"] = self.restore_cb.isChecked()
        self.config["multi_monitor"]      = self.multi_monitor_cb.isChecked()
        self.config["monitor_target"]     = self.monitor_combo.currentText()
        self.config["mute"]               = self.mute_cb.isChecked()
        self.config["loop"]               = self.loop_cb.isChecked()
        self.config["all_desktops"]       = self.all_desktops_cb.isChecked()
        self.config["hide_taskbar"]       = self.hide_taskbar_cb.isChecked()

        self.accept()
