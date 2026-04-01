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
        _log.info(f"robot {self.robot.name} on_ready")
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

    async def on_c2c_message_create(self, message: C2CMessage):
        # 提取用户发送的图片和语音附件（多模态问诊支持）
        image_urls = []
        voice_urls = []
        if hasattr(message, 'attachments') and message.attachments:
            for att in message.attachments:
                url = getattr(att, 'url', None)
                content_type = str(getattr(att, 'content_type', '')).lower()
                if not url:
                    continue
                # 确保URL以https开头
                if not url.startswith('http'):
                    url = 'https://' + url
                
                if 'image' in content_type or url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                    image_urls.append(url)
                    _log.info(f"提取到图片附件: {url}")
                elif 'voice' in content_type or 'audio' in content_type or url.lower().endswith(('.silk', '.amr', '.wav', '.mp3', '.ogg')):
                    voice_urls.append(url)
                    _log.info(f"提取到语音附件: {url}")
        
        # 语音转文字：将语音内容转写后拼接到消息文本
        message_text = message.content or ""
        if voice_urls:
            _log.info(f"检测到 {len(voice_urls)} 条语音消息，开始转写...")
            try:
                from v1.logic.voice_to_text import voice_to_text
                for voice_url in voice_urls:
                    transcribed = await voice_to_text(voice_url)
                    if transcribed:
                        _log.info(f"语音转写成功: {transcribed[:100]}")
                        # 将语音转写结果拼接到消息文本
                        if message_text:
                            message_text = f"{message_text} {transcribed}"
                        else:
                            message_text = transcribed
                    else:
                        _log.warning(f"语音转写失败: {voice_url[:80]}")
                        if not message_text:
                            message_text = "[语音消息转写失败，请重新发送或用文字描述]"
            except Exception as e:
                _log.error(f"语音转写异常: {e}", exc_info=True)
                if not message_text:
                    message_text = "[语音消息处理失败，请用文字重新描述]"
        
        _log.info(
            f"c2c received: user_openid={message.author.user_openid} msg_id={message.id} "
            f"content={message_text[:100]!r} image_count={len(image_urls)} voice_count={len(voice_urls)}"
        )
        
        async def reply_func(reply_text, image_path=None):
            if image_path:
                # C2C 支持图片，需要先上传图片获取 Media 对象
                try:
                    import base64
                    import httpx
                    import uuid
                    import shutil
                    
                    # 读取图片文件
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    
                    file_url = None
                    
                    # 方案1: 使用 img.scdn.io 图床（国内，无需 API key，稳定可靠）
                    try:
                        _log.info("尝试使用 img.scdn.io 图床上传图片...")
                        async with httpx.AsyncClient(timeout=30) as client:
                            files = {'image': ('image.jpg', image_data, 'image/jpeg')}
                            # 尝试使用最快的 CDN 域名
                            data = {
                                'outputFormat': 'jpeg',  # 使用 jpeg 格式，兼容性更好
                                'cdn_domain': 'cloudflareimg.cdn.sn'  # 使用 CloudFlare CDN，速度更快
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
                                _log.info(f"图片已上传到 img.scdn.io，URL: {file_url}")
                                if result.get("message"):
                                    _log.info(f"上传信息: {result['message']}")
                            else:
                                _log.warning(f"img.scdn.io 上传失败: {result.get('message', '未知错误')}")
                    except Exception as e:
                        _log.warning(f"img.scdn.io 上传失败: {e}")
                    
                    # 方案2: 使用本地静态文件服务（如果配置了 PUBLIC_URL）
                    if not file_url:
                        public_url = os.getenv("PUBLIC_URL", "")
                        if public_url:
                            try:
                                _log.info("使用本地静态文件服务...")
                                
                                # 将文件复制到 static/temp 目录
                                file_id = str(uuid.uuid4())
                                file_ext = os.path.splitext(image_path)[1]
                                static_filename = f"{file_id}{file_ext}"
                                
                                # 获取 static/temp 目录路径
                                static_temp_dir = os.path.join(os.path.dirname(__file__), "static", "temp")
                                os.makedirs(static_temp_dir, exist_ok=True)
                                
                                static_path = os.path.join(static_temp_dir, static_filename)
                                shutil.copy2(image_path, static_path)
                                
                                file_url = f"{public_url}/static/temp/{static_filename}"
                                _log.info(f"图片已复制到静态目录，URL: {file_url}")
                                
                                # 设置延迟清理任务
                                async def cleanup():
                                    await asyncio.sleep(60)  # 60秒后删除
                                    try:
                                        os.unlink(static_path)
                                        _log.info(f"临时静态文件已删除: {static_path}")
                                    except Exception as e:
                                        _log.warning(f"删除临时静态文件失败: {e}")
                                
                                asyncio.create_task(cleanup())
                                
                            except Exception as e:
                                _log.warning(f"本地静态文件服务失败: {e}")
                                file_url = None
                    
                    # 方案3: 使用 ImgBB（如果配置了有效的 API key）
                    if not file_url:
                        imgbb_api_key = os.getenv("IMGBB_API_KEY", "")
                        if imgbb_api_key and imgbb_api_key != "d0e8e0b3b9c6c4e8f3b9c6c4e8f3b9c6":
                            try:
                                _log.info("尝试使用 ImgBB 图床上传图片...")
                                image_base64 = base64.b64encode(image_data).decode('utf-8')
                                async with httpx.AsyncClient(timeout=30) as client:
                                    response = await client.post(
                                        "https://api.imgbb.com/1/upload",
                                        data={
                                            "key": imgbb_api_key,
                                            "image": image_base64,
                                        }
                                    )
                                    response.raise_for_status()
                                    result = response.json()
                                    
                                    if result.get("success"):
                                        file_url = result["data"]["url"]
                                        _log.info(f"图片已上传到 ImgBB，URL: {file_url}")
                                    else:
                                        _log.warning(f"ImgBB 上传失败: {result}")
                            except Exception as e:
                                _log.warning(f"ImgBB 上传失败: {e}")
                    
                    # 如果所有方案都失败，提示配置说明
                    if not file_url:
                        _log.error("所有图片上传方案均失败，请参考 docs/QQ_BOT_IMAGE_SETUP.md 配置图片发送功能")
                        raise ValueError("图片上传失败，请配置 PUBLIC_URL 或有效的图床 API Key")
                    
                    # 尝试方案1: 使用 srv_send_msg=True 让 QQ 直接发送图片
                    try:
                        _log.info("尝试使用 srv_send_msg=True 直接发送图片...")
                        await self.api.post_c2c_file(
                            openid=message.author.user_openid,
                            file_type=1,  # 1=图片
                            url=file_url,
                            srv_send_msg=True  # 让 QQ 服务器直接发送
                        )
                        _log.info(f"图片已通过 QQ 服务器发送")
                        
                        # 等待一下再发送文本
                        await asyncio.sleep(0.5)
                        await message.reply(content=reply_text)
                        _log.info(f"文本消息已发送")
                        
                    except Exception as e:
                        _log.warning(f"srv_send_msg 方式失败: {e}")
                        
                        # 降级方案：发送图片链接
                        enhanced_reply = f"{reply_text}\n\n📷 查看猪场监控图片：{file_url}"
                        await message.reply(content=enhanced_reply)
                        _log.info(f"已发送图片链接作为备用方案")
                    
                except Exception as e:
                    _log.error(f"发送图片失败: {e}", exc_info=True)
                    _log.warning(f"仅发送文本消息（图片发送失败）")
                    await message.reply(content=reply_text)
            else:
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
