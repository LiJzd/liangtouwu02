# -*- coding: utf-8 -*-
"""
机器人持久化模型定义

涉及用户信息、简报订阅、待发消息队列及对话历史记录。
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BotUser(Base):
    """
    机器人用户信息。
    记录用户唯一标识（QQ 号）及其归属信息。
    """
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qq_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dms_guild_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BotSubscription(Base):
    """
    简报订阅记录。
    管理用户的订阅状态、推送时间及最后更新记录。
    """
    __tablename__ = "bot_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qq_user_id: Mapped[str] = mapped_column(String(64), index=True)
    daily_brief_time: Mapped[str] = mapped_column(String(5))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BotOutbox(Base):
    """
    待发送消息队列。
    实现消息发送的异步追踪与错误日志记录。
    """
    __tablename__ = "bot_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qq_user_id: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BotConversation(Base):
    """
    对话上下文记录。
    存储用户与智能体之间的多轮交互历史。
    """
    __tablename__ = "bot_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qq_user_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
