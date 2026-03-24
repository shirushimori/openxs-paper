import os

import cv2

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".webm")


def scan_videos(folder):
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(VIDEO_EXTENSIONS)
    ]


def generate_thumbnail(video_path, cache_dir="assets/cache"):
    os.makedirs(cache_dir, exist_ok=True)

    filename = os.path.basename(video_path)
    thumb_path = os.path.join(cache_dir, filename + ".jpg")

    if os.path.exists(thumb_path):
        return thumb_path

    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()

    if success:
        frame = cv2.resize(frame, (200, 120))
        cv2.imwrite(thumb_path, frame)

    cap.release()
    return thumb_path
