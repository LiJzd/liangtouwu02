package com.liangtouwu.business.service;

import com.liangtouwu.business.dto.AlertBroadcastEvent;
import com.liangtouwu.domain.entity.Alert;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Slf4j
@Service
public class AlertRealtimeService {

    private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    public SseEmitter subscribe() {
        // 设置超时时间为5分钟（300秒），防止频繁断连
        SseEmitter emitter = new SseEmitter(300_000L);
        emitters.add(emitter);
        log.info("New SSE subscription established. Active emitters: {}", emitters.size());

        emitter.onCompletion(() -> {
            emitters.remove(emitter);
            log.info("SSE subscription completed. Active emitters: {}", emitters.size());
        });
        emitter.onTimeout(() -> {
            emitters.remove(emitter);
            log.info("SSE subscription timeout. Active emitters: {}", emitters.size());
            emitter.complete();
        });
        emitter.onError(error -> {
            emitters.remove(emitter);
            log.error("SSE subscription error: {}. Active emitters: {}", error != null ? error.getMessage() : "unknown", emitters.size());
            try {
                emitter.complete();
            } catch (Exception ignored) {
            }
        });

        try {
            emitter.send(SseEmitter.event()
                    .name("connected")
                    .data("alert-stream-ready"));
        } catch (IOException e) {
            emitters.remove(emitter);
            emitter.completeWithError(e);
        }

        return emitter;
    }

    public void publish(Alert alert, String spokenText) {
        log.info("Broadcasting alert to {} emitters: {}", emitters.size(), spokenText);
        AlertBroadcastEvent event = AlertBroadcastEvent.builder()
                .eventId(buildEventId(alert))
                .spokenText(spokenText)
                .alert(alert)
                .build();

        List<SseEmitter> expired = new ArrayList<>();
        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("alert")
                        .id(event.getEventId())
                        .data(event));
            } catch (IOException e) {
                expired.add(emitter);
            }
        }

        expired.forEach(emitter -> {
            emitters.remove(emitter);
            emitter.complete();
        });
    }

    @Scheduled(fixedRate = 25000)
    public void heartbeat() {
        if (emitters.isEmpty()) {
            return;
        }

        List<SseEmitter> expired = new ArrayList<>();
        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("heartbeat")
                        .data(LocalDateTime.now().toString()));
            } catch (IOException e) {
                expired.add(emitter);
            }
        }

        expired.forEach(emitter -> {
            emitters.remove(emitter);
            emitter.complete();
        });
    }

    private String buildEventId(Alert alert) {
        String alertId = alert.getId() == null ? "new" : String.valueOf(alert.getId());
        return alertId + "-" + System.currentTimeMillis();
    }
}
