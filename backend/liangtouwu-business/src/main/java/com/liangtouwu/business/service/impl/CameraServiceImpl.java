package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.mapper.CameraMapper;
import com.liangtouwu.business.service.CameraService;
import com.liangtouwu.domain.entity.Camera;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Camera Service Implementation
 * 摄像头服务实现类
 */
@Service
public class CameraServiceImpl implements CameraService {
    
    @Autowired
    private CameraMapper cameraMapper;

    @Override
    public List<Map<String, Object>> getCameras() {
        List<Camera> cameras = cameraMapper.findAll();
        return cameras.stream().map(camera -> {
            Map<String, Object> map = new HashMap<>();
            map.put("id", camera.getId());
            map.put("name", camera.getName());
            map.put("status", camera.getStatus());
            map.put("location", camera.getLocation());
            return map;
        }).collect(Collectors.toList());
    }
}
