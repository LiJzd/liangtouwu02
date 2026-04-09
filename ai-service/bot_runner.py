from __future__ import annotations

import asyncio
import os

import botpy
from botpy import logging
from botpy.message import C2CMessage, DirectMessage
import httpx

from v1.common.config import get_settings

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

_log = logging.get_logger()


class BotClient(botpy.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = get_settings()
        self.httpx = httpx.AsyncClient(base_url=self.settings.bot_api_base, timeout=90)

    async def on_ready(self):
        _log.info(f"机器人 {self.robot.name} 成功上线！")
        # 顺便把后台发信循环也跑起来
        asyncio.create_task(self._outbox_loop())

    async def on_direct_message_create(self, message: DirectMessage):
        _log.info(
            f"dm received: author_id={message.author.id} guild_id={message.guild_id} "
            f"msg_id={message.id} content={message.content!r}"
        )
        
        async def reply_func(reply_text, image_path=None):
            # DM 暂不支持图片，只发送文本
            await self.api.post_dms(
                guild_id=message.guild_id,
                content=reply_text,
                msg_id=message.id,
            )
        
        await self._handle_and_reply(
            qq_user_id=message.author.id,
            guild_id=message.guild_id,
            message_text=message.content or "",
            reply_func=reply_func,
        )

        # 看看消息里有没有图片或者语音（得支持老乡发图问诊和发语音啊）
        image_urls = []
        voice_urls = []
        if hasattr(message, 'attachments') and message.attachments:
            for att in message.attachments:
                url = getattr(att, 'url', None)
                content_type = str(getattr(att, 'content_type', '')).lower()
                if not url:
                    continue
                # 确保 URL 是 https 的，不然有些地方加载不出来
                if not url.startswith('http'):
                    url = 'https://' + url
                
                if 'image' in content_type or url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                    image_urls.append(url)
                    _log.info(f"抓到一张图片: {url}")
                elif 'voice' in content_type or 'audio' in content_type or url.lower().endswith(('.silk', '.amr', '.wav', '.mp3', '.ogg')):
                    voice_urls.append(url)
                    _log.info(f"抓到一段语音: {url}")
        
        # 语音转文字：老乡发语音咱们也得听懂，先转成字儿再说
        message_text = message.content or ""
        if voice_urls:
            _log.info(f"发现 {len(voice_urls)} 条语音，后台正在转写...")
            try:
                from v1.logic.voice_to_text import voice_to_text
                for voice_url in voice_urls:
                    transcribed = await voice_to_text(voice_url)
                    if transcribed:
                        _log.info(f"转写成功: {transcribed[:100]}")
                        # 把转出来的字儿跟原本的文字拼在一起
                        if message_text:
                            message_text = f"{message_text} {transcribed}"
                        else:
                            message_text = transcribed
                    else:
                        _log.warning(f"这块语音没转出来: {voice_url[:80]}")
                        if not message_text:
                            message_text = "[语音转写失败了，老乡要不您打字试试？]"
            except Exception as e:
                _log.error(f"语音转写出差错啦: {e}", exc_info=True)
                if not message_text:
                    message_text = "[语音处理出故障了，请麻烦打字描述下]"
        
        _log.info(
            f"c2c received: user_openid={message.author.user_openid} msg_id={message.id} "
            f"content={message_text[:100]!r} image_count={len(image_urls)} voice_count={len(voice_urls)}"
        )
        
        async def reply_func(reply_text, image_path=None):
            if image_path:
                # 给机器人发图比较麻烦，得先传到图床拿个 URL
                try:
                    import base64
                    import httpx
                    import uuid
                    import shutil
                    
                    # 先把图读出来
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    
                    file_url = None
                    
                    # 办法一：用那个挺稳的免费图床
                    try:
                        _log.info("尝试往 img.scdn.io 传图...")
                        async with httpx.AsyncClient(timeout=30) as client:
                            files = {'image': ('image.jpg', image_data, 'image/jpeg')}
                            data = {
                                'outputFormat': 'jpeg',
                                'cdn_domain': 'cloudflareimg.cdn.sn'
                            }
                            response = await client.post(
                                "https://img.scdn.io/api/v1.php",
                                files=files,
                                data=data
                            )
                            response.raise_for_status()
                            result = response.json()
                            
                            if result.get("success"):
                                file_url = result.get("url")
                                _log.info(f"传上去了，地址是: {file_url}")
                            else:
                                _log.warning(f"img.scdn.io 没传成: {result.get('message', '未知错误')}")
                    except Exception as e:
                        _log.warning(f"img.scdn.io 传图报错: {e}")
                    
                    # 办法二：如果图床不行，看看能不能用咱们自己的静态文件路径
                    if not file_url:
                        public_url = os.getenv("PUBLIC_URL", "")
                        if public_url:
                            try:
                                _log.info("试试自家的静态文件服务...")
                                file_id = str(uuid.uuid4())
                                file_ext = os.path.splitext(image_path)[1]
                                static_filename = f"{file_id}{file_ext}"
                                static_temp_dir = os.path.join(os.path.dirname(__file__), "static", "temp")
                                os.makedirs(static_temp_dir, exist_ok=True)
                                static_path = os.path.join(static_temp_dir, static_filename)
                                shutil.copy2(image_path, static_path)
                                file_url = f"{public_url}/static/temp/{static_filename}"
                                
                                # 定个闹钟，一分钟后把临时文件删了，省得占地方
                                async def cleanup():
                                    await asyncio.sleep(60)
                                    try:
                                        os.unlink(static_path)
                                        _log.info(f"临时图删掉啦: {static_path}")
                                    except Exception:
                                        pass
                                asyncio.create_task(cleanup())
                            except Exception as e:
                                _log.warning(f"静态文件服务也白瞎了: {e}")
                    
                    # 如果还是没拿到 URL，只能报错了
                    if not file_url:
                        _log.error("实在没招了，图片传不上去，请检查 PUBLIC_URL 配置")
                        raise ValueError("图片上传全失败了")
                    
                    # 图片 URL 拿到了，让 QQ 机器人发出去
                    try:
                        _log.info("让 QQ 直接把图甩过去...")
                        await self.api.post_c2c_file(
                            openid=message.author.user_openid,
                            file_type=1,
                            url=file_url,
                            srv_send_msg=True
                        )
                        # 歇口气再发文字，体验更好
                        await asyncio.sleep(0.5)
                        await message.reply(content=reply_text)
                    except Exception as e:
                        _log.warning(f"直接发图失败了，降级发链接吧: {e}")
                        enhanced_reply = f"{reply_text}\n\n📷 监控画面在这儿看：{file_url}"
                        await message.reply(content=enhanced_reply)
                    
                except Exception as e:
                    _log.error(f"发图彻底失败: {e}")
                    await message.reply(content=reply_text)
            else:
                # 没图就直接发文字
                await message.reply(content=reply_text)
        
        await self._handle_and_reply(
            qq_user_id=message.author.user_openid,
            guild_id=None,
            message_text=message_text,
            reply_func=reply_func,
            image_urls=image_urls if image_urls else None,
        )

    async def _handle_and_reply(self, qq_user_id: str, guild_id, message_text: str, reply_func, image_urls=None):
        payload = {
            "qq_user_id": qq_user_id,
            "guild_id": guild_id,
            "message": message_text,
        }
        if image_urls:
            payload["image_urls"] = image_urls
            _log.info(f"携带 {len(image_urls)} 张图片发送到后端处理")
        reply = "system busy"
        image_base64 = None
        try:
            resp = await self.httpx.post("/api/v1/bot/handle", json=payload)
            _log.info(f"handle status={resp.status_code} body={resp.text[:200]}")
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("reply", reply)
                image_base64 = data.get("image")
            else:
                reply = f"handle failed: {resp.status_code}"
        except Exception as exc:
            _log.warning("handle error: %r", exc)
            reply = f"handle error: {str(exc)}"

        try:
            # 如果有图片，先发送图片
            if image_base64:
                # 将 base64 图片保存为临时文件
                import base64
                import tempfile
                
                # 移除 data:image/jpeg;base64, 前缀
                if "base64," in image_base64:
                    image_base64 = image_base64.split("base64,")[1]
                
                image_data = base64.b64decode(image_base64)
                
                # 保存到临时文件（不立即删除）
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(image_data)
                    tmp_path = tmp_file.name
                
                _log.info(f"图片已保存到临时文件: {tmp_path}, 大小: {len(image_data)} 字节")
                
                try:
                    # QQ 机器人发送图片需要使用文件路径
                    await reply_func(reply, image_path=tmp_path)
                    _log.info("reply with image sent")
                except Exception as e:
                    _log.error(f"发送图片失败: {e}", exc_info=True)
                finally:
                    # 延迟删除临时文件（确保发送完成）
                    await asyncio.sleep(1)
                    try:
                        os.unlink(tmp_path)
                        _log.info(f"临时文件已删除: {tmp_path}")
                    except Exception as e:
                        _log.warning(f"删除临时文件失败: {e}")
            else:
                # 只发送文本
                await reply_func(reply)
                _log.info("reply sent")
        except Exception as exc:
            _log.warning(f"reply failed: {exc}")

    async def _outbox_loop(self):
        """后台发信小助手：每隔几秒看看有没有还没发出去的消息。"""
        interval = max(3, int(self.settings.bot_outbox_poll_seconds))
        while True:
            try:
                await self._send_pending()
            except Exception as exc:
                _log.warning("发信小助手出差错啦: %r", exc)
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
