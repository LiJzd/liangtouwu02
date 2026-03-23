package com.liangtouwu.business.mapper;

import com.liangtouwu.domain.entity.Pig;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import java.util.List;

@Mapper
public interface PigMapper {
    Integer getAverageActivityLevel();
    Double getAverageBodyTemp();
    List<Pig> findAbnormalPigs();
    
    // ========== AI Tool 专用方法（租户隔离） ==========
    
    /**
     * 查询指定用户的猪只列表
     * @param userId 用户 ID（租户隔离）
     * @param limit 返回数量限制
     */
    List<Pig> findByUserId(@Param("userId") String userId, @Param("limit") Integer limit);
    
    /**
     * 查询指定用户的单个猪只详情
     * @param pigId 猪只 ID
     * @param userId 用户 ID（租户隔离）
     */
    Pig findByIdAndUserId(@Param("pigId") String pigId, @Param("userId") String userId);
    
    /**
     * 查询指定用户的异常猪只
     * @param userId 用户 ID（租户隔离）
     * @param threshold 健康评分阈值
     * @param limit 返回数量限制
     */
    List<Pig> findAbnormalByUserId(@Param("userId") String userId, 
                                     @Param("threshold") Integer threshold, 
                                     @Param("limit") Integer limit);
    
    /**
     * 统计指定用户的猪场数据
     * @param userId 用户 ID（租户隔离）
     */
    Integer countByUserId(@Param("userId") String userId);
    Integer countAbnormalByUserId(@Param("userId") String userId, @Param("threshold") Integer threshold);
    Double getAvgBodyTempByUserId(@Param("userId") String userId);
    Integer getAvgActivityLevelByUserId(@Param("userId") String userId);
    Integer getAvgHealthScoreByUserId(@Param("userId") String userId);
}
