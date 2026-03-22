package com.liangtouwu.business.controller;

import com.liangtouwu.domain.entity.Alert;
import com.liangtouwu.business.service.AlertService;
import com.liangtouwu.common.vo.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;

@RestController
@RequestMapping("/alerts")
public class AlertController {
    private final AlertService alertService;
    public AlertController(AlertService alertService) { this.alertService = alertService; }

    @GetMapping("")
    public ApiResponse<List<Alert>> getAlerts(
            @RequestParam(required = false) String search,
            @RequestParam(required = false) String risk,
            @RequestParam(required = false) String area) {
        return ApiResponse.success(alertService.getAlerts(search, risk, area));
    }
}
