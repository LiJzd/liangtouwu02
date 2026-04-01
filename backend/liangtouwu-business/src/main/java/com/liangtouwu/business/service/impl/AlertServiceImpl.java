package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.dto.AlertBroadcastRequest;
import com.liangtouwu.domain.entity.Alert;
import com.liangtouwu.business.mapper.AlertMapper;
import com.liangtouwu.business.service.AlertRealtimeService;
import com.liangtouwu.business.service.AlertService;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
public class AlertServiceImpl implements AlertService {
    private static final DateTimeFormatter TIMESTAMP_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final AlertMapper alertMapper;
    private final AlertRealtimeService alertRealtimeService;

    public AlertServiceImpl(AlertMapper alertMapper, AlertRealtimeService alertRealtimeService) {
        this.alertMapper = alertMapper;
        this.alertRealtimeService = alertRealtimeService;
    }

    @Override
    public List<Alert> getAlerts(String search, String risk, String area) {
        return alertMapper.findByCondition(search, risk, area);
    }

    @Override
    public Alert createAndBroadcastAlert(AlertBroadcastRequest request) {
        Alert alert = Alert.builder()
                .pigId(defaultValue(request.getPigId(), "UNKNOWN"))
                .area(defaultValue(request.getArea(), "未分区"))
                .type(defaultValue(request.getType(), "异常预警"))
                .risk(normalizeRisk(request.getRisk()))
                .timestamp(defaultValue(request.getTimestamp(), LocalDateTime.now().format(TIMESTAMP_FORMATTER)))
                .build();
        
        alert.setMessage(buildAnnouncementText(alert, request.getAnnouncementText()));

        alertMapper.insertAlert(alert);
        alertRealtimeService.publish(alert, buildAnnouncementText(alert, request.getAnnouncementText()));
        return alert;
    }

    @Override
    public SseEmitter subscribe() {
        return alertRealtimeService.subscribe();
    }

    private String buildAnnouncementText(Alert alert, String customAnnouncement) {
        if (StringUtils.hasText(customAnnouncement)) {
            return customAnnouncement.trim();
        }
        return String.format(
                "两头乌告警，猪只%s，区域%s，异常类型%s，风险等级%s，请及时处理。",
                alert.getPigId(),
                alert.getArea(),
                alert.getType(),
                riskLabel(alert.getRisk())
        );
    }

    private String riskLabel(String risk) {
        return switch (normalizeRisk(risk)) {
            case "Critical" -> "紧急";
            case "High" -> "高";
            case "Medium" -> "中";
            default -> "低";
        };
    }

    private String normalizeRisk(String risk) {
        if (!StringUtils.hasText(risk)) {
            return "High";
        }
        return switch (risk.trim()) {
            case "Critical", "High", "Medium", "Low" -> risk.trim();
            default -> "High";
        };
    }

    private String defaultValue(String value, String fallback) {
        return StringUtils.hasText(value) ? value.trim() : fallback;
    }
}
