from __future__ import annotations

import os
from telegram import Bot

_TOOL_CALL_MARKERS = (
    '💻 terminal:',
    '📖 read_file:',
    '🔎 search_files:',
    '⏰ cronjob:',
    '📚 skill_view:',
)


def _escape_md2(text: str) -> str:
    s = str(text)
    for ch in r"_[]()~`>#+-=|{}.!":
        s = s.replace(ch, "\\" + ch)
    return s


def _strip_tool_echoes(text: str) -> str:
    lines = [
        ln for ln in str(text).splitlines()
        if not any(ln.lstrip().startswith(marker) for marker in _TOOL_CALL_MARKERS)
    ]
    return '\n'.join(lines).strip()


async def send_message(text: str, markdown_v2: bool = False) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    bot = Bot(token=token)
    clean_text = _strip_tool_echoes(text)
    body = _escape_md2(clean_text) if markdown_v2 else clean_text
    await bot.send_message(
        chat_id=chat_id,
        text=body,
        parse_mode='MarkdownV2' if markdown_v2 else None,
    )
    return True
