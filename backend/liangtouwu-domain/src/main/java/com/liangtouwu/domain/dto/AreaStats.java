package com.liangtouwu.domain.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;

/**
 * 区域环境指标 DTO (Data Transfer Object)
 * =====================================
 * 该类用于将特定区域经过计算后的平均环境数据（如平均温湿度）传输给前端。
 * 不同于 EnvironmentTrend，它通常代表一个截面的统计结果而非历史趋势。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AreaStats {
    private String name;
    private BigDecimal temperature;
    private BigDecimal humidity;

    // 手动添加构造器以确保编译稳定性
    public static AreaStatsBuilder builder() {
        return new AreaStatsBuilder();
    }

    public static class AreaStatsBuilder {
        private String name;
        private BigDecimal temperature;
        private BigDecimal humidity;

        AreaStatsBuilder() {}

        public AreaStatsBuilder name(String name) {
            this.name = name;
            return this;
        }

        public AreaStatsBuilder temperature(BigDecimal temperature) {
            this.temperature = temperature;
            return this;
        }

        public AreaStatsBuilder humidity(BigDecimal humidity) {
            this.humidity = humidity;
            return this;
        }

        public AreaStats build() {
            return new AreaStats(name, temperature, humidity);
        }
    }
}
