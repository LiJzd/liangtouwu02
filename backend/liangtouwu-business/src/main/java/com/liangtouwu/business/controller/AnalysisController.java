package com.liangtouwu.business.controller;

import com.liangtouwu.business.service.AnalysisService;
import com.liangtouwu.business.service.GrowthCurveService;
import com.liangtouwu.common.vo.ApiResponse;
import com.liangtouwu.domain.dto.AreaStats;
import com.liangtouwu.domain.entity.EnvironmentTrend;
import com.liangtouwu.domain.entity.Pig;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("")
public class AnalysisController {
    private final AnalysisService analysisService;
    private final GrowthCurveService growthCurveService;

    public AnalysisController(AnalysisService analysisService, GrowthCurveService growthCurveService) {
        this.analysisService = analysisService;
        this.growthCurveService = growthCurveService;
    }

    @GetMapping("/environment/trends")
    public com.liangtouwu.common.vo.ApiResponse<List<EnvironmentTrend>> getTrends() {
        return com.liangtouwu.common.vo.ApiResponse.success(analysisService.getTrends());
    }

    @GetMapping("/area/stats")
    public com.liangtouwu.common.vo.ApiResponse<List<AreaStats>> getAreaStats() {
        return com.liangtouwu.common.vo.ApiResponse.success(analysisService.getAreaStats());
    }

    @GetMapping("/pigs/abnormal")
    public com.liangtouwu.common.vo.ApiResponse<List<Pig>> getAbnormalPigs() {
        return com.liangtouwu.common.vo.ApiResponse.success(analysisService.getAbnormalPigs());
    }

    @GetMapping("/pigs/list")
    public com.liangtouwu.common.vo.ApiResponse<List<Pig>> getPigsList() {
        return com.liangtouwu.common.vo.ApiResponse.success(analysisService.getAllPigs());
    }

    @GetMapping("/pigs/{pigId}/growth-curve")
    public com.liangtouwu.common.vo.ApiResponse<List<Map<String, Object>>> getGrowthCurve(@PathVariable String pigId) {
        return com.liangtouwu.common.vo.ApiResponse.success(growthCurveService.getGrowthCurve(pigId));
    }
}
