package com.liangtouwu.business.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record InspectionGenerateRequest(
        @JsonProperty("pig_id") String pigId
) {
}
