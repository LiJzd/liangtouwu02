package com.liangtouwu.business.mapper;

import com.liangtouwu.domain.entity.Pig;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface PigMapper {
    Integer getAverageActivityLevel();
    Double getAverageBodyTemp();
    List<Pig> findAbnormalPigs();
}
