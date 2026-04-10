# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger("bot_agent")

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from v1.common.config import get_settings
from v1.objects.bot_models import BotConversation, BotOutbox, BotSubscription, BotUser


_TIME_PATTERN = re.compile(r"(\d{1,2}):(\d{2})")

_EMO_THERMO = "\U0001F321"
_EMO_BOWL = "\U0001F963"
_EMO_PILL = "\U0001F48A"
_EMO_WARN = "\u26A0\uFE0F"

_USER_LOCKS: dict[str, asyncio.Lock] = {}


def _get_user_lock(qq_user_id: str) -> asyncio.Lock:
    lock = _USER_LOCKS.get(qq_user_id)
    if lock is None:
        lock = asyncio.Lock()
        _USER_LOCKS[qq_user_id] = lock
    return lock

_HELP_KEYWORDS = {
    "帮助",
    "菜单",
    "help",
    "你能干啥",
    "你能干什么",
    "你能做什么",
    "你有什么功能",
    "功能",
    "能干啥",
    "能干什么",
    "能做什么",
}

# ─── 智能体角色定义与指令 ───
#
# 该提示词定义了智能体的业务逻辑及响应风格。
# 核心目标是提供专业、高效且易于理解的养殖技术指导。
# 智能体通过 RAG 知识库进行推理，并输出具备执行力的行动方案。
_SYSTEM_PROMPT = (
    "# Role (角色设定)\n"
    "你作为'掌上明猪'智慧农业监测系统的专业智能助手，负责提供畜牧兽医诊断与养殖管理咨询。\n"
    "核心任务是为养殖户提供全天候的技术支持，降低由于巡检真空或经验不足导致的疫病风险。\n\n"
    "# Audience Context (用户画像与语境)\n"
    "1. 用户通常为基层养殖人员，倾向于直接、明确的行动方案。\n"
    "2. 避免使用过于艰深的学术术语，应将技术规范转化为易于执行的操作指令。\n"
    "3. 在面对异常状况时，应提供冷静、专业的指引。\n\n"
    "# System Capabilities (系统能力)\n"
    "1. 计算机视觉感知分析\n"
    "2. IoT 环境参数监控\n"
    "3. 专家知识库 RAG 推理\n\n"
    "# Workflow (执行流程)\n"
    "- 诊断确认：基于输入数据进行初步判断。\n"
    "- 交叉排查：结合环境与健康记录进行多维度分析。\n"
    "- 方案指引：提供明确的处理措施建议。\n\n"
    "# Output Constraints (响应规范)\n"
    "1. 表达严谨简洁，确保语义清晰。\n"
    "2. 针对高风险疫病，必须包含联系畜牧防疫部门的声明。\n"
    "3. 对于非养殖相关的通用咨询，保持客观中立的回复风格。\n"
    "4. 响应长度建议控制在 5 句以内，每句确保核心信息密度。\n"
    "5. 用户问及工具功能时，请先调用 list_tools 工具，再进行功能总结。\n"
    "6. 依据用户具体查询，灵活调用 list_pigs, get_pig_info_by_id, query_pig_growth_prediction 或 capture_pig_farm_snapshot 工具。\n"
    "7. 禁止编造虚假数据或使用夸张的比喻描述。\n"
    "8. 若包含图片信息，应优先基于视觉特征分析并结合专业知识库进行逻辑推理。\n"
)

_SYSTEM_PROMPT_GENERAL = (
    "你是友好、实用的聊天助手。\n"
    "回复简短：1-2句，每句不超过20字。\n"
    "不要自我介绍，不要固定开头，不要长篇大论。\n"
    "用户问'能做什么/功能/工具'，先调用 list_tools，再简短回答。\n"
    "只回答用户最后一句问题，不要回复上一轮的问题。\n"
)


async def ensure_user(session: AsyncSession, qq_user_id: str, guild_id: Optional[str] = None) -> BotUser:
    """
    持久化用户信息。
    完成用户信息登记或历史记录同步。
    """


