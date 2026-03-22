package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.mapper.DailyBriefingMapper;
import com.liangtouwu.business.service.DailyBriefingService;
import com.liangtouwu.domain.entity.DailyBriefing;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * Daily Briefing Service Implementation
 */
@Slf4j
@Service
public class DailyBriefingServiceImpl implements DailyBriefingService {

    private final DailyBriefingMapper dailyBriefingMapper;
    private final RestTemplate restTemplate;
    private final String fastApiBaseUrl;

    public DailyBriefingServiceImpl(
            DailyBriefingMapper dailyBriefingMapper,
            RestTemplateBuilder restTemplateBuilder,
            @Value("${ai.fastapi.base-url:http://localhost:8000}") String fastApiBaseUrl) {
        this.dailyBriefingMapper = dailyBriefingMapper;
        this.restTemplate = restTemplateBuilder.build();
        this.fastApiBaseUrl = fastApiBaseUrl;
    }

    @Scheduled(cron = "0 0 12 * * ?")
    @Override
    public DailyBriefing generateAndSaveBriefing() {
        log.info("Starting Daily Briefing generation...");
        try {
            LocalDate today = LocalDate.now();
            
            // 检查今天是否已有简报
            DailyBriefing existing = dailyBriefingMapper.findByDate(today);
            if (existing != null) {
                log.info("Daily Briefing for {} already exists, returning existing one", today);
                return existing;
            }
            
            String url = fastApiBaseUrl + "/api/v1/inspection/briefing";
            log.info("Calling AI service URL: {}", url);
            
            Map<String, Object> response = restTemplate.postForObject(url, null, Map.class);
            log.info("AI service response: {}", response);
            
            if (response != null && response.get("data") != null) {
                Object codeObj = response.get("code");
                // 兼容 code 为 Integer 或 String 类型
                boolean isSuccess = (codeObj instanceof Integer && (Integer) codeObj == 200) 
                                 || (codeObj instanceof String && "200".equals(codeObj));
                
                if (isSuccess) {
                    Map<String, Object> data = (Map<String, Object>) response.get("data");
                    String report = (String) data.get("report");
                    String summary = (String) data.get("summary");
                    
                    DailyBriefing briefing = new DailyBriefing(
                            null,
                            today,
                            report,
                            summary,
                            LocalDateTime.now()
                    );
                    
                    dailyBriefingMapper.insert(briefing);
                    log.info("Daily Briefing saved successfully for: {}", today);
                    return briefing;
                } else {
                    log.warn("AI service returned non-200 code: {}", codeObj);
                }
            } else {
                log.warn("AI service returned empty response or missing data field: {}", response);
            }
        } catch (Exception e) {
            log.error("Exception during Daily Briefing generation", e);
        }
        return null;
    }

    @Override
    public DailyBriefing getLatestBriefing() {
        List<DailyBriefing> history = dailyBriefingMapper.findHistory(1);
        return history.isEmpty() ? null : history.get(0);
    }

    @Override
    public List<DailyBriefing> getBriefingHistory(int limit) {
        return dailyBriefingMapper.findHistory(limit);
    }
}