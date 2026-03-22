package com.liangtouwu.business.controller;

import com.liangtouwu.business.service.MonitorService;
import com.liangtouwu.common.vo.ApiResponse;
import com.liangtouwu.domain.entity.Camera;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;

@RestController
@RequestMapping("/cameras")
public class MonitorController {
    private final MonitorService monitorService;
    public MonitorController(MonitorService monitorService) { this.monitorService = monitorService; }

    @GetMapping("")
    public ApiResponse<List<Camera>> getCameras() {
        return ApiResponse.success(monitorService.getCameras());
    }
}
