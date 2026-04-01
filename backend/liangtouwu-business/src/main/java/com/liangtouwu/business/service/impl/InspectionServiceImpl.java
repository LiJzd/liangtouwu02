package com.liangtouwu.business.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.liangtouwu.business.dto.InspectionGenerateRequest;
import com.liangtouwu.business.dto.InspectionGenerateResponse;
import com.liangtouwu.business.service.InspectionService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 生猪检测业务逻辑实现类 (AI 桥接层)
 * =====================================
 * 本类充当 Java 后端与 Python AI 后端之间的“中间人”。
 * 它不直接进行算法计算，而是将前端的检测请求透传给运行在 8000 端口的 FastAPI 服务，
 * 并负责将 AI 返回的 Markdown 结果（及 SSE 流）回传给前端。
 *
 * 核心技术：
 * 1. RestTemplate: 用于发送标准的 HTTP POST 请求。
 * 2. ResponseBodyEmitter: 用于实现异步的 SSE (Server-Sent Events) 流式中转。
 */
@Service
public class InspectionServiceImpl implements InspectionService {
    private static final Logger log = LoggerFactory.getLogger(InspectionServiceImpl.class);

    // AI 后端的 API 路由定义
    private static final String GENERATE_PATH = "/api/v1/inspection/generate"; // 同步生成
    private static final String GENERATE_STREAM_PATH = "/api/v1/inspection/generate/stream"; // 流式生成
    private static final String HEALTH_PATH = "/api/v1/inspection/health"; // 健康检查

    private final RestTemplate restTemplate;
    private final String fastApiBaseUrl;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 构造函数：初始化 RestTemplate 并配置超时时间
     * @param fastApiBaseUrl 来自 application.yml 的配置，默认 http://localhost:8000
     */
    public InspectionServiceImpl(
            RestTemplateBuilder restTemplateBuilder,
            @Value("${ai.fastapi.base-url:http://localhost:8000}") String fastApiBaseUrl,
            @Value("${ai.fastapi.connect-timeout-ms:3000}") long connectTimeoutMs,
            @Value("${ai.fastapi.read-timeout-ms:180000}") long readTimeoutMs) {

        this.fastApiBaseUrl = normalizeBaseUrl(fastApiBaseUrl);
        // 配置超时时间，检测任务通常较重，read-timeout 设置为 180 秒（3分钟）
        this.restTemplate = restTemplateBuilder
                .setConnectTimeout(Duration.ofMillis(connectTimeoutMs))
                .setReadTimeout(Duration.ofMillis(readTimeoutMs))
                .build();
    }

    /**
     * 接口 1: 同步生成检测报告
     * 将请求转发给 FastAPI，等待完整报告生成后一次性返回。
     */
    @Override
    public InspectionGenerateResponse generateReport(InspectionGenerateRequest request) {
        try {
            // 向 AI 后端发送 POST 请求
            ResponseEntity<InspectionGenerateResponse> response = restTemplate.postForEntity(
                    fastApiBaseUrl + GENERATE_PATH,
                    request,
                    InspectionGenerateResponse.class
            );

            InspectionGenerateResponse body = response.getBody();
            if (body != null) {
                return body;
            }

            return new InspectionGenerateResponse(
                    500,
                    "AI 服务未返回有效数据",
                    request.pigId(),
                    null,
                    "empty response body",
                    null
            );
        } catch (HttpStatusCodeException ex) {
            // 捕获 API 返回的 4xx/5xx 错误
            return new InspectionGenerateResponse(
                    ex.getStatusCode().value(),
                    "AI 服务请求失败",
                    request.pigId(),
                    null,
                    ex.getResponseBodyAsString(),
                    null
            );
        } catch (RestClientException ex) {
            // 捕获网络连接或超时错误
            return new InspectionGenerateResponse(
                    500,
                    "AI 服务暂不可用 (网络或超时)",
                    request.pigId(),
                    null,
                    ex.getMessage(),
                    null
            );
        }
    }

