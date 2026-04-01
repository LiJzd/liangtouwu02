package com.liangtouwu.business.dto;

import com.liangtouwu.domain.entity.Alert;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlertBroadcastEvent {
    private String eventId;
    private String spokenText;
    private Alert alert;
}
