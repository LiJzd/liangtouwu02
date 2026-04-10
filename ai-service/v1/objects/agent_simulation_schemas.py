# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SimulationThresholds(BaseModel):
    """
    仿真异常检测阈值配置。
    包含体温、活跃度、环境温湿度及氨气浓度等告警红线。
    """
    model_config = ConfigDict(populate_by_name=True)

    body_temp_high: float = Field(default=39.5, alias="bodyTempHigh")
    body_temp_low: float = Field(default=37.0, alias="bodyTempLow")
    activity_level_low: int = Field(default=35, alias="activityLevelLow")
    health_score_high: int = Field(default=60, alias="healthScoreHigh")
    temperature_high: float = Field(default=30.0, alias="temperatureHigh")
    temperature_low: float = Field(default=15.0, alias="temperatureLow")
    humidity_high: float = Field(default=80.0, alias="humidityHigh")
    ammonia_high: float = Field(default=20.0, alias="ammoniaHigh")
    duplicate_window_seconds: int = Field(default=120, alias="duplicateWindowSeconds")


class SimulatedAlertEvent(BaseModel):
    """
    异常仿真事件协议。
    描述猪只健康度变化或环境异常触发的仿真告警包。
    """
    model_config = ConfigDict(populate_by_name=True)

    pig_id: Optional[str] = Field(default=None, alias="pigId")
    area: Optional[str] = None
    source: str = "simulated_event"
    timestamp: Optional[str] = None
    body_temp: Optional[float] = Field(default=None, alias="bodyTemp")
    activity_level: Optional[int] = Field(default=None, alias="activityLevel")
    health_score: Optional[int] = Field(default=None, alias="healthScore")
    temperature_c: Optional[float] = Field(default=None, alias="temperatureC")
    humidity_pct: Optional[float] = Field(default=None, alias="humidityPct")
    ammonia_ppm: Optional[float] = Field(default=None, alias="ammoniaPpm")
    type: Optional[str] = None
    description: Optional[str] = None
    risk: Optional[str] = None
    announcement_text: Optional[str] = Field(default=None, alias="announcementText")
    thresholds: Optional[SimulationThresholds] = None


class SimulationIngestResponse(BaseModel):
    """
    仿真数据注入响应协议。
    """
    accepted: bool = True
    abnormal: bool
    deduplicated: bool = False
    cache_key: str = Field(alias="cacheKey")
    findings: List[str] = []
    route: Optional[str] = None
    analysis: Optional[str] = None
    published_alert: bool = Field(default=False, alias="publishedAlert")
    published_alert_id: Optional[int] = Field(default=None, alias="publishedAlertId")
    alert: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
