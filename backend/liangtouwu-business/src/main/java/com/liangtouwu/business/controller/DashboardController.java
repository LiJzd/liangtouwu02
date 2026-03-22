package com.liangtouwu.business.controller;

import com.liangtouwu.common.vo.ApiResponse;
import com.liangtouwu.domain.dto.DashboardStats;
import com.liangtouwu.business.service.DashboardService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/dashboard")
public class DashboardController {

    @Autowired
    private DashboardService dashboardService;

    @GetMapping("/stats")
    public ApiResponse<DashboardStats> getStats() {
        return ApiResponse.success(dashboardService.getStats());
    }
}
