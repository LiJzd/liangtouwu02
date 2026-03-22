package com.liangtouwu.business.controller;

import com.liangtouwu.business.service.DailyBriefingService;
import com.liangtouwu.domain.entity.DailyBriefing;
import com.liangtouwu.common.vo.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * Daily Briefing Controller
 */
@RestController
@RequestMapping("/briefing")
public class BriefingController {

    private final DailyBriefingService dailyBriefingService;

    public BriefingController(DailyBriefingService dailyBriefingService) {
        this.dailyBriefingService = dailyBriefingService;
    }

    @GetMapping("/latest")
    public ApiResponse<DailyBriefing> getLatest() {
        return ApiResponse.success(dailyBriefingService.getLatestBriefing());
    }

    @GetMapping("/history")
    public ApiResponse<List<DailyBriefing>> getHistory(@RequestParam(value = "limit", defaultValue = "10") int limit) {
        return ApiResponse.success(dailyBriefingService.getBriefingHistory(limit));
    }

    @PostMapping("/trigger")
    public ApiResponse<DailyBriefing> trigger() {
        return ApiResponse.success(dailyBriefingService.generateAndSaveBriefing());
    }
}
