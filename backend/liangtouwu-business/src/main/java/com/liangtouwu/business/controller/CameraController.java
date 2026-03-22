package com.liangtouwu.business.controller;

import com.liangtouwu.business.service.CameraService;
import com.liangtouwu.common.vo.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/camera")
public class CameraController {
    private final CameraService cameraService;
    public CameraController(CameraService cameraService) { this.cameraService = cameraService; }

    @GetMapping("/list")
    public ApiResponse<List<Map<String, Object>>> list() {
        return ApiResponse.success(cameraService.getCameras());
    }
}
