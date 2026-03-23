package com.liangtouwu.business.dto.ai;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

/**
 * 猪只列表查询请求（AI Tool 专用）
 */
@Data
public class PigListRequest {

    @Min(value = 1, message = "limit 最小为 1")
    @Max(value = 200, message = "limit 最大为 200")
    private Integer limit = 50;

    private Boolean abnormalOnly = false;
}
