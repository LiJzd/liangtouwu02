package com.liangtouwu.business.service;

import java.util.List;
import java.util.Map;

/**
 * Camera Service Interface
 * 摄像头服务接口
 */
public interface CameraService {
    /**
     * 获取所有摄像头列表
     * @return 摄像头信息列表
     */
    List<Map<String, Object>> getCameras();
}
