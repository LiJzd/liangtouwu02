"""
代理模拟服务 - 系统的“演习场”

专门用来模拟各种突发异常（比如猪发烧、或者猪舍氨气重），
看看 AI 老师傅能不能及时发现，并利索地把告警发到大屏上去。
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional

from v1.logic.multi_agent_core import AgentContext, MultiAgentOrchestrator
from v1.objects.agent_simulation_schemas import (
    SimulatedAlertEvent,
    SimulationIngestResponse,
    SimulationThresholds,
)

logger = logging.getLogger("agent_simulation")


@dataclass
class CacheEntry:
    fingerprint: str
    seen_at: datetime
    route: Optional[str] = None
    analysis: Optional[str] = None
    alert_id: Optional[int] = None


_CACHE: dict[str, CacheEntry] = {}
_CACHE_LOCK = Lock()
_ORCHESTRATOR: Optional[MultiAgentOrchestrator] = None


def get_orchestrator() -> MultiAgentOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = MultiAgentOrchestrator()
    return _ORCHESTRATOR


class AgentSimulationService:

    async def ingest(self, event: SimulatedAlertEvent) -> SimulationIngestResponse:
        """
        这里是处理模拟告警的“加工流水线”。
        
        流程基本是：
        1. 规整：把传进来的数据弄干净。
        2. 初审：看看有没有指标超标了（阈值检查）。
        3. 查重：要是刚才报过同样的，就直接拿缓存（不浪费 AI 算力）。
        4. 研判：要是新鲜事儿，就请 AI 大脑拿个主意。
        5. 补录：万一 AI 忘了发公告，咱还得在这儿给它补上。
        """
        thresholds = event.thresholds or SimulationThresholds()
        normalized = self._normalize_event(event)
        findings = self._evaluate_findings(normalized, thresholds)
        abnormal = bool(findings)
        cache_key = self._build_cache_key(normalized)

        if not abnormal:
            self._update_cache(cache_key, self._build_fingerprint(normalized, findings), None, None, None)
            return SimulationIngestResponse(
                abnormal=False,
                cacheKey=cache_key,
                findings=["No abnormal condition matched the configured thresholds."],
                analysis="Rule cache judged the incoming simulation as normal, so the agent flow was skipped.",
            )

        fingerprint = self._build_fingerprint(normalized, findings)
        duplicate_entry = self._get_duplicate(cache_key, fingerprint, thresholds.duplicate_window_seconds)
        if duplicate_entry is not None:
            return SimulationIngestResponse(
                abnormal=True,
                deduplicated=True,
                cacheKey=cache_key,
                findings=findings,
                route=duplicate_entry.route,
                analysis=duplicate_entry.analysis or "Duplicate abnormal event detected inside the cache window.",
                publishedAlert=duplicate_entry.alert_id is not None,
                publishedAlertId=duplicate_entry.alert_id,
                metadata={"mode": "cache_deduplicated"},
            )

        prompt = self._build_agent_prompt(normalized, findings)
        context = AgentContext(
            user_id="simulation_ingest",
            user_input=prompt,
            chat_history=[],
            metadata={
                "source": "simulation_ingest",
                "cache_key": cache_key,
                "event": normalized,
                "findings": findings,
            },
            client_id=f"simulation_{hashlib.md5(cache_key.encode('utf-8')).hexdigest()[:12]}",
        )

        result = await get_orchestrator().execute(context)
        published_alert, published_alert_id, alert_payload = self._extract_alert_payload(result.tool_outputs or [])
        
        # 如果agent没有调用publish_alert，强制调用它
        if not published_alert:
            logger.warning(f"Agent {result.worker_name} 未调用 publish_alert，强制调用")
            alert_type = self._derive_alert_type(normalized, findings)
            risk = self._derive_risk(normalized, findings)
            announcement = normalized.get("announcement_text") or self._build_announcement(normalized, alert_type, risk)
            
            force_payload = {
                "pigId": normalized.get("pig_id"),
                "area": normalized.get("area"),
                "type": alert_type,
                "risk": risk,
                "timestamp": normalized.get("timestamp"),
                "announcementText": announcement,
            }
            
            # 调用publish_alert工具
            from v1.logic.bot_tools import tool_publish_alert
            try:
                alert_result = await tool_publish_alert(json.dumps(force_payload, ensure_ascii=False))
                alert_data = json.loads(alert_result)
                if alert_data.get("alert_published"):
                    published_alert = True
                    alert_payload = alert_data.get("alert")
                    if isinstance(alert_payload, dict):
                        published_alert_id = alert_payload.get("id")
                    logger.info(f"强制调用 publish_alert 成功，alert_id={published_alert_id}")
            except Exception as e:
                logger.error(f"强制调用 publish_alert 失败: {e}")
        
        self._update_cache(cache_key, fingerprint, result.worker_name, result.answer, published_alert_id)

        return SimulationIngestResponse(
            abnormal=True,
            cacheKey=cache_key,
            findings=findings,
            route=result.worker_name,
            analysis=result.answer,
            publishedAlert=published_alert,
            publishedAlertId=published_alert_id,
            alert=alert_payload,
            metadata=result.metadata,
        )

    def _normalize_event(self, event: SimulatedAlertEvent) -> dict[str, Any]:
        raw = event.model_dump(by_alias=False, exclude_none=True)
        raw.setdefault("pig_id", "UNKNOWN")
        raw.setdefault("area", "unknown-area")
        raw.setdefault("source", "simulated_event")
        raw.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        raw.pop("thresholds", None)
        return raw

    def _evaluate_findings(self, event: dict[str, Any], thresholds: SimulationThresholds) -> list[str]:
        """
        规则审核官。
        
        挨个对对看：猪发烧了没？是不是活力不够？环境氨气超没超？
        只要发现一项异常，就记到小本本（findings）上。
        """
        findings: list[str] = []

        body_temp = event.get("body_temp")
        if body_temp is not None:
            if body_temp >= thresholds.body_temp_high:
                findings.append(f"体温 {body_temp}℃ 超过阈值 {thresholds.body_temp_high}℃。")
            elif body_temp <= thresholds.body_temp_low:
                findings.append(f"体温 {body_temp}℃ 低于阈值 {thresholds.body_temp_low}℃。")

        activity_level = event.get("activity_level")
        if activity_level is not None and activity_level <= thresholds.activity_level_low:
            findings.append(f"活跃度指数 {activity_level} 低于正常水平 {thresholds.activity_level_low}。")

        health_score = event.get("health_score")
        if health_score is not None and health_score >= thresholds.health_score_high:
            findings.append(
                f"健康评分 {health_score} 触发异常预警（阈值 {thresholds.health_score_high}）。"
            )

        temperature_c = event.get("temperature_c")
        if temperature_c is not None:
            if temperature_c >= thresholds.temperature_high:
                findings.append(f"猪舍环境温度 {temperature_c}℃ 超过阈值 {thresholds.temperature_high}℃。")
            elif temperature_c <= thresholds.temperature_low:
                findings.append(f"猪舍环境温度 {temperature_c}℃ 低于阈值 {thresholds.temperature_low}℃。")

        humidity_pct = event.get("humidity_pct")
        if humidity_pct is not None and humidity_pct >= thresholds.humidity_high:
            findings.append(f"湿度 {humidity_pct}% 超过阈值 {thresholds.humidity_high}%。")

        ammonia_ppm = event.get("ammonia_ppm")
        if ammonia_ppm is not None and ammonia_ppm >= thresholds.ammonia_high:
            findings.append(f"氨气浓度 {ammonia_ppm}ppm 超过阈值 {thresholds.ammonia_high}ppm。")

        if not findings and (event.get("type") or event.get("description")):
            findings.append("调用者将此模拟显式标记为异常场景。")

        return findings

    def _build_cache_key(self, event: dict[str, Any]) -> str:
        return "::".join([
            str(event.get("source", "simulated_event")),
            str(event.get("pig_id", "UNKNOWN")),
            str(event.get("area", "unknown-area")),
        ])

    def _build_fingerprint(self, event: dict[str, Any], findings: list[str]) -> str:
        stable_payload = {
            "pig_id": event.get("pig_id"),
            "area": event.get("area"),
            "body_temp": event.get("body_temp"),
            "activity_level": event.get("activity_level"),
            "health_score": event.get("health_score"),
            "temperature_c": event.get("temperature_c"),
            "humidity_pct": event.get("humidity_pct"),
            "ammonia_ppm": event.get("ammonia_ppm"),
            "type": event.get("type"),
            "findings": findings,
        }
        return hashlib.md5(
            json.dumps(stable_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _get_duplicate(
        self,
        cache_key: str,
        fingerprint: str,
        duplicate_window_seconds: int,
    ) -> Optional[CacheEntry]:
        """
        档案查重。
        
        看看是不是短时间内报了两次同样的警。要是还在“冷静期”内，咱就直接翻旧账。
        """
        with _CACHE_LOCK:
            entry = _CACHE.get(cache_key)
            if entry is None:
                return None
            if entry.fingerprint != fingerprint:
                return None
            if datetime.now() - entry.seen_at > timedelta(seconds=duplicate_window_seconds):
                return None
            return entry

    def _update_cache(
        self,
        cache_key: str,
        fingerprint: str,
        route: Optional[str],
        analysis: Optional[str],
        alert_id: Optional[int],
    ) -> None:
        with _CACHE_LOCK:
            _CACHE[cache_key] = CacheEntry(
                fingerprint=fingerprint,
                seen_at=datetime.now(),
                route=route,
                analysis=analysis,
                alert_id=alert_id,
            )

    def _build_agent_prompt(self, event: dict[str, Any], findings: list[str]) -> str:
        """
        给 AI 的“报案说明”。
        
        把咱们发现的问题清清楚楚地告诉 AI，并提醒它一定要发布通告。
        """
        alert_type = self._derive_alert_type(event, findings)
        risk = self._derive_risk(event, findings)
        announcement = event.get("announcement_text") or self._build_announcement(event, alert_type, risk)

        agent_payload = {
            "pigId": event.get("pig_id"),
            "area": event.get("area"),
            "type": alert_type,
            "risk": risk,
            "timestamp": event.get("timestamp"),
            "announcementText": announcement,
        }

        return (
            "系统规则库判定当前模拟事件为异常，需要智能体介入分析。\n"
            "请使用多智能体工作流选择合适的专家（VetAgent），分析异常原因，并决定采取何种措施。\n\n"
            "!! 【强制要求】你必须在分析完成后调用 publish_alert 工具，将告警发布到网页前端大屏并触发语音播报！\n"
            "!! 这是模拟异常事件，必须通知前端用户，不调用 publish_alert 将导致用户无法收到告警通知！\n\n"
            "发布告警所需的 JSON 参数草稿已在下方准备好，请根据分析结果核实后调用。\n\n"
            f"判定结果：\n- " + "\n- ".join(findings) + "\n\n"
            f"模拟事件详情：\n{json.dumps(event, ensure_ascii=False, indent=2)}\n\n"
            f"建议 publish_alert 参数：\n{json.dumps(agent_payload, ensure_ascii=False)}\n\n"
            "你的最终回复应简洁地总结异常原因、严重程度以及建议采取的行动方案。"
        )

    def _derive_alert_type(self, event: dict[str, Any], findings: list[str]) -> str:
        if event.get("type"):
            return str(event["type"])
        text = " ".join(findings)
        if "体温" in text:
            return "体温异常"
        if "活跃度" in text:
            return "活跃度异常"
        if "氨气" in text or "湿度" in text or "环境温度" in text:
            return "环境异常"
        if "健康评分" in text:
            return "健康评分异常"
        return "综合异常"

    def _derive_risk(self, event: dict[str, Any], findings: list[str]) -> str:
        if event.get("risk") in {"Critical", "High", "Medium", "Low"}:
            return str(event["risk"])

        severe_metrics = 0
        if (event.get("body_temp") or 0) >= 41.0:
            severe_metrics += 1
        if (event.get("ammonia_ppm") or 0) >= 35.0:
            severe_metrics += 1
        if (event.get("health_score") or 0) >= 85:
            severe_metrics += 1

        if severe_metrics > 0 or len(findings) >= 3:
            return "Critical"
        if len(findings) >= 2:
            return "High"
        return "Medium"

    def _build_announcement(self, event: dict[str, Any], alert_type: str, risk: str) -> str:
        return (
            f"模拟告警，{event.get('area', 'unknown-area')}区域，猪只{event.get('pig_id', 'UNKNOWN')}出现{alert_type}，"
            f"风险等级{risk}，请立即关注。"
        )

    def _extract_alert_payload(
        self,
        tool_outputs: list[str],
    ) -> tuple[bool, Optional[int], Optional[dict[str, Any]]]:
        for output in tool_outputs:
            try:
                data = json.loads(output)
            except Exception:
                continue
            if not isinstance(data, dict) or not data.get("alert_published"):
                continue

            alert = data.get("alert")
            alert_id: Optional[int] = None
            if isinstance(alert, dict):
                raw_id = alert.get("id")
                try:
                    alert_id = int(raw_id) if raw_id is not None else None
                except Exception:
                    alert_id = None
            return True, alert_id, alert if isinstance(alert, dict) else None
        return False, None, None
