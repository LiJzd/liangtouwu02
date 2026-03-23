package com.liangtouwu.business.dto.ai;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

/**
 * 异常猪只查询请求（AI Tool 专用）
 */
@Data
public class AbnormalPigsRequest {

    @Min(value = 0, message = "threshold 最小为 0")
    @Max(value = 100, message = "threshold 最大为 100")
    private Integer threshold = 60;

    @Min(value = 1, message = "limit 最小为 1")
    @Max(value = 100, message = "limit 最大为 100")
    private Integer limit = 20;
}
