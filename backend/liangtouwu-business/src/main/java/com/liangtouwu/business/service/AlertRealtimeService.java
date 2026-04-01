package com.liangtouwu.business.service;

import com.liangtouwu.business.dto.AlertBroadcastEvent;
import com.liangtouwu.domain.entity.Alert;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class AlertRealtimeService {

    private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    public SseEmitter subscribe() {
        SseEmitter emitter = new SseEmitter(0L);
        emitters.add(emitter);

        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        emitter.onError(error -> emitters.remove(emitter));

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
