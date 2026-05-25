package com.liangtouwu.business.controller;

import com.liangtouwu.business.mapper.DeviceMapper;
import com.liangtouwu.common.vo.ApiResponse;
import com.liangtouwu.domain.entity.Device;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/devices")
public class DeviceController {

    @Autowired
    private DeviceMapper deviceMapper;

    /**
     * 获取所有设备的状态列表
     */
    @GetMapping("")
    public ApiResponse<List<Device>> getDevices() {
        return ApiResponse.success(deviceMapper.findAll());
    }

    /**
     * 控制指定设备的状态及设定值
     */
    @PostMapping("/control")
    public ApiResponse<Void> controlDevice(@RequestBody Device device) {
        if (device == null || device.getId() == null) {
            return ApiResponse.error("设备ID不能为空");
        }
        
        Device existing = deviceMapper.findById(device.getId());
        if (existing == null) {
            return ApiResponse.error("设备不存在");
        }
        
        // 允许部分更新
        if (device.getState() != null) {
            existing.setState(device.getState());
        }
        if (device.getValue() != null) {
            existing.setValue(device.getValue());
        }
        
        deviceMapper.updateDevice(existing);
        System.out.println("[DeviceController] Device controlled successfully: " + existing);
        return ApiResponse.success(null);
    }
}
