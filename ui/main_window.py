import ctypes
import os
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon, QWheelEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.wallpaper import WallpaperEngine
from core.workerw import get_workerw
from ui.settings_dialog import SettingsDialog
from ui.thumbnail_widget import ThumbnailWidget
from ui.tray import SystemTray
from utils.config import load_config, save_config
from utils.file_utils import scan_videos

DARK_STYLE = """
    QMainWindow, QWidget {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    QMenuBar {
        background-color: #2b2b2b;
        color: #ffffff;
        border-bottom: 1px solid #3a3a3a;
    }
    QMenuBar::item:selected { background-color: #3a3a3a; }
    QMenu {
        background-color: #2b2b2b;
        color: #ffffff;
        border: 1px solid #444;
    }
    QMenu::item:selected { background-color: #444; }
    QMenu::separator { height: 1px; background: #444; margin: 3px 8px; }
    QScrollArea { border: none; background-color: #1e1e1e; }
    QScrollBar:vertical {
        background: #2b2b2b; width: 8px; border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: #555; border-radius: 4px; min-height: 20px;
    }
    QScrollBar:horizontal {
        background: #2b2b2b; height: 8px; border-radius: 4px;
    }
    QScrollBar::handle:horizontal {
        background: #555; border-radius: 4px; min-width: 20px;
    }
"""

CARD_BASE_W = 210
CARD_BASE_H = 155
ZOOM_MIN = 0.6
ZOOM_MAX = 2.0
ZOOM_STEP = 0.1
GRID_PADDING = 22   # left + right content margins


