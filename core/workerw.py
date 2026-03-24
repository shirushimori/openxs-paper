import ctypes


def get_workerw():
    user32 = ctypes.windll.user32
    progman = user32.FindWindowW("Progman", None)

    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, None)

    workerw = 0

    def enum_windows(hwnd, lparam):
        nonlocal workerw
        shell = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
        if shell:
            workerw = user32.FindWindowExW(0, hwnd, "WorkerW", None)
        return True

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(
        enum_windows
    )

    user32.EnumWindows(enum_proc, 0)
    return workerw
