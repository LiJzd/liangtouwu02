package com.liangtouwu.business.service;

import com.liangtouwu.domain.entity.DailyBriefing;
import java.util.List;

/**
 * Daily Briefing Service Interface
 */
public interface DailyBriefingService {
    DailyBriefing generateAndSaveBriefing();
    DailyBriefing getLatestBriefing();
    List<DailyBriefing> getBriefingHistory(int limit);
}
