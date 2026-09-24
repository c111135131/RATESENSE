import html
import os
import re

_TAG_RE = re.compile(r"<[^>]*>")
MAX_TEXT_LEN = 300

_UNSAFE_FILENAME_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]")
MAX_FILENAME_LEN = 120


def sanitize_text(value):
    if value is None:
        return None
    value = str(value)[:MAX_TEXT_LEN]
    value = _TAG_RE.sub("", value)           # strip any HTML tags entirely
    value = html.escape(value, quote=True)   # escape whatever special chars remain
    return value.strip()

def sanitize_filename(original: str) -> str:
    base = os.path.basename(original or "upload")
    base = _UNSAFE_FILENAME_CHARS_RE.sub("_", base)
    base = base[:MAX_FILENAME_LEN]
    return base or "upload"