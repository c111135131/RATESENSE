"""A StaticFiles subclass that adds proper Cache-Control headers, so the
same video isn't silently re-fetched from the server every time a new
<video> element requests the exact same URL (which happens on every phase
transition -- see frontend/js/pages/phaseModule.js's runInteractiveTrial,
which rebuilds the whole page via renderInto() and therefore destroys and
recreates the <video> element on every single trial).

Predefined/demo videos never change once uploaded (a new upload gets a
fresh random filename rather than overwriting an existing one -- see
routers/admin.py's upload_media), so they're safe to cache aggressively
with `immutable`: the browser won't even bother asking the server to
revalidate within the cache window, eliminating the network round-trip
entirely on repeat views within the same experiment.

Self-recordings are explicitly EXCLUDED from long-lived caching: they get
deleted after the experiment completes or expires (privacy requirement,
SRS §1), and a long Cache-Control would let a participant's browser keep
serving a "deleted" video from its own disk cache without ever checking
back with the server.
"""
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

# 7 days -- long enough to eliminate re-fetches for the whole duration of
# one experiment session, short enough that a mistaken re-upload of the
# "same" filename (shouldn't happen, since uploads get random prefixes,
# but just in case) doesn't stay stale forever.
PREDEFINED_VIDEO_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


class CachedMediaFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)

        is_self_recording = path.replace("\\", "/").startswith("recordings/")
        if is_self_recording:
            # Never cache -- these can be deleted server-side at any time.
            response.headers["Cache-Control"] = "no-store"
        else:
            response.headers["Cache-Control"] = (
                f"public, max-age={PREDEFINED_VIDEO_MAX_AGE_SECONDS}, immutable"
            )

        return response