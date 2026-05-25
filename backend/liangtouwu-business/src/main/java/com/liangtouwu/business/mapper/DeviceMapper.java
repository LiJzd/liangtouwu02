package com.liangtouwu.business.mapper;

import com.liangtouwu.domain.entity.Device;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;
import java.util.List;

@Mapper
public interface DeviceMapper {

    @Select("SELECT * FROM sys_device")
    List<Device> findAll();

    @Select("SELECT * FROM sys_device WHERE id = #{id}")
    Device findById(String id);

    @Update("UPDATE sys_device SET state = #{state}, value = #{value} WHERE id = #{id}")
    int updateDevice(Device device);
}
