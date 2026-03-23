package com.liangtouwu.business.dto.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

/**
 * 猪只列表响应（AI Tool 专用）
 * 
 * 设计原则：
 * 1. 扁平化：所有字段在同一层级
 * 2. 精简：只包含 AI 需要的核心字段
 * 3. 类型明确：避免使用 Object 或 Map
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PigListResponse {

    private Integer total;
    private List<PigSimpleDTO> pigs;

    /**
     * 猪只简要信息（扁平化）
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PigSimpleDTO {
        private String id;
        private String breed;
        private BigDecimal currentWeight;
        private Integer dayAge;
        private Integer healthScore;
        private String issue;
    }
}
