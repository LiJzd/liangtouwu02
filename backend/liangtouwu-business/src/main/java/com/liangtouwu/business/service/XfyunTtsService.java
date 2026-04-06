package com.liangtouwu.business.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.liangtouwu.business.config.XfyunTtsProperties;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.Locale;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.TimeUnit;

@Service
public class XfyunTtsService {

    private static final URI BASE_URI = URI.create("wss://tts-api.xfyun.cn/v2/tts");
    private static final DateTimeFormatter RFC_1123 = DateTimeFormatter.RFC_1123_DATE_TIME.withLocale(Locale.US);

    private final XfyunTtsProperties properties;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    public XfyunTtsService(XfyunTtsProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        
        // 启动时打印配置状态（不打印敏感信息）
        System.out.println("=== 讯飞TTS配置状态 ===");
        System.out.println("Enabled: " + properties.isEnabled());
        System.out.println("AppId: " + (properties.getAppId() != null ? properties.getAppId().substring(0, Math.min(4, properties.getAppId().length())) + "****" : "未配置"));
        System.out.println("ApiKey: " + (properties.getApiKey() != null ? "已配置(" + properties.getApiKey().length() + "字符)" : "未配置"));
        System.out.println("ApiSecret: " + (properties.getApiSecret() != null ? "已配置(" + properties.getApiSecret().length() + "字符)" : "未配置"));
        System.out.println("VoiceName: " + properties.getVoiceName());
        System.out.println("Ready: " + properties.isReady());
        
        if (!properties.isReady()) {
            System.err.println("警告：讯飞TTS配置不完整，语音播报功能将不可用");
            System.err.println("请在application.yml中配置：xfyun.tts.app-id, api-key, api-secret");
            System.err.println("获取凭证：https://console.xfyun.cn");
        }
        System.out.println("=======================");
    }

    public byte[] synthesize(String text) {
        if (!properties.isReady()) {
            String errorMsg = "讯飞语音播报未完成配置。";
            if (properties.getAppId() == null || properties.getAppId().isEmpty()) {
                errorMsg += " 缺少 app-id。";
            }
            if (properties.getApiKey() == null || properties.getApiKey().isEmpty()) {
                errorMsg += " 缺少 api-key。";
            }
            if (properties.getApiSecret() == null || properties.getApiSecret().isEmpty()) {
                errorMsg += " 缺少 api-secret。";
            }
            System.err.println("TTS配置错误: " + errorMsg);
            throw new IllegalStateException(errorMsg);
        }
        if (!StringUtils.hasText(text)) {
            throw new IllegalArgumentException("播报文本不能为空");
        }

        String trimmedText = text.trim();
        if (trimmedText.length() > 500) {
            trimmedText = trimmedText.substring(0, 500);
            System.out.println("TTS: 文本过长，已截断至500字符");
        }

        CompletableFuture<byte[]> audioFuture = new CompletableFuture<>();
        ByteArrayOutputStream audioBuffer = new ByteArrayOutputStream();
        
        try {
            String payload = buildPayload(trimmedText);
            URI signedUri = buildAuthorizedUri();
            
            System.out.println("TTS: 开始语音合成");
            System.out.println("  文本长度: " + trimmedText.length());
            System.out.println("  WebSocket URI: " + signedUri.toString().substring(0, 50) + "...");

            httpClient.newWebSocketBuilder()
                    .buildAsync(signedUri, new WebSocket.Listener() {
                        private final StringBuilder frameBuffer = new StringBuilder();

                        @Override
                        public void onOpen(WebSocket webSocket) {
                            System.out.println("TTS: WebSocket连接成功");
                            webSocket.sendText(payload, true);
                            webSocket.request(1);
                        }

                        @Override
                        public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
                            frameBuffer.append(data);
                            if (!last) {
                                webSocket.request(1);
                                return CompletableFuture.completedFuture(null);
                            }

                            try {
                                handleFrame(frameBuffer.toString(), audioBuffer, audioFuture, webSocket);
                            } catch (Exception e) {
                                System.err.println("TTS: 处理响应帧失败 - " + e.getMessage());
                                e.printStackTrace();
                                audioFuture.completeExceptionally(e);
                                webSocket.abort();
                            } finally {
                                frameBuffer.setLength(0);
                            }

                            if (!audioFuture.isDone()) {
                                webSocket.request(1);
                            }
                            return CompletableFuture.completedFuture(null);
                        }

                        @Override
                        public void onError(WebSocket webSocket, Throwable error) {
                            System.err.println("TTS: WebSocket错误 - " + error.getMessage());
                            error.printStackTrace();
                            
                            String errorMsg = "WebSocket连接失败: " + error.getMessage();
                            
                            // 如果是403错误，提供更详细的错误信息
                            if (error.getMessage() != null && error.getMessage().contains("403")) {
                                errorMsg = "讯飞TTS认证失败(403 Forbidden)。可能的原因：\n" +
                                        "1. API凭证(AppId/ApiKey/ApiSecret)无效或已过期\n" +
                                        "2. IP地址未加入白名单（请在讯飞控制台检查IP白名单设置）\n" +
                                        "3. 服务未开通或余额不足\n" +
                                        "请登录讯飞开放平台控制台(https://console.xfyun.cn)检查：\n" +
                                        "- 应用是否已创建并开通语音合成服务\n" +
                                        "- API凭证是否正确\n" +
                                        "- IP白名单是否已关闭或正确配置\n" +
                                        "- 账户余额是否充足";
                            }
                            
                            audioFuture.completeExceptionally(new IllegalStateException(errorMsg));
                        }

                        @Override
                        public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
                            System.out.println("TTS: WebSocket关闭 - statusCode=" + statusCode + ", reason=" + reason);
                            if (!audioFuture.isDone()) {
                                if (audioBuffer.size() > 0) {
                                    audioFuture.complete(audioBuffer.toByteArray());
                                } else {
                                    audioFuture.completeExceptionally(new IllegalStateException("语音合成失败：未收到音频数据"));
                                }
                            }
                            return CompletableFuture.completedFuture(null);
                        }
                    })
                    .exceptionally(error -> {
                        System.err.println("TTS: 创建WebSocket失败 - " + error.getMessage());
                        error.printStackTrace();
                        audioFuture.completeExceptionally(new IllegalStateException("无法连接到讯飞语音服务: " + error.getMessage()));
                        return null;
                    });

