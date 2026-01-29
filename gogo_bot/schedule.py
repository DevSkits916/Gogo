from __future__ import annotations

import logging
import os
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .bot import run_bot

LOGGER = logging.getLogger(__name__)


def run_daemon() -> None:
    tz = os.getenv("TZ", "America/Los_Angeles")
    scheduler = BackgroundScheduler(timezone=tz)
    trigger = CronTrigger(day_of_week="thu", hour=7, minute=0, timezone=tz)
    scheduler.add_job(run_bot, trigger)
    scheduler.start()
    LOGGER.info("Scheduler started. Waiting for jobs.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("Shutting down scheduler.")
        scheduler.shutdown()
