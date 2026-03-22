package com.liangtouwu.business.mapper;

import com.liangtouwu.domain.dto.AreaStats;
import com.liangtouwu.domain.entity.EnvironmentTrend;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

/**
 * 环境趋势数据持久层映射接口 (MyBatis)
 * =====================================
 * 该接口负责处理养殖场环境监控数据的查询，包括传感器数值的历史趋势及各区域的实时汇总统计。
 */
@Mapper
public interface EnvironmentTrendMapper {

    /**
     * 查询最近的环境变化趋势
     * 通常返回过去 24 小时或一段时间内的温湿度、氨气浓度等时序数据。
     */
    List<EnvironmentTrend> findRecentTrends();

    /**
     * 获取各养殖区域的最新的统计概览
     * 聚合各区域的平均环境指标及生猪数量。
     */
    List<AreaStats> findLatestAreaStats();
}
