package com.liangtouwu.business.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.liangtouwu.business.controller.AiKafkaController;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;

/**
 * 掌上明猪 AI 异步结果 Kafka 监听器
 *
 * 监听 pig-farm-results 主题，接收 AI 推理服务返回的最终报告与图表。
 * 通过 SSE 推流至对应前端 client 会话，并做优雅容错退出。
 */
@Slf4j
// @Service
public class AiKafkaListener {

    private final ObjectMapper objectMapper;

    public AiKafkaListener(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @KafkaListener(
            topics = "${ai.kafka.results-topic:pig-farm-results}",
            groupId = "${spring.kafka.consumer.group-id:pig-farm-ai-group}"
    )
    public void listenAiResult(String message) {
        log.info("[KafkaListener] 收到 AI 推理返回结果消息，开始广播推送。");
        try {
            JsonNode root = objectMapper.readTree(message);
            String clientId = root.path("client_id").asText("");
            if (clientId.isEmpty()) {
                log.error("[KafkaListener] 消息缺少 client_id，拒绝投递，内容: {}", message);
                return;
            }

            SseEmitter emitter = AiKafkaController.EMITTER_MAP.get(clientId);
            if (emitter == null) {
                log.warn("[KafkaListener] 对应客户端 {} 的 SSE 句柄不存在或已超时释放，放弃推送结果。", clientId);
                return;
            }

            log.info("[KafkaListener] 正在将 AI 回复推送至客户端 {}...", clientId);

            String status = root.path("status").asText("success");
            
            if ("error".equals(status)) {
                String errorMsg = root.path("reply").asText("推理任务发生未知错误");
                try {
                    emitter.send(SseEmitter.event()
                            .name("error")
                            .data(errorMsg)
                    );
                    emitter.complete();
                } catch (IOException e) {
                    log.error("[KafkaListener] 向客户端 {} 推送错误事件异常", clientId, e);
                    emitter.completeWithError(e);
                } finally {
                    AiKafkaController.EMITTER_MAP.remove(clientId);
                }
                return;
            }

            String reply = root.path("reply").asText("");
            String image = root.path("image").asText("");
            JsonNode metadata = root.path("metadata");

            // 封装发送 payload
            SseResponsePayload payload = new SseResponsePayload();
            payload.setReply(reply);
            payload.setImage(image);
            payload.setMetadata(metadata);

            try {
                // 1. 推送最终推理完成事件和答复数据
                emitter.send(SseEmitter.event()
                        .name("result")
                        .data(objectMapper.writeValueAsString(payload))
                );
                
                // 2. 标志连接优雅结束
                emitter.complete();
                log.info("[KafkaListener] 客户端 {} 数据推送完毕，已正常关闭 SSE 长连接。", clientId);
            } catch (IOException e) {
                log.error("[KafkaListener] 写入 SSE 数据流异常，注销会话，客户端: {}", clientId, e);
                emitter.completeWithError(e);
            } finally {
                AiKafkaController.EMITTER_MAP.remove(clientId);
            }

        } catch (Exception e) {
            log.error("[KafkaListener] 解析或推送 AI 结果报文异常", e);
        }
    }

    /**
     * SSE 最终结果推送报文
     */
    @lombok.Data
    public static class SseResponsePayload {
        private String reply;
        private String image;
        private JsonNode metadata;
    }
}