    /**
     * 接口 2: 流式生成检测报告 (SSE 转发)
     * 利用 Spring Boot 的 ResponseBodyEmitter 建立一个异步连接。
     * 在后台线程中读取 AI 返回的数据流，并逐行推送给浏览器。
     */
    @Override
    public ResponseBodyEmitter generateReportStream(InspectionGenerateRequest request) {
        // 创建一个永不超时的 emitter，直到手动关闭
        ResponseBodyEmitter emitter = new ResponseBodyEmitter(0L);
        emitter.onCompletion(() -> log.info("inspection stream completed pigId={}", request.pigId()));
        emitter.onTimeout(() -> log.warn("inspection stream timed out pigId={}", request.pigId()));
        emitter.onError(ex -> log.warn("inspection stream emitter error pigId={} error={}", request.pigId(), ex.toString()));

        // 开启异步任务，避免阻塞 Servlet 容器主线程
        CompletableFuture.runAsync(() -> {
            try {
                // restTemplate.execute 允许我们以流的方式处理响应体
                restTemplate.execute(
                        fastApiBaseUrl + GENERATE_STREAM_PATH,
                        HttpMethod.POST,
                        clientHttpRequest -> {
                            clientHttpRequest.getHeaders().setContentType(MediaType.APPLICATION_JSON);
                            clientHttpRequest.getHeaders().setAccept(List.of(MediaType.TEXT_EVENT_STREAM, MediaType.ALL));
                            objectMapper.writeValue(clientHttpRequest.getBody(), request);
                        },
                        clientHttpResponse -> {
                            // 逐行读取 AI 后端发送的 SSE 数据帧
                            try (BufferedReader reader = new BufferedReader(
                                    new InputStreamReader(clientHttpResponse.getBody(), StandardCharsets.UTF_8))) {
                                String line;
                                while ((line = reader.readLine()) != null) {
                                    // 将读取到的每一行原样推送到前端
                                    try {
                                        emitter.send(line + "\n", MediaType.TEXT_PLAIN);
                                    } catch (Exception sendEx) {
                                        if (isClientAbort(sendEx)) {
                                            log.info("inspection stream client disconnected pigId={}", request.pigId());
                                            return null;
                                        }
                                        throw sendEx;
                                    }
                                }
                            }
                            return null;
                        }
                );
                // AI 传输完毕，结束 emitter
                emitter.complete();
            } catch (Exception ex) {
                if (isClientAbort(ex)) {
                    log.info("inspection stream aborted by client pigId={}", request.pigId());
                    emitter.complete();
                    return;
                }
                // 异常处理：发送错误事件并结束连接
                try {
                    emitter.send("event: error\n", MediaType.TEXT_PLAIN);
                    emitter.send("data: {\"message\":\"流式转发失败\",\"detail\":\"" + ex.getMessage() + "\"}\n\n", MediaType.TEXT_PLAIN);
                } catch (Exception ignored) {
                }
                emitter.completeWithError(ex);
            }
        });

        return emitter;
    }

    /**
     * 系统监控：检查 AI 集群健康状态
     */
    @Override
    public Map<String, Object> healthCheck() {
        try {
            Map<?, ?> healthResponse = restTemplate.getForObject(fastApiBaseUrl + HEALTH_PATH, Map.class);
            if (healthResponse == null) {
                return downHealth("AI 服务响应空 body");
            }

            Map<String, Object> result = new HashMap<>();
            healthResponse.forEach((key, value) -> result.put(String.valueOf(key), value));
            return result;
        } catch (RestClientException ex) {
            return downHealth("连接 AI 节点超时: " + ex.getMessage());
        }
    }

    /**
     * URL 格式化：去除末尾斜杠
     */
    private boolean isClientAbort(Throwable throwable) {
        Throwable current = throwable;
        while (current != null) {
            String className = current.getClass().getName();
            String message = current.getMessage();
            if (className.contains("ClientAbortException") || className.contains("AsyncRequestNotUsableException")) {
                return true;
            }
            if (message != null) {
                String lower = message.toLowerCase();
                if (lower.contains("broken pipe")
                        || lower.contains("connection reset")
                        || message.contains("软件中止了一个已建立的连接")) {
                    return true;
                }
            }
            current = current.getCause();
        }
        return false;
    }

    private String normalizeBaseUrl(String baseUrl) {
        if (baseUrl == null || baseUrl.isBlank()) {
            return "http://localhost:8000";
        }
        if (baseUrl.endsWith("/")) {
            return baseUrl.substring(0, baseUrl.length() - 1);
        }
        return baseUrl;
    }

    /**
     * 构造服务宕机状态 DTO
     */
    private Map<String, Object> downHealth(String detail) {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "DOWN");
        result.put("service", "两头乌 AI 分析引擎");
        result.put("detail", detail == null ? "未知异常" : detail);
        return result;
    }
}
