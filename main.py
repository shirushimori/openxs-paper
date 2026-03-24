import os
import sys

from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow

APP_NAME = "OpenXS Paper"
APP_ID   = "OpenXSPaper.WallpaperEngine.1"   # unique AppUserModelID for taskbar
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "logo.ico")


def apply_dark_palette(app: QApplication):
    palette = QPalette()
    dark   = QColor("#1e1e1e")
    mid    = QColor("#2b2b2b")
    light  = QColor("#3a3a3a")
    text   = QColor("#ffffff")
    subtext = QColor("#cccccc")
    accent = QColor("#666666")

    palette.setColor(QPalette.ColorRole.Window,          dark)
    palette.setColor(QPalette.ColorRole.WindowText,      text)
    palette.setColor(QPalette.ColorRole.Base,            mid)
    palette.setColor(QPalette.ColorRole.AlternateBase,   light)
    palette.setColor(QPalette.ColorRole.Text,            text)
    palette.setColor(QPalette.ColorRole.BrightText,      text)
    palette.setColor(QPalette.ColorRole.Button,          mid)
    palette.setColor(QPalette.ColorRole.ButtonText,      text)
    palette.setColor(QPalette.ColorRole.Highlight,       accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, subtext)
    app.setPalette(palette)


def main():
    # Tell Windows this process has its own identity so the taskbar
    # shows our icon instead of the generic Python icon
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
    apply_dark_palette(app)

    window = MainWindow(app, APP_NAME, ICON_PATH)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
