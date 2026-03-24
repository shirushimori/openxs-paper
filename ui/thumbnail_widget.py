import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from utils.file_utils import generate_thumbnail

CARD_STYLE = """
    QWidget#card {{
        background-color: #2b2b2b;
        border: 1px solid #444444;
        border-radius: 8px;
    }}
    QWidget#card:hover {{
        border: 1px solid #888888;
        background-color: #333333;
    }}
"""


class ThumbnailWidget(QWidget):
    def __init__(self, video_path: str, click_callback, width: int = 210, height: int = 155):
        super().__init__()

        self.video_path = video_path
        self.click_callback = click_callback

        self.setObjectName("card")
        self.setStyleSheet(CARD_STYLE)
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        img_h = height - 30  # leave room for label

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # thumbnail
        thumb_path = generate_thumbnail(video_path)

        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setFixedSize(width - 12, img_h)
        self.thumbnail.setStyleSheet("border: none; border-radius: 4px; background: #1e1e1e;")

        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path).scaled(
                width - 12, img_h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumbnail.setPixmap(pixmap)
        else:
            self.thumbnail.setText("No Preview")
            self.thumbnail.setStyleSheet("color: #666; border: none;")

        # label
        name = os.path.basename(video_path)
        max_chars = max(10, int((width - 12) / 7))
        if len(name) > max_chars:
            name = name[: max_chars - 3] + "..."

        self.label = QLabel(name)
        self.label.setStyleSheet("color: #ffffff; font-size: 10px; border: none;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.thumbnail)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        self.click_callback(self.video_path)
