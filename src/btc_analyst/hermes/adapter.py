from __future__ import annotations

from pathlib import Path
import yaml

from btc_analyst.hermes import schedules

CONFIG_PATH = Path(__file__).resolve().parents[3] / 'hermes.config.yaml'


def _load_cfg():
    return yaml.safe_load(CONFIG_PATH.read_text())


def register(hermes_runtime=None):
    cfg = _load_cfg()
    if hermes_runtime:
        for t in cfg.get('tools', []):
            if hasattr(hermes_runtime, 'register_tool'):
                hermes_runtime.register_tool(t['name'], t['handler'])
        for s in cfg.get('schedules', []):
            if hasattr(hermes_runtime, 'register_schedule'):
                hermes_runtime.register_schedule(s['id'], s['cron'], s['handler'])
        for sub in cfg.get('subscribes', []):
            if hasattr(hermes_runtime, 'subscribe'):
                hermes_runtime.subscribe(sub['topic'], sub['handler'])
    return {
        'id': cfg['agent']['id'],
        'display_name': cfg['agent']['display_name'],
        'version': cfg['agent']['version'],
        'capabilities': cfg.get('capabilities', []),
        'config': cfg,
    }


def on_bar_close_4h(event=None):
    return {'ok': True, 'event': '4h_close', 'result': schedules.on_4h_close()}


def on_bar_close_daily(event=None):
    return {'ok': True, 'event': 'daily_close', 'result': schedules.on_daily_close()}


def on_liquidation(event=None):
    return {'ok': True, 'event': 'liquidation'}


def graceful_shutdown(event=None):
    return {'ok': True, 'event': 'shutdown'}


def reload_config(event=None):
    return {'ok': True, 'event': 'reload', 'config_loaded': bool(_load_cfg())}
