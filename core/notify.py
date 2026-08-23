"""Discord 웹훅으로 알림 메시지를 전송한다."""
from __future__ import annotations

import requests

from core.config import DISCORD_WEBHOOK_URL


class NotifyError(RuntimeError):
    pass


def send_discord_message(content: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        raise NotifyError("DISCORD_WEBHOOK_URL이 설정되지 않았습니다. .env를 확인하세요.")
    response = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=30)
    if response.status_code not in (200, 204):
        raise NotifyError(f"Discord 전송 실패 ({response.status_code}): {response.text[:500]}")
