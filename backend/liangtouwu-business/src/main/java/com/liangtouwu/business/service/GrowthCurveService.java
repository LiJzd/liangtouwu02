package com.liangtouwu.business.service;

import java.util.List;
import java.util.Map;

/**
 * Growth Curve Service Interface
 */
public interface GrowthCurveService {
    /**
     * Get growth curve data for a specific pig
     * @param pigId String ID of the pig (e.g. PIG-001)
     * @return List of month-weight mappings
     */
    List<Map<String, Object>> getGrowthCurve(String pigId);
}
