package com.liangtouwu.business.controller;

import com.liangtouwu.business.dto.AlertBroadcastRequest;
import com.liangtouwu.business.dto.AlertSimulationRequest;
import com.liangtouwu.business.dto.TtsSynthesisRequest;
import com.liangtouwu.business.service.AlertSimulationService;
import com.liangtouwu.business.service.AlertService;
import com.liangtouwu.business.service.XfyunTtsService;
import com.liangtouwu.common.vo.ApiResponse;
import com.liangtouwu.domain.entity.Alert;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/alerts")
public class AlertController {

    private final AlertService alertService;
    private final AlertSimulationService alertSimulationService;
    private final XfyunTtsService xfyunTtsService;

    public AlertController(
            AlertService alertService,
            AlertSimulationService alertSimulationService,
            XfyunTtsService xfyunTtsService) {
        this.alertService = alertService;
        this.alertSimulationService = alertSimulationService;
        this.xfyunTtsService = xfyunTtsService;
    }

    @GetMapping("")
    public ApiResponse<List<Alert>> getAlerts(
            @RequestParam(value = "search", required = false) String search,
            @RequestParam(value = "risk", required = false) String risk,
            @RequestParam(value = "area", required = false) String area
    ) {
        return ApiResponse.success(alertService.getAlerts(search, risk, area));
    }

    @GetMapping(path = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamAlerts() {
        return alertService.subscribe();
    }

    @PostMapping("")
    public ApiResponse<Alert> createAlert(@RequestBody AlertBroadcastRequest request) {
        return ApiResponse.success(alertService.createAndBroadcastAlert(request));
    }

    @PostMapping("/simulate")
    public ApiResponse<Map<String, Object>> simulateAlert(@RequestBody AlertSimulationRequest request) {
        return ApiResponse.success(alertSimulationService.forwardSimulation(request));
    }

    @PostMapping(value = "/tts")
    public ResponseEntity<?> synthesizeSpeech(@RequestBody TtsSynthesisRequest request) {
        try {
            byte[] audio = xfyunTtsService.synthesize(request.getText());
            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType("audio/mpeg"))
                    .body(audio);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(ApiResponse.error(400, e.getMessage()));
        } catch (IllegalStateException e) {
            String msg = e.getMessage();
            if (msg != null && msg.contains("未完成配置")) {
                return ResponseEntity.status(503).body(ApiResponse.error(503, msg));
            }
            return ResponseEntity.status(500).body(ApiResponse.error(500, "语音服务异常: " + msg));
        }
    }
}
