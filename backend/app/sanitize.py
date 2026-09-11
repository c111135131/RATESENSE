"""Defense-in-depth sanitization for any free-text the participant types.

Right now the only free-text input anywhere in ADAPT is the survey's
"Other: ___" fields (frontend/js/pages/survey.js). Everything else is a
fixed set of radio/checkbox values chosen from a known list, so it can't
carry an XSS payload.

sanitize_text() strips any HTML tags entirely, then HTML-escapes whatever
characters are left, so the stored value is always safe to render later
-- e.g. in the admin panel (frontend/js/admin.js), which builds its tables
with raw innerHTML template strings and would otherwise execute a script
tag hidden inside a submitted answer. Sanitizing at the point of storage
means every future render site is protected automatically, rather than
relying on each one to remember to escape on its own.
"""
import html
import re

_TAG_RE = re.compile(r"<[^>]*>")
MAX_TEXT_LEN = 300


def sanitize_text(value):
    """Returns a safe-to-render version of `value`, or None if value is None."""
    if value is None:
        return None
    value = str(value)[:MAX_TEXT_LEN]
    value = _TAG_RE.sub("", value)           # strip any HTML tags entirely
    value = html.escape(value, quote=True)   # escape whatever special chars remain
    return value.strip()