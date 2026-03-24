import os

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

ICON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "icons", "logo.ico",
)


class SystemTray(QSystemTrayIcon):
    def __init__(self, window, app):
        if os.path.exists(ICON_PATH):
            icon = QIcon(ICON_PATH)
        else:
            icon = app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon)

        super().__init__(icon, app)

        self.window = window
        self.setToolTip("OpenXS Paper")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
            }
            QMenu::item:selected { background-color: #444; }
        """)

        show_action = menu.addAction("Show")
        show_action.triggered.connect(self._show_window)

        menu.addSeparator()

        mute_action = menu.addAction("Mute / Unmute")
        mute_action.triggered.connect(window.toggle_mute)

        loop_action = menu.addAction("Toggle Loop")
        loop_action.triggered.connect(window.toggle_loop)

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(window._quit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self.show()

    def _show_window(self):
        self.window.showNormal()
        self.window.activateWindow()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()
