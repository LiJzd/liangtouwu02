package com.liangtouwu.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 智能日报实体类
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DailyBriefing {
    private Long id;
    private LocalDate briefingDate;
    private String content;
    private String summary;
    private LocalDateTime createdAt;
}
