import logging
import os


def configure_logging() -> None:
    level = logging.INFO
    if os.getenv("GOGO_VERBOSE", "0") == "1":
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
