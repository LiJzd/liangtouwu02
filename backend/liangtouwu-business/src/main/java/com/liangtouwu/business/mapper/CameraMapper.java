package com.liangtouwu.business.mapper;

import com.liangtouwu.domain.entity.Camera;
import org.apache.ibatis.annotations.Mapper;
import java.util.List;

@Mapper
public interface CameraMapper {
    List<Camera> findAll();
}
