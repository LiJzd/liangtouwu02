package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.service.GrowthCurveService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class GrowthCurveServiceImpl implements GrowthCurveService {

    private static final String GENERATE_PATH = "/api/v1/inspection/generate";

    private final RestTemplate restTemplate;
    private final String fastApiBaseUrl;

    public GrowthCurveServiceImpl(
            RestTemplateBuilder restTemplateBuilder,
            @Value("${ai.fastapi.base-url:http://localhost:8000}") String fastApiBaseUrl,
            @Value("${ai.fastapi.connect-timeout-ms:3000}") long connectTimeoutMs,
            @Value("${ai.fastapi.read-timeout-ms:180000}") long readTimeoutMs) {
        this.fastApiBaseUrl = normalizeBaseUrl(fastApiBaseUrl);
        this.restTemplate = restTemplateBuilder
                .setConnectTimeout(Duration.ofMillis(connectTimeoutMs))
                .setReadTimeout(Duration.ofMillis(readTimeoutMs))
                .build();
    }

    @Override
    public List<Map<String, Object>> getGrowthCurve(String pigId) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("pig_id", pigId);

            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.postForObject(
                    fastApiBaseUrl + GENERATE_PATH,
                    request,
                    Map.class
            );

            if (response == null) {
                log.warn("Growth curve AI response is null for pigId={}", pigId);
                return Collections.emptyList();
            }

            Object code = response.get("code");
            Object report = response.get("report");
            if (!(code instanceof Number) || ((Number) code).intValue() != 200 || !(report instanceof String) || ((String) report).isBlank()) {
                log.warn(
                        "Growth curve AI response invalid pigId={} code={} detail={}",
                        pigId,
                        code,
                        response.get("detail")
                );
                return Collections.emptyList();
            }

            return parseCurvePoints((String) report);
        } catch (RestClientException e) {
            log.error("Failed to call AI growth curve endpoint for pigId={}", pigId, e);
            return Collections.emptyList();
        } catch (Exception e) {
            log.error("Failed to parse AI growth curve report for pigId={}", pigId, e);
            return Collections.emptyList();
        }
    }

    private List<Map<String, Object>> parseCurvePoints(String report) {
        Map<Integer, Map<String, Object>> pointsByMonth = new LinkedHashMap<>();
        String[] lines = report.replace("\r", "").split("\n");

        for (String rawLine : lines) {
            String line = rawLine == null ? "" : rawLine.trim();
            if (!line.startsWith("|") || line.contains("---")) {
                continue;
            }

            List<String> cells = extractCells(line);
            if (cells.size() < 3) {
                continue;
            }

            Integer month = parseInteger(cells.get(0));
            Double weight = parseDouble(cells.get(1));
            if (month == null || weight == null || month <= 0 || weight <= 0) {
                continue;
            }

            Map<String, Object> point = new LinkedHashMap<>();
            point.put("month", month);
            point.put("weight", weight);
            point.put("status", cells.get(2));
            pointsByMonth.put(month, point);
        }

        List<Map<String, Object>> points = new ArrayList<>(pointsByMonth.values());
        points.sort((left, right) -> Integer.compare(
                ((Number) left.get("month")).intValue(),
                ((Number) right.get("month")).intValue()
        ));
        return points;
    }

    private List<String> extractCells(String line) {
        String[] parts = line.split("\\|");
        List<String> cells = new ArrayList<>();
        for (String part : parts) {
            String cell = part == null ? "" : part.trim();
            if (!cell.isEmpty()) {
                cells.add(cell);
            }
        }
        return cells;
    }

    private Integer parseInteger(String text) {
        String normalized = text == null ? "" : text.replaceAll("[^\\d]", "");
        if (normalized.isEmpty()) {
            return null;
        }
        try {
            return Integer.parseInt(normalized);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Double parseDouble(String text) {
        String normalized = text == null ? "" : text.replaceAll("[^\\d.]", "");
        if (normalized.isEmpty()) {
            return null;
        }
        try {
            return Double.parseDouble(normalized);
        } catch (NumberFormatException e) {
            return null;
        }
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
}
