"""Word completion for the gaze keyboard. Stdlib only.

Ranking comes from a frequency-ordered wordlist. The real list is provided
by the `wordfreq` package (installed separately); tests and the no-network
fallback use caller-supplied lists only.
"""

FALLBACK_WORDS = ["hola", "que", "de", "la", "el", "en", "gracias", "si",
                  "no", "por", "favor", "como", "estas", "bien", "voy"]
FALLBACK_WORDS_EN = ["hello", "the", "and", "you", "please", "thank",
                     "thanks", "yes", "no", "water", "help", "need",
                     "want", "good", "here"]


def load_words(n=5000, lang="en"):
    """Frequency-ordered words. wordfreq if present, else fallback."""
    fallback = FALLBACK_WORDS_EN if lang != "es" else FALLBACK_WORDS
    try:
        from wordfreq import top_n_list

        words = top_n_list("es" if lang == "es" else "en", n)
        return words if words else list(fallback)
    except Exception:
        return list(fallback)


def current_prefix(text):
    """Letters after the last space (lowercased). '' when text ends in space."""
    if not text or text[-1] == " ":
        return ""
    return text.split(" ")[-1].lower()


def suggest(prefix, words, k=3):
    """First k words starting with prefix, in list (frequency) order."""
    if not prefix:
        return []
    out = []
    for w in words:
        if w.startswith(prefix) and w != prefix:
            out.append(w)
            if len(out) >= k:
                break
    return out


def apply_suggestion(text, word):
    """Replace the current prefix with word plus a trailing space."""
    if text and text[-1] != " ":
        head, _, _ = text.rpartition(" ")
        text = head + " " if head else ""
    return text + word + " "
