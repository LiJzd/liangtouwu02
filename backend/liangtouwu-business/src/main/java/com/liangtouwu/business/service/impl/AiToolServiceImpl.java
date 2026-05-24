package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.dto.AlertBroadcastRequest;
import com.liangtouwu.business.dto.ai.*;
import com.liangtouwu.business.mapper.PigMapper;
import com.liangtouwu.business.service.AiToolService;
import com.liangtouwu.business.service.AlertService;
import com.liangtouwu.domain.entity.Alert;
import com.liangtouwu.domain.entity.Pig;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * AI 工具服务实现，支持多租户隔离
 */
@Slf4j
@Service
public class AiToolServiceImpl implements AiToolService {

    private final PigMapper pigMapper;
    private final AlertService alertService;

    public AiToolServiceImpl(PigMapper pigMapper, AlertService alertService) {
        this.pigMapper = pigMapper;
        this.alertService = alertService;
    }

    @Override
    public PigListResponse listPigs(String userId, PigListRequest request) {
        log.debug("Get pig list: userId={}, abnormalOnly={}", userId, request.getAbnormalOnly());

        try {
            List<Pig> pigs;
            
            if (request.getAbnormalOnly()) {
                pigs = pigMapper.findAbnormalByUserId(userId, 60, request.getLimit());
            } else {
                pigs = pigMapper.findByUserId(userId, request.getLimit());
            }

            List<PigListResponse.PigSimpleDTO> pigDTOs = pigs.stream()
                .map(this::convertToPigSimpleDTO)
                .collect(Collectors.toList());

            return PigListResponse.builder()
                .total(pigDTOs.size())
                .pigs(pigDTOs)
                .build();

        } catch (Exception e) {
            log.error("查询猪只列表失败", e);
            throw new RuntimeException("查询猪只列表失败: " + e.getMessage());
        }
    }

    @Override
    public PigInfoResponse getPigInfo(String userId, PigInfoRequest request) {
        log.info("AI Tool - getPigInfo: userId={}, pigId={}, includeLifecycle={}", 
            userId, request.getPigId(), request.getIncludeLifecycle());

        try {
            Pig pig = pigMapper.findByIdAndUserId(request.getPigId(), userId);
            
            if (pig == null) {
                throw new RuntimeException("猪只不存在或无权访问: " + request.getPigId());
            }

            PigInfoResponse response = PigInfoResponse.builder()
                .id(pig.getId())
                .breed("两头乌") // 暂时硬编码
                .currentWeight(BigDecimal.valueOf(35.2))
                .dayAge(90)
                .currentMonth(3)
                .healthScore(pig.getScore())
                .issue(pig.getIssue())
                .bodyTemp(pig.getBodyTemp())
                .activityLevel(pig.getActivityLevel())
                .build();

            if (request.getIncludeLifecycle()) {
                List<PigInfoResponse.LifecyclePoint> lifecycle = new ArrayList<>();
                for (int month = 1; month <= 3; month++) {
                    double mockWeight = month == 1 ? 14.8 : (month == 2 ? 25.2 : 35.2);
                    lifecycle.add(PigInfoResponse.LifecyclePoint.builder()
                        .month(month)
                        .weight(BigDecimal.valueOf(mockWeight))
                        .dayAge(month * 30)
                        .build());
                }
                response.setLifecycle(lifecycle);
            }

            return response;

        } catch (Exception e) {
            log.error("AI Tool - getPigInfo 失败: userId={}, pigId={}, error={}", 
                userId, request.getPigId(), e.getMessage(), e);
            throw new RuntimeException("查询猪只档案失败: " + e.getMessage());
        }
    }

    @Override
    public AbnormalPigsResponse getAbnormalPigs(String userId, AbnormalPigsRequest request) {
        log.info("AI Tool - getAbnormalPigs: userId={}, threshold={}, limit={}", 
            userId, request.getThreshold(), request.getLimit());

        try {
            List<Pig> abnormalPigs = pigMapper.findAbnormalByUserId(
                userId, 
                request.getThreshold(), 
                request.getLimit()
            );

            List<AbnormalPigsResponse.AbnormalPigDTO> pigDTOs = abnormalPigs.stream()
                .map(this::convertToAbnormalPigDTO)
                .collect(Collectors.toList());

            return AbnormalPigsResponse.builder()
                .count(pigDTOs.size())
                .pigs(pigDTOs)
                .build();

        } catch (Exception e) {
            log.error("AI Tool - getAbnormalPigs 失败: userId={}, error={}", userId, e.getMessage(), e);
            throw new RuntimeException("查询异常猪只失败: " + e.getMessage());
        }
    }

    @Override
    public FarmStatsResponse getFarmStats(String userId, FarmStatsRequest request) {
        log.info("AI Tool - getFarmStats: userId={}", userId);

        try {
            Integer totalPigs = pigMapper.countByUserId(userId);
            Integer abnormalCount = pigMapper.countAbnormalByUserId(userId, 60);
            Integer avgHealthScore = pigMapper.getAvgHealthScoreByUserId(userId);
            Double avgBodyTempDouble = pigMapper.getAvgBodyTempByUserId(userId);
            Integer avgActivityLevel = pigMapper.getAvgActivityLevelByUserId(userId);
            
            BigDecimal avgBodyTemp = avgBodyTempDouble != null 
                ? BigDecimal.valueOf(avgBodyTempDouble).setScale(2, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

            return FarmStatsResponse.builder()
                .totalPigs(totalPigs != null ? totalPigs : 0)
                .abnormalCount(abnormalCount != null ? abnormalCount : 0)
                .avgHealthScore(avgHealthScore != null ? avgHealthScore : 0)
                .avgBodyTemp(avgBodyTemp)
                .avgActivityLevel(avgActivityLevel != null ? avgActivityLevel : 0)
                .todayNewAbnormal(0)
                .build();

        } catch (Exception e) {
            log.error("AI Tool - getFarmStats 失败: userId={}, error={}", userId, e.getMessage(), e);
            throw new RuntimeException("查询猪场统计失败: " + e.getMessage());
        }
    }

    @Override
    public Alert publishAlert(String userId, AlertBroadcastRequest request) {
        log.info("AI Tool - publishAlert: userId={}, pigId={}, area={}, type={}",
            userId, request.getPigId(), request.getArea(), request.getType());
        return alertService.createAndBroadcastAlert(request);
    }

    // 实体转换逻辑

    private PigListResponse.PigSimpleDTO convertToPigSimpleDTO(Pig pig) {
        return PigListResponse.PigSimpleDTO.builder()
            .id(pig.getId())
            .breed("两头乌")
            .currentWeight(BigDecimal.valueOf(35.2))
            .dayAge(90)
            .healthScore(pig.getScore())
            .issue(pig.getIssue())
            .build();
    }

    private AbnormalPigsResponse.AbnormalPigDTO convertToAbnormalPigDTO(Pig pig) {
        return AbnormalPigsResponse.AbnormalPigDTO.builder()
            .id(pig.getId())
            .healthScore(pig.getScore())
            .issue(pig.getIssue())
            .bodyTemp(pig.getBodyTemp())
            .activityLevel(pig.getActivityLevel())
            .dayAge(120)
            .build();
    }
}
