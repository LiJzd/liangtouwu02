package com.liangtouwu.domain.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;

/**
 * 主控台统计数据 DTO (Data Transfer Object)
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DashboardStats {

    private BigDecimal averageTemp;
    private Integer activityLevel;
    private Integer alertCount;

    // 扩充字段以对接前端的各种展示卡片
    private Integer count;               // 全场实时总头数
    private String countChange;         // 周头数变化量
    private String efficiency;          // 核心繁育效率
    private String mortality;           // 当日死亡率
    private String avgWeight;           // 场均体重
    private String feedRatio;           // 全周料肉比
    private String dailyFeed;           // 场均日供料总量
    private String dailyWater;          // 每日饮水总量
    private String deviceOnline;        // 核心设备在线率
}
