from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_ERROR

from btc_analyst.config import load_config
from btc_analyst.hermes import schedules
from btc_analyst.hermes import tools as hermes_tools
from btc_analyst.storage.db import get_conn, run_migrations

DB = './data/btc_analyst.db'


async def main():
    conn = get_conn(DB)
    run_migrations(conn)
    cfg = load_config()
    monitoring_cfg = (cfg.get('monitoring', {}) or {})
    monitor_minutes = int(monitoring_cfg.get('interval_minutes', 15))
    crowd_minutes = int(monitoring_cfg.get('crowd_interval_minutes', 5))
    heatmap_minutes = int(monitoring_cfg.get('heatmap_interval_minutes', 15))

    sched = AsyncIOScheduler(timezone='UTC')

    def _job_listener(event):
        if event.exception:
            hermes_tools.record_pipeline_failure(
                component=f"apscheduler:{event.job_id}",
                err=event.exception,
                context={'traceback': str(event.traceback)[:1000] if event.traceback else ''},
            )

    sched.add_listener(_job_listener, EVENT_JOB_ERROR)
    sched.add_job(schedules.heartbeat, 'cron', minute='*/5')
    sched.add_job(schedules.market_monitoring_cycle, 'cron', minute=f'*/{monitor_minutes}')
    sched.add_job(schedules.refresh_crowd_positioning, 'cron', minute=f'*/{crowd_minutes}')
    sched.add_job(schedules.refresh_liq_heatmap_cycle, 'cron', minute=f'*/{heatmap_minutes}')
    sched.add_job(schedules.probability_hourly_1d, 'cron', minute=0)
    sched.add_job(schedules.probability_retrospective_daily, 'cron', hour=0, minute=30)
    sched.add_job(schedules.probability_weekly_recompute, 'cron', day_of_week='sun', hour=0, minute=0)
    sched.add_job(schedules.on_4h_close, 'cron', minute=1, hour='0,4,8,12,16,20')
    sched.add_job(schedules.on_daily_close, 'cron', hour=0, minute=1)
    sched.add_job(schedules.run_daily_report, 'cron', hour=12, minute=0)
    sched.add_job(schedules.run_weekly_review, 'cron', day_of_week='mon', hour=14, minute=0)
    sched.add_job(schedules.cme_close_warning, 'cron', day_of_week='thu', hour=20, minute=0)
    sched.add_job(schedules.cme_open_check, 'cron', day_of_week='sun', hour=22, minute=0)
    sched.add_job(schedules.db_maintenance, 'cron', day_of_week='sun', hour=3, minute=0)
    sched.add_job(schedules.apply_decay, 'cron', hour=2, minute=0)
    sched.start()

    try:
        while True:
            await asyncio.sleep(5)
    finally:
        sched.shutdown(wait=False)


if __name__ == '__main__':
    asyncio.run(main())
