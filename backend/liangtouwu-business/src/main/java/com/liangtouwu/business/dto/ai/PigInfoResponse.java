package com.liangtouwu.business.dto.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

/**
 * 猪只档案响应（AI Tool 专用）
 * 
 * 扁平化设计：
 * - 基础信息在第一层
 * - 生长周期数据在第二层（数组）
 * - 避免深层嵌套
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PigInfoResponse {

    // ========== 基础信息 ==========
    private String id;
    private String breed;
    private BigDecimal currentWeight;
    private Integer dayAge;
    private Integer currentMonth;
    private Integer healthScore;
    private String issue;
    private BigDecimal bodyTemp;
    private Integer activityLevel;

    // ========== 生长周期数据 ==========
    private List<LifecyclePoint> lifecycle;

    /**
     * 生长周期数据点（扁平化）
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
