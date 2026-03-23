package com.liangtouwu.business.dto.ai;

import lombok.Data;

/**
 * 猪场统计查询请求（AI Tool 专用）
 */
@Data
public class FarmStatsRequest {

    private Boolean includeAreaStats = false;
}
