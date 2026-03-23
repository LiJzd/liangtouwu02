package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.dto.ai.*;
import com.liangtouwu.business.mapper.PigMapper;
import com.liangtouwu.business.service.AiToolService;
import com.liangtouwu.domain.entity.Pig;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * AI Tool 服务实现
 * 
 * 核心原则：
 * 1. 所有查询必须带 userId 过滤（租户隔离）
 * 2. 数据扁平化处理
 * 3. 异常统一处理，返回友好错误信息
 */
@Slf4j
@Service
public class AiToolServiceImpl implements AiToolService {

    private final PigMapper pigMapper;

    public AiToolServiceImpl(PigMapper pigMapper) {
        this.pigMapper = pigMapper;
    }

    @Override
    public PigListResponse listPigs(String userId, PigListRequest request) {
        log.info("AI Tool - listPigs: userId={}, limit={}, abnormalOnly={}", 
            userId, request.getLimit(), request.getAbnormalOnly());

        try {
            List<Pig> pigs;
            
            if (request.getAbnormalOnly()) {
                // 查询异常猪只（健康评分 >= 60 或有问题描述）
                pigs = pigMapper.findAbnormalByUserId(userId, 60, request.getLimit());
            } else {
                // 查询所有猪只
                pigs = pigMapper.findByUserId(userId, request.getLimit());
            }

            // 转换为扁平化 DTO
            List<PigListResponse.PigSimpleDTO> pigDTOs = pigs.stream()
                .map(this::convertToPigSimpleDTO)
                .collect(Collectors.toList());

            return PigListResponse.builder()
                .total(pigDTOs.size())
                .pigs(pigDTOs)
                .build();

        } catch (Exception e) {
            log.error("AI Tool - listPigs 失败: userId={}, error={}", userId, e.getMessage(), e);
            throw new RuntimeException("查询猪只列表失败: " + e.getMessage());
        }
    }

    @Override
    public PigInfoResponse getPigInfo(String userId, PigInfoRequest request) {
        log.info("AI Tool - getPigInfo: userId={}, pigId={}, includeLifecycle={}", 
            userId, request.getPigId(), request.getIncludeLifecycle());

        try {
            // 租户隔离查询
            Pig pig = pigMapper.findByIdAndUserId(request.getPigId(), userId);
            
            if (pig == null) {
                throw new RuntimeException("猪只不存在或无权访问: " + request.getPigId());
            }

            // 转换为扁平化 DTO
            PigInfoResponse response = PigInfoResponse.builder()
                .id(pig.getId())
                .breed("金华两头乌") // TODO: 从数据库读取品种字段
                .currentWeight(BigDecimal.valueOf(45.5)) // TODO: 从数据库读取体重字段
                .dayAge(120) // TODO: 从数据库读取日龄字段
                .currentMonth(4) // TODO: 从数据库读取月龄字段
                .healthScore(pig.getScore())
                .issue(pig.getIssue())
                .bodyTemp(pig.getBodyTemp())
                .activityLevel(pig.getActivityLevel())
                .build();

            // 如果需要生长周期数据
            if (request.getIncludeLifecycle()) {
                // TODO: 从数据库查询生长周期历史记录
                List<PigInfoResponse.LifecyclePoint> lifecycle = new ArrayList<>();
                for (int month = 1; month <= 4; month++) {
                    lifecycle.add(PigInfoResponse.LifecyclePoint.builder()
                        .month(month)
                        .weight(BigDecimal.valueOf(5.0 + month * 10))
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
            // 租户隔离查询
            List<Pig> abnormalPigs = pigMapper.findAbnormalByUserId(
                userId, 
                request.getThreshold(), 
                request.getLimit()
            );

            // 转换为扁平化 DTO
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
            // 租户隔离统计查询
            Integer totalPigs = pigMapper.countByUserId(userId);
            Integer abnormalCount = pigMapper.countAbnormalByUserId(userId, 60);
            Integer avgHealthScore = pigMapper.getAvgHealthScoreByUserId(userId);
            Double avgBodyTempDouble = pigMapper.getAvgBodyTempByUserId(userId);
            Integer avgActivityLevel = pigMapper.getAvgActivityLevelByUserId(userId);
            
            // 处理空值
            BigDecimal avgBodyTemp = avgBodyTempDouble != null 
                ? BigDecimal.valueOf(avgBodyTempDouble).setScale(2, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

            return FarmStatsResponse.builder()
                .totalPigs(totalPigs != null ? totalPigs : 0)
                .abnormalCount(abnormalCount != null ? abnormalCount : 0)
                .avgHealthScore(avgHealthScore != null ? avgHealthScore : 0)
                .avgBodyTemp(avgBodyTemp)
                .avgActivityLevel(avgActivityLevel != null ? avgActivityLevel : 0)
                .todayNewAbnormal(0) // TODO: 需要新增时间戳字段才能统计今日新增
                .build();

        } catch (Exception e) {
            log.error("AI Tool - getFarmStats 失败: userId={}, error={}", userId, e.getMessage(), e);
            throw new RuntimeException("查询猪场统计失败: " + e.getMessage());
        }
    }

    // ========== 私有转换方法 ==========

    private PigListResponse.PigSimpleDTO convertToPigSimpleDTO(Pig pig) {
        return PigListResponse.PigSimpleDTO.builder()
            .id(pig.getId())
            .breed("金华两头乌") // TODO: 从数据库读取
            .currentWeight(BigDecimal.valueOf(45.5)) // TODO: 从数据库读取
            .dayAge(120) // TODO: 从数据库读取
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
            .dayAge(120) // TODO: 从数据库读取
            .build();
    }
}
