package com.liangtouwu.business.dto.ai;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 猪只档案查询请求（AI Tool 专用）
 */
@Data
public class PigInfoRequest {

    @NotBlank(message = "pigId 不能为空")
    private String pigId;

    private Boolean includeLifecycle = true;
}