class MainWindow(QMainWindow):
    def __init__(self, app: QApplication, name: str = "OpenXS Paper", icon_path: str = ""):
        super().__init__()

        self.app = app
        self.zoom = 1.0

        self.setWindowTitle(name)
        self.resize(960, 640)
        self.setStyleSheet(DARK_STYLE)

        # center on screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - 480,
            screen.center().y() - 320,
        )

        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # wallpaper engine
        self.wallpaper = WallpaperEngine()
        self.wallpaper.show()

        # attach to desktop
        if sys.platform == "win32":
            hwnd = int(self.wallpaper.winId())
            workerw = get_workerw()
            ctypes.windll.user32.SetParent(hwnd, workerw)

        # config
        self.config = load_config()
        self._restore_state()

        self.setAcceptDrops(True)

        # restore dashboard — prefer saved video list, fall back to re-scanning last folder
        saved_videos = [p for p in self.config.get("dashboard_videos", []) if os.path.exists(p)]
        if saved_videos:
            self.video_list = saved_videos
        else:
            last_folder = self.config.get("last_folder", "")
            if last_folder and os.path.isdir(last_folder):
                self.video_list = scan_videos(last_folder)
            else:
                self.video_list = []

        self.init_ui()
        self.create_menu()

        # system tray (must be after create_menu so toggle_mute/loop exist)
        self.tray = SystemTray(self, app)

        # apply desktop settings from saved config
        self._apply_desktop_settings()

        # defer grid population until after the window is fully shown & laid out
        # so viewport().width() returns the real size (fixes 2-col startup bug)
        if self.video_list:
            QTimer.singleShot(0, self.populate_grid)

    # ------------------------------------------------------------------
    def _restore_state(self):
        if self.config.get("mute"):
            self.wallpaper.audio.setMuted(True)
        if self.config.get("loop") is False:
            self.wallpaper.loop = False
        if self.config.get("restore_on_startup", True):
            last_video = self.config.get("last_video")
            if last_video and os.path.exists(last_video):
                self.wallpaper.set_video(last_video)

    # ------------------------------------------------------------------
    def init_ui(self):
        self.container = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.scroll_widget = QWidget()
        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_widget.setLayout(self.grid)
        self.scroll.setWidget(self.scroll_widget)

        self.main_layout.addWidget(self.scroll)
        self.container.setLayout(self.main_layout)
        self.setCentralWidget(self.container)

    # ------------------------------------------------------------------
    # MENU
    # ------------------------------------------------------------------
    def create_menu(self):
        menubar = self.menuBar()

        # FILE
        file_menu = menubar.addMenu("File")

        open_folder = QAction("Open Folder", self)
        open_folder.triggered.connect(self.open_folder)

        add_video = QAction("Add Video", self)
        add_video.triggered.connect(self.add_video)

        clear = QAction("Clear Dashboard", self)
        clear.triggered.connect(self.clear_dashboard)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)

        file_menu.addActions([open_folder, add_video, clear])
        file_menu.addSeparator()
        file_menu.addAction(settings_action)
        file_menu.addSeparator()

        exit_app = QAction("Exit", self)
        exit_app.triggered.connect(self._quit)
        file_menu.addAction(exit_app)

        # TOOLS
        tools_menu = menubar.addMenu("Tools")

        refresh = QAction("Refresh", self)
        refresh.triggered.connect(self.refresh)

        mute = QAction("Mute / Unmute", self)
        mute.triggered.connect(self.toggle_mute)

        loop = QAction("Toggle Loop", self)
        loop.triggered.connect(self.toggle_loop)

        tools_menu.addActions([refresh, mute, loop])

        # HELP
        help_menu = menubar.addMenu("Help")
        about = QAction("About", self)
        about.triggered.connect(lambda: print("Wallpaper Engine v1"))

        docs = QAction("Documentation", self)
        docs.triggered.connect(lambda: __import__("webbrowser").open(
            "https://github.com/shirushimori/openxs-paper#readme"
        ))

        help_menu.addAction(about)
        help_menu.addAction(docs)

    # ------------------------------------------------------------------
    # SETTINGS
    # ------------------------------------------------------------------
    def open_settings(self):
        exe_path = sys.executable + f' "{os.path.abspath("main.py")}"'
        dlg = SettingsDialog(self.config, exe_path, parent=self)
        if dlg.exec():
            self.wallpaper.audio.setMuted(self.config.get("mute", False))
            self.wallpaper.loop = self.config.get("loop", True)
            self._apply_desktop_settings()
            self.save_settings()

    def _apply_desktop_settings(self):
        """
        Hide/show the app's own taskbar button and Alt+Tab entry.
        Also hides the wallpaper video window from Alt+Tab.

        WS_EX_TOOLWINDOW  → removes window from taskbar + Alt+Tab
        WS_EX_APPWINDOW   → forces window into taskbar (undo of above)
        """
        if sys.platform != "win32":
            return

        GWL_EXSTYLE      = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW  = 0x00040000

        hide = self.config.get("hide_taskbar", False)

        # ── main app window ──────────────────────────────────────────
        hwnd = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if hide:
            style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        else:
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

        # ── wallpaper video window ───────────────────────────────────
        # Always hide the video widget from Alt+Tab — it's a desktop
        # background, users should never see it in the switcher.
        wp_hwnd = int(self.wallpaper.winId())
        wp_style = ctypes.windll.user32.GetWindowLongW(wp_hwnd, GWL_EXSTYLE)
        wp_style = (wp_style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(wp_hwnd, GWL_EXSTYLE, wp_style)

    # ------------------------------------------------------------------
    # GRID
    # ------------------------------------------------------------------
    def _cols(self) -> int:
        """How many cards fit in the current scroll area width."""
        card_w = int(CARD_BASE_W * self.zoom)
        available = self.scroll.viewport().width() - GRID_PADDING
        cols = max(1, available // (card_w + self.grid.spacing()))
        return cols

    def populate_grid(self):
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        card_w = int(CARD_BASE_W * self.zoom)
        card_h = int(CARD_BASE_H * self.zoom)
        cols = self._cols()
        row, col = 0, 0

        for video in self.video_list:
            thumb = ThumbnailWidget(video, self.set_wallpaper, card_w, card_h)
            self.grid.addWidget(thumb, row, col)
            col += 1
            if col == cols:
                col = 0
                row += 1

    def _save_dashboard(self):
        self.config["dashboard_videos"] = self.video_list
        self.save_settings()

    # ------------------------------------------------------------------
    # FILE ACTIONS
    # ------------------------------------------------------------------
    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return
        self.video_list.extend(scan_videos(folder))
        self.config["last_folder"] = folder
        self._save_dashboard()
        self.populate_grid()

    def add_video(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Video")
        if file:
            self.video_list.append(file)
            self._save_dashboard()
            self.populate_grid()

    def clear_dashboard(self):
        self.video_list.clear()
        self.config.pop("last_folder", None)
        self._save_dashboard()
        self.populate_grid()

    # ------------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------------
    def refresh(self):
        self.populate_grid()

    def toggle_mute(self):
        self.wallpaper.toggle_mute()
        self.config["mute"] = self.wallpaper.is_muted()
        self.save_settings()

    def toggle_loop(self):
        self.wallpaper.toggle_loop()
        self.config["loop"] = self.wallpaper.is_looping()
        self.save_settings()

    def set_wallpaper(self, path):
        self.wallpaper.set_video(path)
        self.config["last_video"] = path
        self.save_settings()

    def save_settings(self):
        save_config(self.config)

    # ------------------------------------------------------------------
    # ZOOM  (Ctrl + Scroll)
    # ------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom = min(ZOOM_MAX, round(self.zoom + ZOOM_STEP, 2))
            else:
                self.zoom = max(ZOOM_MIN, round(self.zoom - ZOOM_STEP, 2))
            self.populate_grid()
            event.accept()
        else:
            super().wheelEvent(event)

    # ------------------------------------------------------------------
    # CLOSE → minimize to tray
    # ------------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.video_list:
            # defer so the viewport has updated its size before we measure it
            QTimer.singleShot(0, self.populate_grid)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "OpenXS Paper",
            "Running in background. Double-click tray icon to restore.",
        )

    def _quit(self):
        sys.exit()

    # ------------------------------------------------------------------
    # DRAG & DROP
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.video_list.extend(scan_videos(path))
            elif path.lower().endswith((".mp4", ".mkv", ".avi", ".webm")):
                self.video_list.append(path)
        self._save_dashboard()
        self.populate_grid()
