package com.liangtouwu.business.service;

import com.liangtouwu.business.dto.AlertBroadcastRequest;
import com.liangtouwu.business.dto.ai.*;
import com.liangtouwu.domain.entity.Alert;

/**
 * AI Tool 服务接口
 * 
 * 职责：
 * 1. 为 AI Agent 提供数据查询服务
 * 2. 强制租户隔离（所有方法必须传入 userId）
 * 3. 数据扁平化处理
 */
public interface AiToolService {

    /**
     * 列出猪只列表
     * 
     * @param userId 用户ID（租户隔离）
     * @param request 查询参数
     * @return 猪只列表
     */
    PigListResponse listPigs(String userId, PigListRequest request);

    /**
     * 查询猪只详细档案
     * 
     * @param userId 用户ID（租户隔离）
     * @param request 查询参数
     * @return 猪只档案
     */
    PigInfoResponse getPigInfo(String userId, PigInfoRequest request);

    /**
     * 查询异常猪只列表
     * 
     * @param userId 用户ID（租户隔离）
     * @param request 查询参数
     * @return 异常猪只列表
     */
    AbnormalPigsResponse getAbnormalPigs(String userId, AbnormalPigsRequest request);

    /**
     * 获取猪场统计概览
     * 
     * @param userId 用户ID（租户隔离）
     * @param request 查询参数
     * @return 猪场统计
     */
    FarmStatsResponse getFarmStats(String userId, FarmStatsRequest request);

    Alert publishAlert(String userId, AlertBroadcastRequest request);
}
