package com.liangtouwu.business.controller;

import com.liangtouwu.business.dto.AlertBroadcastRequest;
import com.liangtouwu.business.dto.ai.*;
import com.liangtouwu.business.service.AiToolService;
import com.liangtouwu.common.vo.ApiResponse;
import com.liangtouwu.domain.entity.Alert;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

/**
 * AI Tool 专用 API 控制器
 * 
 * 设计原则：
 * 1. 扁平化 DTO：避免嵌套超过 2 层
 * 2. 精简字段：只返回 AI 需要的核心数据
 * 3. 租户隔离：强制校验 user_id（由拦截器处理）
 * 
 * 注意：
 * - 所有接口必须传递 X-User-ID Header
 * - 返回数据已去重去冗余
 */
@RestController
@RequestMapping("/v1/ai-tool")
public class AiToolController {

    private final AiToolService aiToolService;

    public AiToolController(AiToolService aiToolService) {
        this.aiToolService = aiToolService;
    }

    /**
     * 列出猪只列表
     */
    @PostMapping("/pigs/list")
    public ApiResponse<PigListResponse> listPigs(
        @RequestHeader("X-User-ID") String userId,
        @RequestBody @Valid PigListRequest request
    ) {
        return ApiResponse.success(aiToolService.listPigs(userId, request));
    }

    /**
     * 查询猪只详细档案
     */
    @PostMapping("/pigs/info")
    public ApiResponse<PigInfoResponse> getPigInfo(
        @RequestHeader("X-User-ID") String userId,
        @RequestBody @Valid PigInfoRequest request
    ) {
        return ApiResponse.success(aiToolService.getPigInfo(userId, request));
    }

    /**
     * 查询异常猪只列表
     */
    @PostMapping("/pigs/abnormal")
    public ApiResponse<AbnormalPigsResponse> getAbnormalPigs(
        @RequestHeader("X-User-ID") String userId,
        @RequestBody @Valid AbnormalPigsRequest request
    ) {
        return ApiResponse.success(aiToolService.getAbnormalPigs(userId, request));
    }

    /**
     * 获取猪场统计概览
     */
    @PostMapping("/farm/stats")
    public ApiResponse<FarmStatsResponse> getFarmStats(
        @RequestHeader("X-User-ID") String userId,
        @RequestBody(required = false) FarmStatsRequest request
    ) {
        return ApiResponse.success(aiToolService.getFarmStats(userId, request));
    }

    @PostMapping("/alerts/publish")
    public ApiResponse<Alert> publishAlert(
        @RequestHeader("X-User-ID") String userId,
        @RequestBody AlertBroadcastRequest request
    ) {
        return ApiResponse.success(aiToolService.publishAlert(userId, request));
    }
}
