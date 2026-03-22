package com.liangtouwu.business.controller;

import com.liangtouwu.business.dto.InspectionGenerateRequest;
import com.liangtouwu.business.dto.InspectionGenerateResponse;
import com.liangtouwu.business.service.InspectionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;

import java.util.Map;

@RestController
@RequestMapping("/inspection")
public class InspectionController {

    @Autowired
    private InspectionService inspectionService;

    @PostMapping("/generate")
    public InspectionGenerateResponse generate(@RequestBody InspectionGenerateRequest request) {
        return inspectionService.generateReport(request);
    }

    @PostMapping(value = "/generate/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public ResponseBodyEmitter generateStream(@RequestBody InspectionGenerateRequest request) {
        return inspectionService.generateReportStream(request);
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return inspectionService.healthCheck();
    }
}
