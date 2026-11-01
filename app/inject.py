"""OS input injection for the desktop demo (Windows only, ctypes, stdlib).

Sends real clicks and keystrokes to whatever app has focus, so the gaze
keyboard types into Discord, Notepad, or any window. Pure helpers stay
testable; the two send_* functions touch the OS and are covered live.
"""

import ctypes

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
VK_RETURN = 0x0D
VK_BACK = 0x08
VK_LWIN = 0x5B
VK_ESCAPE = 0x1B


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]

    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]


def _send(inputs):
    arr = (_INPUT * len(inputs))(*inputs)
    ctypes.windll.user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))


def click_at(x, y):
    """Move the cursor (absolute virtual pixels) and left-click."""
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    down = _INPUT(INPUT_MOUSE, _INPUT._U(mi=_MOUSEINPUT(
        0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)))
    up = _INPUT(INPUT_MOUSE, _INPUT._U(mi=_MOUSEINPUT(
        0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)))
    _send([down, up])


def key_events(text):
    """Build keyboard INPUTs for unicode text plus special tokens.

    Tokens: {ENTER}, {BKSP}, {WIN}, {ESC}, {SPACE}. Pure: returns the
    INPUT list without sending (testable).
    """
    inputs = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == "{":
            j = text.find("}", i)
            token = text[i:j + 1] if j > 0 else ""
            vk = {"{ENTER}": VK_RETURN, "{BKSP}": VK_BACK,
                  "{WIN}": VK_LWIN, "{ESC}": VK_ESCAPE}.get(token)
            if vk is not None:
                inputs.append(_INPUT(INPUT_KEYBOARD, _INPUT._U(
                    ki=_KEYBDINPUT(vk, 0, 0, 0, None))))
                inputs.append(_INPUT(INPUT_KEYBOARD, _INPUT._U(
                    ki=_KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None))))
                i = j + 1
                continue
        ch = " " if text[i:i + 7] == "{SPACE}" else text[i]
        i += 7 if ch == " " and text[i:i + 7] == "{SPACE}" else 1
        code = ord(ch)
        inputs.append(_INPUT(INPUT_KEYBOARD, _INPUT._U(
            ki=_KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, None))))
        inputs.append(_INPUT(INPUT_KEYBOARD, _INPUT._U(
            ki=_KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None))))
    return inputs


def send_text(text):
    """Type text (plus tokens) into the focused window."""
    inputs = key_events(text)
    if inputs:
        _send(inputs)


_HOTKEY_ARMED = [True]


def shift_q_pressed():
    """Edge-triggered global Shift+Q check. Needs no window focus.

    Poll every frame; returns True once per physical press. The desktop
    overlay never owns keyboard focus, so Tk bindings cannot quit it.
    """
    try:
        down = (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000
                and ctypes.windll.user32.GetAsyncKeyState(0x51) & 0x8000)
    except Exception:
        return False
    if down and _HOTKEY_ARMED[0]:
        _HOTKEY_ARMED[0] = False
        return True
    if not down:
        _HOTKEY_ARMED[0] = True
    return False


def foreground_title():
    """Title of the currently focused window ('' when unavailable)."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""