def _parse_time(text: str) -> Optional[str]:
    match = _TIME_PATTERN.search(text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _help_text() -> str:
    return (
        "可用：订阅简报 HH:MM / 取消订阅 / 工具列表 / 调用 工具名 参数\n"
        "也可以直接说猪的情况。"
    )


def _format_tools() -> str:
    tools = list_tools()
    if not tools:
        return "当前没有可用工具。"
    lines = ["可用工具:"]
    for name, tool in tools.items():
        lines.append(f"- {name}: {tool.description}")
    return "\n".join(lines)


async def _subscribe_brief(session: AsyncSession, qq_user_id: str, time_text: str) -> str:
    result = await session.execute(select(BotSubscription).where(BotSubscription.qq_user_id == qq_user_id))
    sub = result.scalar_one_or_none()
    if sub is None:
        sub = BotSubscription(qq_user_id=qq_user_id, daily_brief_time=time_text, enabled=True)
        session.add(sub)
    else:
        sub.daily_brief_time = time_text
        sub.enabled = True
    await session.commit()
    return f"已订阅每日简报，推送时间 {time_text}。"


async def _cancel_brief(session: AsyncSession, qq_user_id: str) -> str:
    result = await session.execute(select(BotSubscription).where(BotSubscription.qq_user_id == qq_user_id))
    sub = result.scalar_one_or_none()
    if sub is None:
        return "你还没有订阅简报。"
    sub.enabled = False
    await session.commit()
    return "已取消订阅。"


async def _save_turn(session: AsyncSession, qq_user_id: str, role: str, content: str) -> None:
    session.add(BotConversation(qq_user_id=qq_user_id, role=role, content=content))
    await session.commit()


def _build_messages(system_prompt: str, history: list[BotConversation], user_text: str, image_urls: Optional[List[str]] = None) -> list[dict]:
    """
    构建符合大模型输入规范的消息序列。
    
    支持多模态输入，将文本与图像资源 URL 封装为标准对话格式。
    """
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for item in reversed(history):
        messages.append({"role": item.role, "content": item.content})
    
    # 构建用户消息：有图片时使用多模态格式
    if image_urls:
        content_parts = []
        if user_text:
            content_parts.append({"type": "text", "text": user_text})
        else:
            content_parts.append({"type": "text", "text": "请分析这张图片中的猪只状况"})
        for url in image_urls:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": url}
            })
        messages.append({"role": "user", "content": content_parts})
    else:
        messages.append({"role": "user", "content": user_text})
    
    return messages


