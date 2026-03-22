package com.liangtouwu.business.controller;

import com.liangtouwu.business.service.AnalysisService;
import com.liangtouwu.common.vo.ApiResponse;
import com.liangtouwu.domain.dto.AreaStats;
import com.liangtouwu.domain.entity.EnvironmentTrend;
import com.liangtouwu.domain.entity.Pig;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;

@RestController
@RequestMapping("")
public class AnalysisController {
    private final AnalysisService analysisService;

    public AnalysisController(AnalysisService analysisService) {
        this.analysisService = analysisService;
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
}
