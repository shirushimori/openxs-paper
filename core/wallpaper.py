from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QWidget

# How many milliseconds before the real end we trigger the swap.
# The standby player starts rendering below the active one at this point,
# so by the time the active video would have gone black the standby is
# already painting and the cut is invisible.
EARLY_SWAP_MS = 1010


class _Slot:
    """One player + audio + video widget."""

    def __init__(self, parent: QWidget):
        self.widget = QVideoWidget(parent)
        self.widget.setStyleSheet("background: black;")
        self.widget.setGeometry(0, 0, 1920, 1080)

        self.audio = QAudioOutput()
        self.audio.setVolume(0)

        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.widget)

    def load(self, path: str):
        self.player.setSource(QUrl.fromLocalFile(path))

    def play_from_start(self):
        self.player.setPosition(0)
        self.player.play()

    def pause(self):
        self.player.pause()

    def duration_ms(self) -> int:
        return self.player.duration()

    def position_ms(self) -> int:
        return self.player.position()

    def is_buffered(self) -> bool:
        return self.player.mediaStatus() in (
            QMediaPlayer.MediaStatus.BufferedMedia,
            QMediaPlayer.MediaStatus.LoadedMedia,
        )

    def is_at_end(self) -> bool:
        return self.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia

    def set_muted(self, muted: bool):
        self.audio.setMuted(muted)

    def is_muted(self) -> bool:
        return self.audio.isMuted()


class WallpaperEngine(QWidget):
    """
    Ping-pong double-buffer — zero flicker seamless loop.

    Early-swap trick:
        Instead of waiting for EndOfMedia (which already shows black),
        we watch the active player's position. When it gets within
        EARLY_SWAP_MS (1 second) of the end we start the standby player
        rendering *below* the active one. By the time the active video
        actually ends the standby has already decoded its first frame and
        is painting — so we raise it and the cut is invisible.

    Timeline:
        A playing  [...........|←1s→]   B pre-loaded hidden [\\\\\\]
                               ↑ swap triggered here
        B starts playing below A (A still visible on top)
        B.position > 0  →  raise B, pause A  →  seamless cut
        A reloads quietly for next swap
    """

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setGeometry(0, 0, 1920, 1080)
        self.setStyleSheet("background: black;")

        self._a = _Slot(self)
        self._b = _Slot(self)
        self._a.widget.raise_()

        self._path: str = ""
        self._loop: bool = True
        self._active: _Slot = self._a
        self._standby: _Slot = self._b
        self._swapping: bool = False

        # 100 ms poll — checks position for early-swap trigger
        self._poll = QTimer(self)
        self._poll.setInterval(100)
        self._poll.timeout.connect(self._tick)

    # ------------------------------------------------------------------ public

    def set_video(self, path: str):
        self._path = path
        self._swapping = False
        self._poll.stop()

        self._a.player.setSource(QUrl())
        self._b.player.setSource(QUrl())

        self._active  = self._a
        self._standby = self._b

        self._a.load(path)
        self._b.load(path)

        self._wait_for_buffer(self._a, self._start_playback)

    def toggle_mute(self):
        muted = not self._active.is_muted()
        self._a.set_muted(muted)
        self._b.set_muted(muted)

    def toggle_loop(self):
        self._loop = not self._loop

    def is_muted(self) -> bool:
        return self._a.is_muted()

    def is_looping(self) -> bool:
        return self._loop

    @property
    def audio(self):
        return self._a.audio

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    # ------------------------------------------------------------------ internal

    def _wait_for_buffer(self, slot: _Slot, callback):
        if slot.is_buffered():
            callback()
        else:
            QTimer.singleShot(50, lambda: self._wait_for_buffer(slot, callback))

    def _start_playback(self):
        self._active.widget.raise_()
        self._active.play_from_start()
        self._poll.start()

    def _tick(self):
        if not self._loop or not self._path or self._swapping:
            return

        dur = self._active.duration_ms()
        pos = self._active.position_ms()

        # fallback: if we somehow missed the early trigger, catch EndOfMedia too
        if self._active.is_at_end():
            self._swapping = True
            self._begin_swap()
            return

        # early trigger: within EARLY_SWAP_MS of the end
        if dur > 0 and pos > 0 and (dur - pos) <= EARLY_SWAP_MS:
            self._swapping = True
            self._begin_swap()

    def _begin_swap(self):
        """Start standby rendering below active, then wait for its first frame."""
        nxt = self._standby
        if not nxt.is_buffered():
            QTimer.singleShot(50, self._begin_swap)
            return

        # standby starts playing hidden below active
        nxt.play_from_start()
        self._wait_for_first_frame(nxt)

    def _wait_for_first_frame(self, slot: _Slot):
        """Wait until slot has decoded frame 1, then cut."""
        if slot.position_ms() > 0:
            self._cut_to_standby()
        else:
            QTimer.singleShot(16, lambda: self._wait_for_first_frame(slot))

    def _cut_to_standby(self):
        prev = self._active
        nxt  = self._standby

        self._active  = nxt
        self._standby = prev
        self._swapping = False

        # raise new active — it's already painting, cut is invisible
        nxt.widget.raise_()

        # freeze old on last frame (pause keeps the frame visible, stop clears it)
        prev.pause()

        # reload old quietly for next swap
        prev.load(self._path)
