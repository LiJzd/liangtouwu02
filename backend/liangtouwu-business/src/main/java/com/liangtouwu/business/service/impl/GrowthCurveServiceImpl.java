package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.service.GrowthCurveService;
import org.springframework.stereotype.Service;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@Service
public class GrowthCurveServiceImpl implements GrowthCurveService {
    @Override
    public List<Map<String, Object>> getGrowthCurve(String pigId) {
        return Collections.emptyList();
    }
}
