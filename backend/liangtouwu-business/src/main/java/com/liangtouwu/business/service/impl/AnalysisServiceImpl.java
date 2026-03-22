package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.mapper.EnvironmentTrendMapper;
import com.liangtouwu.business.mapper.PigMapper;
import com.liangtouwu.business.service.AnalysisService;
import com.liangtouwu.domain.dto.AreaStats;
import com.liangtouwu.domain.entity.EnvironmentTrend;
import com.liangtouwu.domain.entity.Pig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
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
}
