package com.liangtouwu.business.service;

import com.liangtouwu.domain.dto.AreaStats;
import com.liangtouwu.domain.entity.EnvironmentTrend;
import com.liangtouwu.domain.entity.Pig;
import java.util.List;

public interface AnalysisService {
    List<EnvironmentTrend> getTrends();
    List<AreaStats> getAreaStats();
    List<Pig> getAbnormalPigs();
    List<Pig> getAllPigs();
}
