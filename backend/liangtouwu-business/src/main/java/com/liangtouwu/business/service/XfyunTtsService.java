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
    }

    public byte[] synthesize(String text) {
        if (!properties.isReady()) {
            throw new IllegalStateException("讯飞语音播报未完成配置，请补充 xfyun.tts.app-id 和 xfyun.tts.api-secret。");
        }
        if (!StringUtils.hasText(text)) {
            throw new IllegalArgumentException("播报文本不能为空");
        }

        CompletableFuture<byte[]> audioFuture = new CompletableFuture<>();
        ByteArrayOutputStream audioBuffer = new ByteArrayOutputStream();
        String payload = buildPayload(text.trim());
        URI signedUri = buildAuthorizedUri();
        
        // 添加日志
        System.out.println("TTS WebSocket URL: " + signedUri);
        System.out.println("TTS Payload: " + payload);

        httpClient.newWebSocketBuilder()
                .buildAsync(signedUri, new WebSocket.Listener() {
                    private final StringBuilder frameBuffer = new StringBuilder();

                    @Override
                    public void onOpen(WebSocket webSocket) {
                        System.out.println("TTS WebSocket opened successfully");
                        webSocket.sendText(payload, true);
                        webSocket.request(1);
                    }

                    @Override
                    public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
                        System.out.println("TTS received text: " + data + ", last=" + last);
                        frameBuffer.append(data);
                        if (!last) {
                            webSocket.request(1);
                            return CompletableFuture.completedFuture(null);
                        }

                        try {
                            handleFrame(frameBuffer.toString(), audioBuffer, audioFuture, webSocket);
                        } catch (Exception e) {
                            System.err.println("TTS frame handling error: " + e.getMessage());
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
                        System.err.println("TTS WebSocket Error: " + error.getMessage());
                        error.printStackTrace();
                        audioFuture.completeExceptionally(error);
                    }

                    @Override
                    public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
                        System.out.println("TTS WebSocket closed: statusCode=" + statusCode + ", reason=" + reason);
                        if (!audioFuture.isDone()) {
                            audioFuture.complete(audioBuffer.toByteArray());
                        }
                        return CompletableFuture.completedFuture(null);
                    }
                })
                .exceptionally(error -> {
                    System.err.println("TTS WebSocket buildAsync failed: " + error.getMessage());
                    error.printStackTrace();
                    audioFuture.completeExceptionally(error);
                    return null;
                });

        try {
            return audioFuture.orTimeout(25, TimeUnit.SECONDS).join();
        } catch (Exception e) {
            throw new IllegalStateException("讯飞语音合成失败: " + e.getMessage(), e);
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
        String host = BASE_URI.getHost();
        String path = BASE_URI.getPath();
        String date = RFC_1123.format(ZonedDateTime.now(ZoneOffset.UTC));

        // 按照讯飞文档拼接签名原文
        String signatureOrigin = "host: " + host + "\n"
                + "date: " + date + "\n"
                + "GET " + path + " HTTP/1.1";

        String signature = hmacSha256Base64(signatureOrigin, properties.getApiSecret());

        // 拼接authorization原文
        String authorizationOrigin = "api_key=\"" + properties.getApiKey() + "\", "
                + "algorithm=\"hmac-sha256\", "
                + "headers=\"host date request-line\", "
                + "signature=\"" + signature + "\"";

        String authorization = Base64.getEncoder()
                .encodeToString(authorizationOrigin.getBytes(StandardCharsets.UTF_8));

        // 构建完整URL（注意：不要对authorization再次编码）
        String query = "authorization=" + authorization
                + "&date=" + urlEncode(date)
                + "&host=" + urlEncode(host);
        
        return URI.create(BASE_URI.toString() + "?" + query);
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