            byte[] result = audioFuture.orTimeout(30, TimeUnit.SECONDS).join();
            System.out.println("TTS: 语音合成成功，音频大小=" + result.length + " bytes");
            return result;
        } catch (Exception e) {
            Throwable cause = e.getCause() != null ? e.getCause() : e;
            System.err.println("TTS: 语音合成失败 - " + cause.getMessage());
            cause.printStackTrace();
            throw new IllegalStateException("讯飞语音合成失败: " + cause.getMessage(), cause);
        }
    }

    private void handleFrame(
            String frame,
            ByteArrayOutputStream audioBuffer,
            CompletableFuture<byte[]> audioFuture,
            WebSocket webSocket
    ) throws Exception {
        JsonNode root = objectMapper.readTree(frame);
        int code = root.path("code").asInt();
        if (code != 0) {
            String message = root.path("message").asText("讯飞语音合成失败");
            throw new IllegalStateException(message + " [code=" + code + "]");
        }

        JsonNode dataNode = root.path("data");
        String audioBase64 = dataNode.path("audio").asText("");
        if (StringUtils.hasText(audioBase64)) {
            audioBuffer.write(Base64.getDecoder().decode(audioBase64));
        }

        if (dataNode.path("status").asInt() == 2 && !audioFuture.isDone()) {
            audioFuture.complete(audioBuffer.toByteArray());
            webSocket.sendClose(WebSocket.NORMAL_CLOSURE, "completed");
        }
    }

    private URI buildAuthorizedUri() {
        try {
            String host = BASE_URI.getHost();
            String path = BASE_URI.getPath();
            
            // 生成RFC1123格式的日期（GMT时区）
            ZonedDateTime now = ZonedDateTime.now(ZoneOffset.UTC);
            String date = now.format(RFC_1123);

            // 构建签名原文（严格按照讯飞文档格式，注意换行符）
            String signatureOrigin = "host: " + host + "\n"
                    + "date: " + date + "\n"
                    + "GET " + path + " HTTP/1.1";

            // 使用HMAC-SHA256生成签名（使用ApiSecret）
            String signature = hmacSha256Base64(signatureOrigin, properties.getApiSecret());

            // 构建authorization原文（注意：headers字段必须与签名原文一致）
            String authorizationOrigin = "api_key=\"" + properties.getApiKey() + "\", "
                    + "algorithm=\"hmac-sha256\", "
                    + "headers=\"host date request-line\", "
                    + "signature=\"" + signature + "\"";

            // Base64编码authorization
            String authorization = Base64.getEncoder()
                    .encodeToString(authorizationOrigin.getBytes(StandardCharsets.UTF_8));

            // 构建完整URL（注意：根据讯飞文档，参数需要URL编码）
            // 但authorization参数本身已经是Base64编码，可能不需要再次URL编码
            String query = "authorization=" + authorization
                    + "&date=" + urlEncode(date)
                    + "&host=" + urlEncode(host);
            
            URI result = URI.create(BASE_URI.toString() + "?" + query);
            
            System.out.println("=== TTS认证详情 ===");
            System.out.println("Host: " + host);
            System.out.println("Path: " + path);
            System.out.println("Date: " + date);
            System.out.println("Signature Origin:\n" + signatureOrigin);
            System.out.println("Signature: " + signature);
            System.out.println("Authorization Origin: " + authorizationOrigin);
            System.out.println("Authorization (Base64): " + authorization);
            System.out.println("Final URI: " + result.toString());
            System.out.println("==================");
            
            return result;
        } catch (Exception e) {
            System.err.println("TTS: 构建认证URI失败 - " + e.getMessage());
            e.printStackTrace();
            throw new IllegalStateException("构建认证URI失败: " + e.getMessage(), e);
        }
    }

    private String buildPayload(String text) {
        ObjectNode root = objectMapper.createObjectNode();
        ObjectNode common = root.putObject("common");
        common.put("app_id", properties.getAppId());

        ObjectNode business = root.putObject("business");
        business.put("aue", "lame");
        business.put("sfl", 1);
        business.put("tte", "UTF8");
        business.put("vcn", properties.getVoiceName());
        business.put("speed", properties.getSpeed());
        business.put("volume", properties.getVolume());
        business.put("pitch", properties.getPitch());

        ObjectNode data = root.putObject("data");
        data.put("status", 2);
        data.put("text", Base64.getEncoder().encodeToString(text.getBytes(StandardCharsets.UTF_8)));

        return root.toString();
    }

    private String hmacSha256Base64(String content, String secret) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return Base64.getEncoder().encodeToString(mac.doFinal(content.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException("讯飞签名生成失败", e);
        }
    }

    private String urlEncode(String value) {
        return java.net.URLEncoder.encode(value, StandardCharsets.UTF_8);
    }
}
