package com.liangtouwu.domain.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;

/**
 * 环境趋势 (EnvironmentTrend) 领域实体模型
 * =====================================
 * 该类对应数据库中的 `environment_trend` 表，记录猪舍内部各监测点的环境实时指标。
 * 用于构建前端的大屏环境监控趋势图。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "environment_trend")
public class EnvironmentTrend {

    /**
     * 数据记录唯一 ID
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * 采样时间点
     * 格式示例："08:00", "12:00"（通常用于 X 轴展示）。
     */
    private String time;

    /**
     * 监测区域/猪舍名称
     * 例如："一号哺乳舍", "育肥区B"。
     */
    private String area;

    /**
     * 环境温度数值
     * 单位：摄氏度 (°C)。
     */
    private BigDecimal temperature;

    /**
     * 环境相对湿度
     * 单位：百分比 (%)。
     */
    private BigDecimal humidity;
}