async def _get_history(session: AsyncSession, qq_user_id: str, limit: int) -> list[BotConversation]:
    result = await session.execute(
        select(BotConversation)
        .where(BotConversation.qq_user_id == qq_user_id)
        .order_by(desc(BotConversation.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


def _fallback_reply(text: str) -> str:
    if _is_danger(text):
        return _reply_danger()
    return "系统繁忙，请再说一遍。"


async def _call_central_agent(qq_user_id: str, messages: list[dict], image_urls: Optional[List[str]] = None) -> tuple[Optional[str], Optional[str]]:
    """
    调用中央智能体协同引擎。
    
    优先请求多智能体协作接口（V2），若请求异常则自动路由至单智能体兜底逻辑。
    """
    settings = get_settings()
    if not settings.central_agent_url:
        return None, None
    
    headers = {"Content-Type": "application/json"}
    if settings.central_agent_api_key:
        headers["Authorization"] = f"Bearer {settings.central_agent_api_key}"
    
    payload = {
        "user_id": qq_user_id,
        "messages": messages,
        "metadata": {"channel": "c2c", "source": "qq_bot"},
    }
    
    # 多模态：传递图片URL给中央智能体
    if image_urls:
        payload["image_urls"] = image_urls
        logger.info(f"携带 {len(image_urls)} 张图片调用中央智能体")
    
    try:
        async with httpx.AsyncClient(timeout=settings.central_agent_timeout_seconds) as client:
            # 优先使用 V2 多智能体接口
            v2_url = settings.central_agent_url.replace("/chat", "/chat/v2")
            try:
                resp = await client.post(v2_url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    reply = data.get("reply")
                    image = data.get("image")
                    reply_text = reply if isinstance(reply, str) and reply.strip() else None
                    return reply_text, image
            except Exception:
                # V2 失败，降级到 V1
                pass
            
            # 降级到 V1 单智能体接口
            resp = await client.post(settings.central_agent_url, json=payload, headers=headers)
        
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        reply = data.get("reply")
        reply_text = reply if isinstance(reply, str) and reply.strip() else None
        return reply_text, None
    except Exception:
        return None, None


def _is_danger(text: str) -> bool:
    keywords = ["非洲猪瘟", "高热", "出血", "紫斑", "抽搐", "快死", "死得快"]
    return any(k in text for k in keywords)


def _is_help_query(text: str) -> bool:
    cleaned = text.strip()
    if cleaned in _HELP_KEYWORDS:
        return True
    return any(keyword in cleaned for keyword in _HELP_KEYWORDS if len(keyword) > 1)


def _is_pig_topic(text: str) -> bool:
    keywords = [
        "猪",
        "养殖",
        "猪场",
        "母猪",
        "仔猪",
        "拉稀",
        "咳嗽",
        "不吃",
        "腹泻",
        "发烧",
        "体温",
        "打架",
        "咬尾",
    ]
    return any(k in text for k in keywords)


def _strip_canned_prefix(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    canned = [
        "掌上明猪",
        "猪BOT",
        "开机成功",
        "数字兽医",
        "养猪的管家",
        "我是来帮您养好猪的",
    ]
    cleaned: list[str] = []
    for idx, line in enumerate(lines):
        if idx < 2 and any(token in line for token in canned):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _shorten_reply(text: str, max_lines: int = 8, max_sentences: int = 6, max_chars: int = 300) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        text = "\n".join(lines[:max_lines])
    if len(text) > max_chars:
        parts = re.split(r"(?<=[\u3002\uff01\uff1f!?])", text)
        compact = ""
        count = 0
        for part in parts:
            part = part.strip()
            if not part:
                continue
            compact += part
            count += 1
            if count >= max_sentences or len(compact) >= max_chars:
                break
        text = compact or text
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def _postprocess_reply(text: str) -> str:
    """
    对智能体响应内容进行后处理。
    
    包括清洗冗余前缀、移除推理逻辑标记（ReAct Tags）及内容长度截断。
    """
    text = (text or "").strip()
    if not text:
        return "我在，想聊什么？"
    
    # 【关键】如果回复中包含 ReAct 格式标记，强制提取 Final Answer
    react_markers = ["Thought:", "Action:", "Observation:", "Question:"]
    if any(marker in text for marker in react_markers):
        import re
        match = re.search(r"Final Answer:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            # 尝试提取非标记行作为回复（而不是直接丢弃）
            logger.warning(f"检测到思考链残留，尝试提取有用内容: {text[:200]}")
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            filtered = [
                line for line in lines
                if not any(marker in line for marker in react_markers)
                and not line.startswith("Action Input:")
            ]
            if filtered:
                # 取最后几行有意义的内容
                text = "\n".join(filtered[-5:])
            else:
                return "系统繁忙，请再说一遍。"
    
    text = _strip_canned_prefix(text)
    text = _shorten_reply(text)
    return text


def _reply_danger() -> str:
    """针对高风险事件的预防性提醒响应。"""


async def _handle_message_locked(
    session: AsyncSession,
    qq_user_id: str,
    message: str,
    guild_id: Optional[str],
    image_urls: Optional[List[str]] = None,
) -> tuple[str, Optional[str]]:
    """
    处理消息（支持多模态图片问诊）
    
    Returns:
        tuple[reply_text, image_base64]: (回复文本, 图片base64)
    """
    await ensure_user(session, qq_user_id=qq_user_id, guild_id=guild_id)
    text = message.strip()

    if not text and not image_urls:
        return "请发送有效内容。", None

    settings = get_settings()
    history = await _get_history(session, qq_user_id, settings.central_agent_max_history)
    
    # 有图片时强制使用养殖系统提示词（图片问诊=兽医场景）
    if image_urls:
        system_prompt = _SYSTEM_PROMPT
        logger.info(f"检测到图片，启用多模态问诊模式")
    else:
        system_prompt = _SYSTEM_PROMPT if _is_pig_topic(text) else _SYSTEM_PROMPT_GENERAL
    
    messages = _build_messages(system_prompt, history, text, image_urls=image_urls)

    reply = None
    image = None
    try:
        reply, image = await asyncio.wait_for(
            _call_central_agent(qq_user_id, messages, image_urls=image_urls),
            timeout=settings.central_agent_timeout_seconds,
        )
    except asyncio.TimeoutError:
        reply = None
        image = None
    if not reply:
        reply = _fallback_reply(text)
    reply = _postprocess_reply(reply)

    # 保存对话记录（图片仅记录文本描述）
    save_text = text if text else "[用户发送了图片]"
    await _save_turn(session, qq_user_id, "user", save_text)
    await _save_turn(session, qq_user_id, "assistant", reply)
    return reply, image


async def handle_message(
    session: AsyncSession, 
    qq_user_id: str, 
    message: str, 
    guild_id: Optional[str] = None,
    image_urls: Optional[List[str]] = None,
) -> tuple[str, Optional[str]]:
    """
    处理消息（带锁，支持多模态）
    
    Returns:
        tuple[reply_text, image_base64]: (回复文本, 图片base64)
    """
    lock = _get_user_lock(qq_user_id)
    async with lock:
        return await _handle_message_locked(session, qq_user_id, message, guild_id, image_urls=image_urls)


async def build_daily_brief(session: AsyncSession, qq_user_id: str) -> str:
    settings = get_settings()
    tz = ZoneInfo(settings.bot_timezone)
    now = datetime.now(tz)
    return (
        "每日简报\n"
        f"日期: {now.strftime('%Y-%m-%d')}\n"
        "环境数据: 尚未接入数据源\n"
        "提示: 如需查询，请先添加对应工具。"
    )


async def enqueue_brief(session: AsyncSession, qq_user_id: str, content: str) -> None:
    outbox = BotOutbox(qq_user_id=qq_user_id, content=content, status="pending")
    session.add(outbox)
    await session.commit()


def is_due(sub: BotSubscription, now_date: date, now_time: str) -> bool:
    if not sub.enabled:
        return False
    if sub.daily_brief_time != now_time:
        return False
    if sub.last_sent_date == now_date:
        return False
    return True


