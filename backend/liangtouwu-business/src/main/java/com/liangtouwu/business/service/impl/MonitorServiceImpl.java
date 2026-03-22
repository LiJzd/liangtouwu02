package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.mapper.CameraMapper;
import com.liangtouwu.business.service.MonitorService;
import com.liangtouwu.domain.entity.Camera;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Map;

@Service
public class MonitorServiceImpl implements MonitorService {
    @Autowired
    private CameraMapper cameraMapper;
    
    @Value("${ai.fastapi.base-url:http://localhost:8000}")
    private String aiBaseUrl;
    
    // 摄像头 ID 到视频文件的映射
    private static final Map<Long, String> CAMERA_VIDEO_MAP = Map.of(
        1L, "保育-西南角_20250409000000-20250411000000_15 - 副本.mp4",  // 摄像头 1
        2L, "保育-西南角_20250409000000-20250411000000_23 - 副本.mp4"   // 摄像头 2
    );

    @Override
    public List<Camera> getCameras() {
        List<Camera> cameras = cameraMapper.findAll();
        // 为每个摄像头设置视频流 URL
        for (Camera camera : cameras) {
            if ("online".equals(camera.getStatus())) {
                String videoFile = CAMERA_VIDEO_MAP.getOrDefault(camera.getId(), "video.mp4");
                // 视频流地址指向 AI 端的感知 API
                camera.setStreamUrl(aiBaseUrl + "/api/v1/perception/stream/" + videoFile);
            }
        }
        return cameras;
    }
}
