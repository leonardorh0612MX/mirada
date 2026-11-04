"""OS input injection for the desktop demo (Windows only, ctypes, stdlib).

Sends real clicks and keystrokes to whatever app has focus, so the gaze
keyboard types into Discord, Notepad, or any window. Pure helpers stay
testable; the two send_* functions touch the OS and are covered live.
"""

import ctypes

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
VK_RETURN = 0x0D
VK_BACK = 0x08
VK_LWIN = 0x5B
VK_ESCAPE = 0x1B
SW_MAXIMIZE = 3
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010


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


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def _send(inputs):
    arr = (_INPUT * len(inputs))(*inputs)
    ctypes.windll.user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))


def clamp_xy(x, y, rect):
    """Clamp a point into (left, top, w, h). Pure (tested).

    Gaze extrapolates past the screen edge (~280 px live variance),
    and an unclamped dwell click once landed 74 px off-monitor.
    """
    l, t, w, h = rect
    return (min(max(x, l), l + w - 1), min(max(y, t), t + h - 1))


def virtual_screen():
    """(vx, vy, vw, vh) of the Windows virtual screen. OS call."""
    g = ctypes.windll.user32.GetSystemMetrics
    return (g(76), g(77), g(78), g(79))


def to_absolute(x, y, vs):
    """Pixels -> SendInput absolute coords (0..65535). Pure (tested)."""
    vx, vy, vw, vh = vs
    ax = int((x - vx) * 65535 / vw)
    ay = int((y - vy) * 65535 / vh)
    return (min(max(ax, 0), 65535), min(max(ay, 0), 65535))


def _abs_move(ax, ay):
    # VIRTUALDESK is not optional: without it, absolute coords map to
    # the PRIMARY monitor only, and every gaze click landed on the
    # laptop while the ring aimed at the external screen (Nov 3).
    return _INPUT(INPUT_MOUSE, _INPUT._U(mi=_MOUSEINPUT(
        ax, ay, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
        | MOUSEEVENTF_VIRTUALDESK, 0, None)))


def click_at(x, y):
    """Left-click at absolute virtual pixels, cursor undisturbed.

    One SendInput batch - move to target, down, up, move back - so
    the compositor never paints the cursor mid-click (the earlier
    three-syscall version flickered visibly ~0.1 s, Nov 3). The
    gaze ring is the pointer; the caregiver's mouse never moves.
    """
    pt = _POINT()
    try:
        has_pos = bool(ctypes.windll.user32.GetCursorPos(
            ctypes.byref(pt)))
    except Exception:
        has_pos = False
    try:
        vs = virtual_screen()
    except Exception:
        vs = None
    if not has_pos or not vs or vs[2] <= 0 or vs[3] <= 0:
        # Degraded: plain move + click, no restore possible.
        try:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
        except Exception:
            pass
    else:
        tax, tay = to_absolute(x, y, vs)
        sax, say = to_absolute(pt.x, pt.y, vs)
        down = _INPUT(INPUT_MOUSE, _INPUT._U(mi=_MOUSEINPUT(
            0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)))
        up = _INPUT(INPUT_MOUSE, _INPUT._U(mi=_MOUSEINPUT(
            0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)))
        _send([_abs_move(tax, tay), down, up, _abs_move(sax, say)])
        return
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


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def foreground_rect():
    """(hwnd, (l, t, r, b)) of the focused window. (None, None) on failure."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        rc = _RECT()
        if hwnd and ctypes.windll.user32.GetWindowRect(hwnd,
                                                       ctypes.byref(rc)):
            return (hwnd, (rc.left, rc.top, rc.right, rc.bottom))
    except Exception:
        pass
    return (None, None)


def center_on_monitor(rect, mon):
    """True when rect's center falls inside (ml, mt, mw, mh). Pure."""
    l, t, r, b = rect
    ml, mt, mw, mh = mon
    return ml <= (l + r) / 2 <= ml + mw and mt <= (t + b) / 2 <= mt + mh


def place_on_monitor(hwnd, mon):
    """Move a window onto (ml, mt, mw, mh) and maximize it. OS call.

    Browsers open wherever they please; gaze lives on one monitor, so
    a launch that lands elsewhere strands the user (Nov 3).
    """
    ml, mt, _mw, _mh = mon
    u = ctypes.windll.user32
    u.SetWindowPos(hwnd, 0, ml + 30, mt + 30, 0, 0,
                   SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
    u.ShowWindow(hwnd, SW_MAXIMIZE)


def park_cursor(mon):
    """Park the system cursor on (ml, mt, mw, mh) if it's elsewhere.

    Gaze clicks restore the cursor wherever it was, so a cursor left
    on the laptop meant all click feedback blinked there (Nov 3):
    the user stared at the gaze screen while the only arrow sat
    across the room. Called once per launch; the caregiver's mouse
    stays live afterwards. True when it moved. OS call.
    """
    ml, mt, mw, mh = mon
    pt = _POINT()
    try:
        if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return False
    except Exception:
        return False
    if center_on_monitor((pt.x, pt.y, pt.x, pt.y), mon):
        return False
    try:
        ctypes.windll.user32.SetCursorPos(ml + mw // 2, mt + mh // 2)
        return True
    except Exception:
        return False
