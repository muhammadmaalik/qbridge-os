"""
Run the FastAPI app from any working directory.

Uvicorn must resolve the ``backend`` package; that only works when the
``qbridge_project`` root (parent of ``backend/``) is on ``sys.path`` and is
the process cwd. This launcher sets both so ``python run_api.py`` works
whether you invoke it from ``qbridge_project``, ``frontend``, or elsewhere.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    os.chdir(_ROOT)
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)

    # Local launcher: allow POST /api/v1/compute/* without PQC session headers.
    # Set QBRIDGE_SKIP_PQC_VERIFY=0 to require X-QBridge-Session / X-QBridge-Signature.
    os.environ.setdefault("QBRIDGE_SKIP_PQC_VERIFY", "1")

    import logging
    import logging.config

    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    from backend.main import _UvicornReadyLogHandler

    logging.config.dictConfig(LOGGING_CONFIG)
    _ready = _UvicornReadyLogHandler()
    _ready.setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").addHandler(_ready)

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        log_config=None,
        timeout_keep_alive=120,
    )


if __name__ == "__main__":
    main()
