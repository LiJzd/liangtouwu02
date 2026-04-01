package com.liangtouwu.business.service;

import com.liangtouwu.business.dto.AlertSimulationRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.util.Map;

@Service
public class AlertSimulationService {

    private static final String SIMULATION_PATH = "/api/v1/agent/simulations/ingest";

    private final RestTemplate restTemplate;
    private final String fastApiBaseUrl;

    public AlertSimulationService(
            RestTemplateBuilder restTemplateBuilder,
            @Value("${ai.fastapi.base-url:http://localhost:8000}") String fastApiBaseUrl,
            @Value("${ai.fastapi.connect-timeout-ms:3000}") long connectTimeoutMs,
            @Value("${ai.fastapi.read-timeout-ms:180000}") long readTimeoutMs) {
        this.restTemplate = restTemplateBuilder
                .setConnectTimeout(Duration.ofMillis(connectTimeoutMs))
                .setReadTimeout(Duration.ofMillis(readTimeoutMs))
                .build();
        this.fastApiBaseUrl = normalizeBaseUrl(fastApiBaseUrl);
    }

    public Map<String, Object> forwardSimulation(AlertSimulationRequest request) {
        Map<String, Object> response = restTemplate.postForObject(
                fastApiBaseUrl + SIMULATION_PATH,
                request,
                Map.class
        );
        if (response == null) {
            throw new IllegalStateException("AI simulation service returned empty response");
        }
        return response;
    }

    private String normalizeBaseUrl(String baseUrl) {
        if (baseUrl == null || baseUrl.isBlank()) {
            return "http://localhost:8000";
        }
        return baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    }
}
