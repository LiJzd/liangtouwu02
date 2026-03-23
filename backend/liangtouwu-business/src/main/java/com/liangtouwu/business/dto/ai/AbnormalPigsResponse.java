package com.liangtouwu.business.dto.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

/**
 * 异常猪只响应（AI Tool 专用）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AbnormalPigsResponse {

    private Integer count;
    private List<AbnormalPigDTO> pigs;

    /**
     * 异常猪只信息（扁平化）
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AbnormalPigDTO {
        private String id;
        private Integer healthScore;
        private String issue;
        private BigDecimal bodyTemp;
        private Integer activityLevel;
        private Integer dayAge;
    }
}
