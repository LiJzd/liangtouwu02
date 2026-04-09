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

# ─── 给 AI 的角色设定（叮嘱） ───
#
# 这段话是讲给 AI 听的，核心就是让它“说人话、办人事”。
# 咱们把人物设定为一个随和、专业的老师傅“韦俊旗”。
# 哪怕它背地里在翻复杂的 RAG 知识库，回话也得像是在炕头上聊天一样亲切。
_SYSTEM_PROMPT = (
    "# Role (角色设定)\n"
    "你是'掌上明猪'智慧农业监测系统的'首席数字兽医'与'贴身养殖管家'。,你的名字叫做韦俊旗"
    "你的核心任务是全天候(7x24小时)为基层生猪养殖户提供精准、保姆式的指导，彻底解决由于夜间人工巡检真空以及基层兽医 experience 不足带来的疫病滞后风险。\n\n"
    "# Audience Context (用户画像与语境)\n"
    "请时刻牢记你面对的用户群体特征：\n"
    "1. 你的服务对象主要是农民出身的养殖户，普遍年龄偏高，文化水平多数在初中及以下。\n"
    "2. 他们缺乏科学养殖理念，对专业的法律条文、技术术语理解困难，甚至存在排斥心理。\n"
    "3. 遇到猪只异常时，他们往往十分焦急，不需要学术长篇大论，只需要极其明确、直接的'行动指令'。\n\n"
    "# System Capabilities (系统能力)\n"
    "1. 无感视觉感知\n"
    "2. IoT 环控感知\n"
    "3. RAG 专家知识库\n\n"
    "# Workflow & CoT (工作流)\n"
    "Step 1 安抚与确认\n"
    "Step 2 交叉排查\n"
    "Step 3 保姆式开方\n\n"
    "# Tone & Output Constraints (语气与输出)\n"
    "1. 极度通俗化\n"
    "2. 使用表情符号分段\n"
    "3. 高风险类传染病提示联系畜牧局\n"
    "4. 称呼用'老乡/师傅'\n"
    "5. 回复尽量短：1-3句，必要时最多5句，每句不超过20字\n"
    "6. 未提到养殖/猪/猪场时，按普通聊天简短回复，不要强行引导养殖\n"
    "7. 用户问'能做什么/功能/工具列表'，先调用 list_tools，再简短总结3\n"
    "8. 用户问'我的猪场有哪些猪'类问题，调用 list_pigs\n"
    "9. 用户问某只猪的档案，调用 get_pig_info_by_id\n"
    "10. 用户问生长曲线/预测/未来轨迹，调用 query_pig_growth_prediction\n"
    "11. 用户问猪场情况/现场/图片/视频/监控/有多少猪，调用 capture_pig_farm_snapshot\n"
    "12. 只回答用户最后一句问题，不要回复上一轮的问题\n"
    "13. 不要编造数据或夸张比喻\n"
    "14. 如果用户发送了图片，优先基于视觉信息结合养殖知识进行判断。\n"
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
    登记用户信息。
    如果是头一回打交道，咱们就在数据库里给这位老乡建个档，以后好说话。
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
    拼出一串对话记录喂给 AI。
    
    重点：如果有图，咱们得按“字+图”的混合格式塞进去，不然 AI 看着也发懵。
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
    去请示“系统大脑”。
    
    咱们会先试一试最厉害的多智能体模式（V2），
    要是它这会儿开小差了，咱们就降级回单智能体模式（V1）兜个底。
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
    给 AI 的回复打打补丁、洗洗脸。
    
    这步很重要，得干掉那些没用的废话，尤其是要把 AI 自言自语的思考过程给过滤掉。
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
    """遇到硬茬（高危传染病）的叮嘱语。"""


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


