from __future__ import annotations

import asyncio

import botpy
from botpy import logging
from botpy.message import C2CMessage, DirectMessage
import httpx

from v1.common.config import get_settings

_log = logging.get_logger()


class BotClient(botpy.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = get_settings()
        self.httpx = httpx.AsyncClient(base_url=self.settings.bot_api_base, timeout=30)

    async def on_ready(self):
        _log.info(f"robot {self.robot.name} on_ready")
        asyncio.create_task(self._outbox_loop())

    async def on_direct_message_create(self, message: DirectMessage):
        _log.info(
            f"dm received: author_id={message.author.id} guild_id={message.guild_id} "
            f"msg_id={message.id} content={message.content!r}"
        )
        await self._handle_and_reply(
            qq_user_id=message.author.id,
            guild_id=message.guild_id,
            message_text=message.content or "",
            reply_func=lambda reply: self.api.post_dms(
                guild_id=message.guild_id,
                content=reply,
                msg_id=message.id,
            ),
        )

    async def on_c2c_message_create(self, message: C2CMessage):
        _log.info(
            f"c2c received: user_openid={message.author.user_openid} msg_id={message.id} "
            f"content={message.content!r}"
        )
        await self._handle_and_reply(
            qq_user_id=message.author.user_openid,
            guild_id=None,
            message_text=message.content or "",
            reply_func=lambda reply: message.reply(content=reply),
        )

    async def _handle_and_reply(self, qq_user_id: str, guild_id, message_text: str, reply_func):
        payload = {
            "qq_user_id": qq_user_id,
            "guild_id": guild_id,
            "message": message_text,
        }
        reply = "system busy"
        try:
            resp = await self.httpx.post("/api/v1/bot/handle", json=payload)
            _log.info(f"handle status={resp.status_code} body={resp.text[:200]}")
            if resp.status_code == 200:
                reply = resp.json().get("reply", reply)
            else:
                reply = f"handle failed: {resp.status_code}"
        except Exception as exc:
            _log.warning("handle error: %r", exc)
            reply = f"handle error: {str(exc)}"

        try:
            await reply_func(reply)
            _log.info("reply sent")
        except Exception as exc:
            _log.warning(f"reply failed: {exc}")

    async def _outbox_loop(self):
        interval = max(3, int(self.settings.bot_outbox_poll_seconds))
        while True:
            try:
                await self._send_pending()
            except Exception as exc:
                _log.warning("outbox loop error: %r", exc)
            await asyncio.sleep(interval)

    async def _send_pending(self):
        resp = await self.httpx.get("/api/v1/bot/outbox/pending", params={"limit": 20})
        if resp.status_code != 200:
            return
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return

        sent_ids = []
        failed_ids = []

        for item in items:
            outbox_id = item.get("id")
            guild_id = item.get("guild_id")
            content = item.get("content")
            if not guild_id:
                failed_ids.append(outbox_id)
                continue
            try:
                await self.api.post_dms(guild_id=guild_id, content=content)
                sent_ids.append(outbox_id)
            except Exception:
                failed_ids.append(outbox_id)

        if sent_ids:
            await self.httpx.post("/api/v1/bot/outbox/mark", json={"ids": sent_ids, "status": "sent"})
        if failed_ids:
            await self.httpx.post(
                "/api/v1/bot/outbox/mark",
                json={"ids": failed_ids, "status": "failed", "error": "send_failed"},
            )


if __name__ == "__main__":
    settings = get_settings()
    intents = botpy.Intents(public_messages=True, direct_message=True)
    client = BotClient(intents=intents)
    client.run(appid=settings.bot_app_id, secret=settings.bot_app_secret)



