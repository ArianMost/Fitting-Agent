# """
# langfuse_client.py — thin wrapper around the Langfuse SDK.

# If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set the client falls
# back to a no-op stub so the rest of the app keeps working without tracing.
# """

# import os
# from typing import Any

# _enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))

# if _enabled:
#     from langfuse import Langfuse  # type: ignore

#     _client = Langfuse(
#         public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
#         secret_key=os.environ["LANGFUSE_SECRET_KEY"],
#         host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
#     )
# else:
#     _client = None  # type: ignore


# # ── Public helpers ────────────────────────────────────────────────────────────

# def trace(name: str, input: Any, output: Any, metadata: dict | None = None) -> None:
#     """Create a Langfuse trace. No-ops silently if Langfuse is not configured."""
#     if _client is None:
#         return
#     t = _client.trace(name=name, input=input, output=output, metadata=metadata or {})
#     t.flush()


# def score(trace_id: str, name: str, value: float, comment: str = "") -> None:
#     """Attach a numeric score to an existing trace."""
#     if _client is None:
#         return
#     _client.score(trace_id=trace_id, name=name, value=value, comment=comment)
#     _client.flush()


# def is_enabled() -> bool:
#     return _enabled


from langfuse import get_client
from loguru import logger
from typing import Any, Optional


class LangfuseClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            client = get_client()

            if client and client.auth_check():
                logger.info("Langfuse client is authenticated and ready!")
                cls._instance = client
            else:
                logger.warning("Langfuse disabled (no valid credentials)")
                cls._instance = None

        return cls._instance


# Singleton instance
langfuse_client = LangfuseClient()


# ── Helper functions (clean API) ─────────────────────────

def create_trace(name: str, input: Any, metadata: dict | None = None) -> Optional[str]:
    if langfuse_client is None:
        return None

    trace = langfuse_client.trace(
        name=name,
        input=input,
        metadata=metadata or {},
    )
    return trace.id


def update_trace(trace_id: str, output: Any) -> None:
    if langfuse_client is None or trace_id is None:
        return

    langfuse_client.trace(
        id=trace_id,
        output=output,
    )
    langfuse_client.flush()


def log_event(
    trace_id: str,
    name: str,
    input: Any = None,
    output: Any = None,
) -> None:
    if langfuse_client is None or trace_id is None:
        return

    langfuse_client.event(
        trace_id=trace_id,
        name=name,
        input=input,
        output=output,
    )


def score(trace_id: str, name: str, value: float, comment: str = "") -> None:
    if langfuse_client is None or trace_id is None:
        return

    langfuse_client.score(
        trace_id=trace_id,
        name=name,
        value=value,
        comment=comment,
    )
    langfuse_client.flush()