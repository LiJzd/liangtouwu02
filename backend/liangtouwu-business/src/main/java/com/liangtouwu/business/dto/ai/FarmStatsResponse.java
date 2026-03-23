package com.liangtouwu.business.dto.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * 猪场统计响应（AI Tool 专用）
 * 
 * 扁平化设计：所有统计指标在同一层级
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FarmStatsResponse {

    private Integer totalPigs;
    private Integer abnormalCount;
    private Integer avgHealthScore;
    private BigDecimal avgBodyTemp;
    private Integer avgActivityLevel;
    private Integer todayNewAbnormal;
}
