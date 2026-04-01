package com.liangtouwu.business.dto;

import lombok.Data;

@Data
public class AlertBroadcastRequest {
    private String pigId;
    private String area;
    private String type;
    private String risk;
    private String timestamp;
    private String announcementText;
}
