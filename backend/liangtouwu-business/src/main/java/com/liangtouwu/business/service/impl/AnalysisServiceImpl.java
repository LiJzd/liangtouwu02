package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.mapper.EnvironmentTrendMapper;
import com.liangtouwu.business.mapper.PigMapper;
import com.liangtouwu.business.service.AnalysisService;
import com.liangtouwu.domain.dto.AreaStats;
import com.liangtouwu.domain.entity.EnvironmentTrend;
import com.liangtouwu.domain.entity.Pig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.util.List;

@Service
public class AnalysisServiceImpl implements AnalysisService {
    @Autowired
    private EnvironmentTrendMapper environmentTrendMapper;
    
    @Autowired
    private PigMapper pigMapper;

    @Override
    public List<EnvironmentTrend> getTrends() {
        return environmentTrendMapper.findRecentTrends();
    }

    @Override
    public List<AreaStats> getAreaStats() {
        return environmentTrendMapper.findLatestAreaStats();
    }

    @Override
    public List<Pig> getAbnormalPigs() {
        return pigMapper.findAbnormalPigs();
    }

    @Override
    public List<Pig> getAllPigs() {
        List<Pig> pigs = pigMapper.findAllPigs();
        // 为缺失的字段设置默认值（用于生长曲线功能）
        for (Pig pig : pigs) {
            if (pig.getArea() == null) {
                // 根据ID分配区域
                int hash = Math.abs(pig.getId().hashCode());
                pig.setArea(hash % 3 == 0 ? "猪舍A" : hash % 3 == 1 ? "猪舍B" : "猪舍C");
            }
            if (pig.getCurrentWeightKg() == null) {
                // 设置模拟体重 (30-70kg)
                pig.setCurrentWeightKg(BigDecimal.valueOf(30.0 + Math.random() * 40));
            }
            if (pig.getCurrentMonth() == null) {
                // 设置模拟月龄 (2-6月)
                pig.setCurrentMonth(2 + (int)(Math.random() * 5));
            }
        }
        return pigs;
    }
}
