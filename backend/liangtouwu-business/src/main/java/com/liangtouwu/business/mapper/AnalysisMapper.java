package com.liangtouwu.business.mapper;

import org.apache.ibatis.annotations.Mapper;
import java.util.Map;

@Mapper
public interface AnalysisMapper {
    Map<String, Object> getStats();
}
