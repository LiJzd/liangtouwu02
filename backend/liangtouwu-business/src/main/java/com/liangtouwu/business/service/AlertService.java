package com.liangtouwu.business.service;

import com.liangtouwu.business.dto.AlertBroadcastRequest;
import com.liangtouwu.domain.entity.Alert;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;

public interface AlertService {
    List<Alert> getAlerts(String search, String risk, String area);
    Alert createAndBroadcastAlert(AlertBroadcastRequest request);
    SseEmitter subscribe();
}
