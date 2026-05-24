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
    List<Pig> findAllPigs();
    
    // 业务扩展逻辑
    
    // 分页查询猪只列表
    List<Pig> findByUserId(@Param("userId") String userId, @Param("limit") Integer limit);
    
    // 获取详情
    Pig findByIdAndUserId(@Param("pigId") String pigId, @Param("userId") String userId);
    
    // 筛选异常记录
    List<Pig> findAbnormalByUserId(@Param("userId") String userId, 
                                     @Param("threshold") Integer threshold, 
                                     @Param("limit") Integer limit);
    
    // 统计相关
    Integer countByUserId(@Param("userId") String userId);
    Integer countAbnormalByUserId(@Param("userId") String userId, @Param("threshold") Integer threshold);
    Double getAvgBodyTempByUserId(@Param("userId") String userId);
    Integer getAvgActivityLevelByUserId(@Param("userId") String userId);
    Integer getAvgHealthScoreByUserId(@Param("userId") String userId);
}
