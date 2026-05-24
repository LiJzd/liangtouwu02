package com.liangtouwu.business.mapper;

import com.liangtouwu.domain.entity.Alert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface AlertMapper {
    Integer countTodayAlerts();
    List<Alert> findByCondition(@Param("search") String search, @Param("risk") String risk, @Param("area") String area);
    int insertAlert(Alert alert);
    int deleteAlertById(@Param("id") Long id);
    int deleteAlertsByIds(@Param("ids") List<Long> ids);
    int deleteAll();
}
