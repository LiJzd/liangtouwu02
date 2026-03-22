package com.liangtouwu.business.mapper;

import com.liangtouwu.domain.entity.DailyBriefing;
import org.apache.ibatis.annotations.Param;
import java.util.List;
import java.time.LocalDate;

public interface DailyBriefingMapper {
    void insert(DailyBriefing briefing);
    DailyBriefing findByDate(@Param("date") LocalDate date);
    List<DailyBriefing> findHistory(@Param("limit") int limit);
}
