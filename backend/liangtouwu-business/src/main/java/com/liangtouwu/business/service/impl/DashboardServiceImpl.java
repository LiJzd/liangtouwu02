package com.liangtouwu.business.service.impl;

import com.liangtouwu.domain.dto.DashboardStats;
import com.liangtouwu.business.mapper.AlertMapper;
import com.liangtouwu.business.mapper.PigMapper;
import com.liangtouwu.business.service.DashboardService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * 仪表盘统计业务实现类
 * =====================================
 * 本服务负责为养殖场指挥中心（Dashboard）提供实时概览数据。
 * 它从生猪档案、实时监测数据以及预警库中提取核心指标，并进行汇总计算。
 */
@Service
public class DashboardServiceImpl implements DashboardService {

    @Autowired
    private PigMapper pigMapper;

    @Autowired
    private AlertMapper alertMapper;

    /**
     * 获取全场核心统计指标
     * 包含：
     * 1. 全场生猪平均体温（反映是否存在热应激或疫情风险）
     * 2. 全场生猪平均活力等级（由 AI 分析视频得出并存储在库中）
     * 3. 今日新增预警总数
     * 
     * @return 封装好的统计 DTO
     */
    @Override
    public DashboardStats getStats() {
        // 从生猪表聚合平均体温
        Double avgTemp = pigMapper.getAverageBodyTemp();
        // 从生猪表聚合平均活动强度
        Integer avgActivity = pigMapper.getAverageActivityLevel();
        // 统计今日 0 点以来的预警记录数
        Integer alertCount = alertMapper.countTodayAlerts();

        // 构造 DTO 并进行数值精修 (体温保留一位小数)
        return DashboardStats.builder()
                .averageTemp(avgTemp != null ? BigDecimal.valueOf(avgTemp).setScale(1, RoundingMode.HALF_UP) : BigDecimal.ZERO)
                .activityLevel(avgActivity != null ? avgActivity : 0)
                .alertCount(alertCount != null ? alertCount : 0)
                .build();
    }
}
