from __future__ import annotations

import os
from telegram import Bot


def _escape_md2(text: str) -> str:
    s = str(text)
    for ch in r"_[]()~`>#+-=|{}.!":
        s = s.replace(ch, "\\" + ch)
    return s


async def send_message(text: str, markdown_v2: bool = False) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    bot = Bot(token=token)
    body = _escape_md2(text) if markdown_v2 else text
    await bot.send_message(
        chat_id=chat_id,
        text=body,
        parse_mode='MarkdownV2' if markdown_v2 else None,
    )
    return True
