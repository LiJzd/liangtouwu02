# -*- coding: utf-8 -*-
import logging
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    logger.warning("未检测到 pyserial 库，IOT 控制将运行在【模拟演示模式】。")

# ----------------------------------------------------------------
# 串口配置
# ----------------------------------------------------------------
SERIAL_PORT = "COM11"
BAUD_RATE = 115200

# ----------------------------------------------------------------
# 数据模型
# ----------------------------------------------------------------
class DeviceControlRequest(BaseModel):
    state: bool  # True 为开启，False 为关闭
    device_id: Optional[str] = "ESP32_Fan_Gateway"

class DeviceStatusResponse(BaseModel):
    device_id: str
    is_online: bool
    current_state: str
    last_action_timestamp: str
    mode: str  # "real" 或 "simulated"

# ----------------------------------------------------------------
# IoT 逻辑管理器 (串口中继控制模式)
# ----------------------------------------------------------------
class IoTManager:
    _instance = None
    _simulated_state = "CLOSED"
    _serial_conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IoTManager, cls).__new__(cls)
        return cls._instance

    def _get_serial(self):
        if not HAS_SERIAL:
            return None
        
        if self._serial_conn is None or not self._serial_conn.is_open:
            try:
                self._serial_conn = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
                logger.info(f"成功打开串口: {SERIAL_PORT}")
            except Exception as e:
                logger.error(f"打开串口 {SERIAL_PORT} 失败: {str(e)}")
                self._serial_conn = None
        return self._serial_conn

    async def send_command(self, cmd_char: str) -> bool:
        """发送单字符指令到 ESP32 串口 ('1', '0', 's')"""
        if not HAS_SERIAL:
            logger.info(f"[模拟模式] 向串口 {SERIAL_PORT} 发送指令: '{cmd_char}'")
            return True

        # 由于串口写操作会阻塞，使用 asyncio.to_thread 包装
        def _write():
            try:
                conn = self._get_serial()
                if conn:
                    conn.write(cmd_char.encode('ascii'))
                    conn.flush()
                    return True
                return False
            except Exception as e:
                logger.error(f"写入串口 {SERIAL_PORT} 失败: {str(e)}")
                # 出现异常时强制重连
                if self._serial_conn:
                    try:
                        self._serial_conn.close()
                    except:
                        pass
                    self._serial_conn = None
                return False

        try:
            success = await asyncio.to_thread(_write)
            if success:
                logger.info(f"✅ 已通过串口 {SERIAL_PORT} 下发指令 '{cmd_char}'")
            else:
                logger.error(f"❌ 无法通过串口 {SERIAL_PORT} 下发指令，请检查硬件连接或端口号 (当前: {SERIAL_PORT})")
            return success
        except Exception as e:
            logger.error(f"串口任务调度异常: {str(e)}")
            return False

    async def set_switch(self, on: bool) -> bool:
        """执行开关操作 (ESP32 端映射 '1'开，'0'关)"""
        cmd = '1' if on else '0'
        success = await self.send_command(cmd)
        if success:
            self._simulated_state = "OPEN" if on else "CLOSED"
        return success

    async def run_duration(self, seconds: int):
        """
        自动化联动：开启风扇并在指定秒数后自动关闭。
        """
        logger.info(f"开启自动化联动：风扇运行 {seconds} 秒")
        try:
            # 开启
            await self.set_switch(True)
            # 等待
            await asyncio.sleep(seconds)
            # 关闭
            await self.set_switch(False)
            logger.info("自动化联动结束：风扇已自动关闭")
        except Exception as e:
            logger.error(f"自动化联动执行异常: {e}")

    async def get_status(self) -> str:
        """执行状态查询操作 (ESP32 端映射 's'查)"""
        cmd = 's'
        await self.send_command(cmd)
        # 实际情况需要读取串口回传，这里简化返回最后一次记录的状态
        return self._simulated_state

# ----------------------------------------------------------------
# 路由定义
# ----------------------------------------------------------------
router = APIRouter()
iot_manager = IoTManager()

@router.post("/device/control", response_model=dict)
async def control_device(req: DeviceControlRequest = Body(...)):
    """
    控制智能风扇开关
    """
    success = await iot_manager.set_switch(req.state)
    if not success and HAS_SERIAL:
        raise HTTPException(status_code=500, detail="ESP32 串口通信失败，请检查硬件连接。")
    
    return {
        "status": "success",
        "action": "OPEN" if req.state else "CLOSE",
        "device": req.device_id,
        "mode": "real" if HAS_SERIAL else "simulated",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/device/status", response_model=DeviceStatusResponse)
async def get_device_status():
    """
    获取智能风扇当前状态
    """
    state = await iot_manager.get_status()
    return DeviceStatusResponse(
        device_id="ESP32_Fan_Gateway",
        is_online=True if not HAS_SERIAL else (iot_manager._get_serial() is not None),
        current_state=state,
        last_action_timestamp=datetime.now().isoformat(),
        mode="real" if HAS_SERIAL else "simulated"
    )
