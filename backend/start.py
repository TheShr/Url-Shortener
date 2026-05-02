import os
import sys
from app.core.migrations import run_migrations


def main() -> None:
    run_migrations()

    port = os.environ.get("PORT", "8000")
    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
            "--workers",
            "2",
            "--loop",
            "uvloop",
        ],
    )


if __name__ == "__main__":
    main()
