package com.liangtouwu.business.dto;

import lombok.Data;

import java.util.Map;

@Data
public class AlertSimulationRequest {
    private String pigId;
    private String area;
    private String source = "simulated_event";
    private String timestamp;
    private Double bodyTemp;
    private Integer activityLevel;
    private Integer healthScore;
    private Double temperatureC;
    private Double humidityPct;
    private Double ammoniaPpm;
    private String type;
    private String description;
    private String risk;
    private String announcementText;
    private Map<String, Object> thresholds;
}
