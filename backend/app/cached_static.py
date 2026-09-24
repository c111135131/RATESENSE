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