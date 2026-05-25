package com.liangtouwu.business.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.liangtouwu.common.vo.ApiResponse;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 掌上明猪 AI 异构 Kafka 通信与 SSE 异步推送控制器
 */
@Slf4j
// @RestController
@RequestMapping("/v1/ai/stream")
public class AiKafkaController {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Value("${ai.kafka.tasks-topic:pig-farm-tasks}")
    private String tasksTopic;

    // 静态管理所有活跃的 SSE 会话实例，保障多路复用并发安全
    public static final Map<String, SseEmitter> EMITTER_MAP = new ConcurrentHashMap<>();

    public AiKafkaController(KafkaTemplate<String, String> kafkaTemplate, ObjectMapper objectMapper) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * 前端订阅 SSE 实时的流式消息信道
     */
    @GetMapping(value = "/connect/{clientId}", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter connect(@PathVariable("clientId") String clientId) {
        // 设置超时时间（如 5分钟 ），超时后自动断开
        SseEmitter emitter = new SseEmitter(300_000L);
        EMITTER_MAP.put(clientId, emitter);
        log.info("[SSE] 客户端 {} 成功注册长连接信道。", clientId);

        // 注册回调清理 Map 防止内存溢出
        emitter.onCompletion(() -> {
            log.info("[SSE] 客户端 {} 连接已完成，释放句柄。", clientId);
            EMITTER_MAP.remove(clientId);
        });

        emitter.onTimeout(() -> {
            log.warn("[SSE] 客户端 {} 连接超时，强制释放并移除。", clientId);
            emitter.complete();
            EMITTER_MAP.remove(clientId);
        });

        emitter.onError((ex) -> {
            log.error("[SSE] 客户端 {} 通信通道发生异常: {}，强行断开并注销。", clientId, ex.getMessage());
            emitter.completeWithError(ex);
            EMITTER_MAP.remove(clientId);
        });

        // 建立连接后立刻推送握手消息，防止前端 SSE 因超时未收到数据而自动断开
        try {
            emitter.send(SseEmitter.event()
                    .name("handshake")
                    .data("连接已建立，进入 AI 推理队列中...")
            );
        } catch (IOException e) {
            log.error("[SSE] 推送握手消息异常", e);
            emitter.completeWithError(e);
            EMITTER_MAP.remove(clientId);
        }

        return emitter;
    }

    /**
     * 前端异步发送智能推理请求
     */
    @PostMapping("/send")
    public ApiResponse<String> sendTask(@RequestBody AiTaskRequest request) {
        try {
            if (request.getClientId() == null || request.getClientId().trim().isEmpty()) {
                return ApiResponse.error(400, "clientId 不能为空");
            }
            if (request.getQuery() == null || request.getQuery().trim().isEmpty()) {
                return ApiResponse.error(400, "query 不能为空");
            }

            // 补充基础默认参数
            if (request.getUserId() == null) {
                request.setUserId("demo_user");
            }

            log.info("[Kafka] 接收到大模型异步推理任务发送请求，客户端ID: {}, 任务: {}", request.getClientId(), request.getQuery());

            // 将请求参数 JSON 序列化并推送至 tasks 主题
            String message = objectMapper.writeValueAsString(request);
            kafkaTemplate.send(tasksTopic, request.getClientId(), message);
            
            return ApiResponse.success("任务发送成功，正在入队处理。");
        } catch (Exception e) {
            log.error("[Kafka] 投递大模型异步推理任务异常", e);
            return ApiResponse.error(500, "内部服务异常: " + e.getMessage());
        }
    }

    @Data
    public static class AiTaskRequest {
        private String clientId;
        private String userId;
        private String query;
        private List<Map<String, Object>> messages; // 多轮对话历史
        private Map<String, Object> metadata;      // 剧本元数据等
        private List<String> imageUrls;
        private String audioPath;
    }
}
