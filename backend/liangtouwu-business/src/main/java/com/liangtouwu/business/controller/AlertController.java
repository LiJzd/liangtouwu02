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
            // 验证请求
            if (request == null || request.getText() == null || request.getText().trim().isEmpty()) {
                return ResponseEntity.badRequest()
                        .body(ApiResponse.error(400, "播报文本不能为空"));
            }
            
            // 调用TTS服务
            byte[] audio = xfyunTtsService.synthesize(request.getText());
            
            // 验证返回数据
            if (audio == null || audio.length == 0) {
                return ResponseEntity.status(500)
                        .body(ApiResponse.error(500, "语音合成失败：返回数据为空"));
            }
            
            // 返回音频数据
            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType("audio/mpeg"))
                    .header("Content-Length", String.valueOf(audio.length))
                    .body(audio);
                    
        } catch (IllegalArgumentException e) {
            // 参数错误（如文本为空）
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error(400, e.getMessage()));
                    
        } catch (IllegalStateException e) {
            // 配置错误或服务不可用
            String msg = e.getMessage();
            if (msg != null && msg.contains("未完成配置")) {
                return ResponseEntity.status(503)
                        .body(ApiResponse.error(503, msg));
            }
            // 其他状态错误（如讯飞API调用失败）
            return ResponseEntity.status(500)
                    .body(ApiResponse.error(500, "语音服务异常: " + msg));
                    
        } catch (Exception e) {
            // 未知错误
            e.printStackTrace(); // 打印完整堆栈到控制台
            return ResponseEntity.status(500)
                    .body(ApiResponse.error(500, "语音服务内部错误: " + e.getMessage()));
        }
    }

    /**
     * TTS配置测试端点
     * 用于诊断讯飞TTS配置问题
     */
    @GetMapping("/tts/test")
    public ApiResponse<Map<String, Object>> testTtsConfig() {
        try {
            // 测试简单文本合成
            String testText = "测试";
            byte[] audio = xfyunTtsService.synthesize(testText);
            
            return ApiResponse.success(Map.of(
                "status", "success",
                "message", "TTS配置正常，语音合成成功",
                "audioSize", audio.length,
                "testText", testText
            ));
        } catch (Exception e) {
            return ApiResponse.error(500, "TTS测试失败: " + e.getMessage());
        }
    }
}
