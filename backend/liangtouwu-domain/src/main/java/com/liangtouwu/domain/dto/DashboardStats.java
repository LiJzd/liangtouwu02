package com.liangtouwu.domain.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;

/**
 * 主控台统计数据 DTO (Data Transfer Object)
 * <p>
 * 用于传输主控台首页所需的核心指标数据。
 * </p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DashboardStats {

    private BigDecimal averageTemp;
    private Integer activityLevel;
    private Integer alertCount;

    // 手动添加构造器以确保编译稳定性
    public static DashboardStatsBuilder builder() {
        return new DashboardStatsBuilder();
    }

    public static class DashboardStatsBuilder {
        private BigDecimal averageTemp;
        private Integer activityLevel;
        private Integer alertCount;

        DashboardStatsBuilder() {}

        public DashboardStatsBuilder averageTemp(BigDecimal averageTemp) {
            this.averageTemp = averageTemp;
            return this;
        }

        public DashboardStatsBuilder activityLevel(Integer activityLevel) {
            this.activityLevel = activityLevel;
            return this;
        }

        public DashboardStatsBuilder alertCount(Integer alertCount) {
            this.alertCount = alertCount;
            return this;
        }

        public DashboardStats build() {
            return new DashboardStats(averageTemp, activityLevel, alertCount);
        }
    }
}
