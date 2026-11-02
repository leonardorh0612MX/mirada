"""UI language tables: English default, Spanish second. Stdlib only.

The contest is judged in English, so DEFAULT_LANG is "en" and every
user-facing string lives here (Python side) or in the matching I18N dict
in site/board.html (client side). Cell labels are also config keys, so
both languages keep exactly 8 cells; func rows carry stable ids with
per-language display labels. Pure (tested).
"""

DEFAULT_LANG = "en"
LANGS = ("en", "es")


def norm_lang(lang):
    """Coerce anything into "en"|"es". Pure."""
    return lang if lang in LANGS else DEFAULT_LANG


CELLS = {
    "en": [("YES", "Yes"),
            ("NO", "No"),
            ("WATER", "I want water, please"),
            ("BATHROOM", "I need to use the bathroom"),
            ("HELP", "I need help, please come"),
            ("THANKS", "Thank you"),
            ("COME", "Please come, I need you"),
            ("PAIN", "I am in pain, please help me")],
    "es": [("SI", "Sí"),
            ("NO", "No"),
            ("AGUA", "Quiero agua, por favor"),
            ("BAÑO", "Necesito ir al baño"),
            ("AYUDA", "Necesito ayuda, por favor ven"),
            ("GRACIAS", "Gracias"),
            ("LLAMAR", "Por favor ven, te necesito"),
            ("DOLOR", "Me duele, por favor ayúdame")],
}

# (stable id, display label) per func row. Dispatch matches on id.
FUNCS = {
    "en": {"main": [("recal", "RECAL"), ("speak", "SPEAK"),
                     ("clear", "CLEAR"), ("settings", "SETTINGS"),
                     ("apps", "APPS"), ("keyboard", "KEYBOARD"),
                     ("quit", "QUIT")],
           "apps": [("phrases", "PHRASES"), ("recal", "RECAL"),
                     ("quit", "QUIT")],
           "kb": [("phrases", "BACK"), ("speak", "SPEAK"),
                   ("send", "SEND"), ("quit", "QUIT")]},
    "es": {"main": [("recal", "RECAL"), ("speak", "SPEAK"),
                     ("clear", "CLEAR"), ("settings", "SETTINGS"),
                     ("apps", "APPS"), ("keyboard", "TECLADO"),
                     ("quit", "QUIT")],
           "apps": [("phrases", "FRASES"), ("recal", "RECAL"),
                     ("quit", "QUIT")],
           "kb": [("phrases", "VOLVER"), ("speak", "DECIR"),
                   ("send", "ENVIAR"), ("quit", "QUIT")]},
}

STR = {
    "en": {
        "enroll_natural": "look at the dot · head and eyes together",
        "enroll_suffix": "· eyes on the dot",
        "pose_center": "face centered",
        "pose_left": "turn your head left",
        "pose_right": "turn your head right",
        "pose_up": "lift your chin a little",
        "pose_down": "lower your chin a little",
        "tk_step1": "STEP 1 · YOUR FACE",
        "tk_step1_sub": "get comfortable · sit as you always do",
        "tk_calib": "CALIBRATION · {}/{}",
        "tk_dot": "look at the green dot · head and eyes together",
        "tk_saved": "point saved",
        "tk_voice": "Voice",
        "tk_phrases": "Phrases per cell",
        "tk_save": "Save",
        "tk_close": "Close",
        "face_turn": "face the screen",
        "face_gone": "NO FACE - come back to the camera",
        "guide_search": "finding your face…",
        "guide_ok": "that's your posture · starting…",
        "guide_fix": "return to your comfortable posture",
        "bar_hint": "look + hold to speak…",
        "bar_outside": "gaze outside trusted area",
        "settings_title": "Mirada · Settings",
        "back_sub": "BACK",
        "kb_main": "KEYBOARD",
        "kb_sub": "TYPE",
    },
    "es": {
        "enroll_natural": "mira el punto · cabeza y ojos juntos",
        "enroll_suffix": "· ojos en el punto",
        "pose_center": "rostro al centro",
        "pose_left": "gira la cabeza a la izquierda",
        "pose_right": "gira la cabeza a la derecha",
        "pose_up": "levanta un poco la barbilla",
        "pose_down": "baja un poco la barbilla",
        "tk_step1": "PASO 1 · TU ROSTRO",
        "tk_step1_sub": "ponte cómodo · así como te sientas siempre",
        "tk_calib": "CALIBRACIÓN · {}/{}",
        "tk_dot": "mira el punto verde · cabeza y ojos juntos",
        "tk_saved": "punto guardado",
        "tk_voice": "Voz",
        "tk_phrases": "Frases por celda",
        "tk_save": "Guardar",
        "tk_close": "Cerrar",
        "face_turn": "mira a la pantalla",
        "face_gone": "SIN ROSTRO - vuelve a la cámara",
        "guide_search": "busca tu rostro…",
        "guide_ok": "esa es tu postura · empezamos…",
        "guide_fix": "vuelve a tu postura cómoda",
        "bar_hint": "mira + hold para hablar…",
        "bar_outside": "mirada fuera del área confiable",
        "settings_title": "Mirada · Ajustes",
        "back_sub": "VOLVER",
        "kb_main": "TECLADO",
        "kb_sub": "ESCRIBIR",
    },
}


def cells_for_lang(lang):
    """8 (label, phrase) cells for the language. Pure."""
    return list(CELLS[norm_lang(lang)])


def funcs_for_lang(lang, row):
    """(id, label) funcs for row in main|apps|kb. Pure."""
    return list(FUNCS[norm_lang(lang)][row])


def s(lang, key, *args):
    """Chrome string, English fallback. Pure."""
    lang = norm_lang(lang)
    text = STR[lang].get(key, STR["en"].get(key, key))
    return text.format(*args) if args else text
