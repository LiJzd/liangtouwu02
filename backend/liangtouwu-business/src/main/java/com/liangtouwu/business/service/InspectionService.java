package com.liangtouwu.business.service;

import com.liangtouwu.business.dto.InspectionGenerateRequest;
import com.liangtouwu.business.dto.InspectionGenerateResponse;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;

import java.util.Map;

public interface InspectionService {
    InspectionGenerateResponse generateReport(InspectionGenerateRequest request);

    ResponseBodyEmitter generateReportStream(InspectionGenerateRequest request);

    Map<String, Object> healthCheck();
}
