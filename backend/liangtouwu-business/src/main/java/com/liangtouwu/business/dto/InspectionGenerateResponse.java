package com.liangtouwu.business.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record InspectionGenerateResponse(
        Integer code,
        String message,
        @JsonProperty("pig_id") String pigId,
        String report,
        String detail,
        String timestamp
) {
}
