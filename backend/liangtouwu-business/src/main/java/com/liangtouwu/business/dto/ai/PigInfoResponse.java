package com.liangtouwu.business.dto.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

/**
 * 猪只档案响应 (用于 AI 推理分析)
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PigInfoResponse {

    // 基础信息
    private String id;
    private String breed;
    private BigDecimal currentWeight;
    private Integer dayAge;
    private Integer currentMonth;
    private Integer healthScore;
    private String issue;
    private BigDecimal bodyTemp;
    private Integer activityLevel;

    // 生长周期历史
    private List<LifecyclePoint> lifecycle;

    /**
     * 周期数据采样点
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class LifecyclePoint {
        private Integer month;
        private BigDecimal weight;
        private Integer dayAge;
    }
}
