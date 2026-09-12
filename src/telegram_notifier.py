# -*- coding: utf-8 -*-
"""텔레그램 봇 API로 알림 메시지를 보낸다."""
import os
import requests


class TelegramNotifier:
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        """메시지 전송. 실패해도 예외를 던지지 않고 False를 반환한다
        (알림 실패가 프로그램 전체를 멈추면 안 되므로)."""
        if not self.is_configured():
            return False
        url = "https://api.telegram.org/bot{}/sendMessage".format(self.token)
        try:
            resp = requests.post(
                url, data={"chat_id": self.chat_id, "text": text}, timeout=10
            )
            return resp.ok
        except requests.RequestException:
            return False
