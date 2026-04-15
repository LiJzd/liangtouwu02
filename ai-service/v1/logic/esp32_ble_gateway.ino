#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

/**
 * 两头乌智慧养殖系统 - ESP32 蓝牙风扇控制器网关
 * 功能：通过串口接收指令，转发至蓝牙风扇控制模块。
 * 指令集：
 *   '1' -> 开启风扇 (发送 A4 09 FF 00 00 37 37 37 37 37 37)
 *   '0' -> 关闭风扇 (发送 A4 09 00 00 00 37 37 37 37 37 37)
 *   's' -> 查询状态 (发送 A5 00)
 */

// ── 蓝牙配置 ──────────────────────────────────
static BLEUUID serviceUUID("0000ffb0-0000-1000-8000-00805f9b34fb");
static BLEUUID    charUUID("0000ffb1-0000-1000-8000-00805f9b34fb"); // 写特征
static BLEUUID  notifyUUID("0000ffb2-0000-1000-8000-00805f9b34fb"); // 通知特征

// 🎯 演示现场请务必确认此 MAC 地址是否正确
static String targetAddress = "20:26:03:23:02:c9"; 

static BLERemoteCharacteristic* pRemoteCharacteristic;
static BLEClient* pClient;
static bool connected = false;
static bool doConnect = false;

// ── 响应处理（接收风扇状态回传） ──────────────────────────────────────────────────
static void notifyCallback(BLERemoteCharacteristic* pBLERemoteCharacteristic, uint8_t* pData, size_t length, bool isNotify) {
    Serial.print("[BLE Notify] ");
    for (size_t i = 0; i < length; i++) {
        Serial.printf("%02X ", pData[i]);
    }
    Serial.println();
}

// ── 蓝牙连接逻辑 ────────────────────────────────────────────────────────
bool connectToServer() {
    Serial.print("正在连接到蓝牙设备: ");
    Serial.println(targetAddress);

    pClient = BLEDevice::createClient();
    
    if (!pClient->connect(BLEAddress(targetAddress.c_str()))) {
        Serial.println("❌ 连接失败！请检查风扇电源是否开启。");
        return false;
    }

    // 获取服务
    BLERemoteService* pRemoteService = pClient->getService(serviceUUID);
    if (pRemoteService == nullptr) {
        Serial.println("❌ 找不到 Service UUID，请确认协议版本。");
        pClient->disconnect();
        return false;
    }

    // 获取写特征
    pRemoteCharacteristic = pRemoteService->getCharacteristic(charUUID);
    if (pRemoteCharacteristic == nullptr) {
        Serial.println("❌ 找不到写特征，请确认协议版本。");
        pClient->disconnect();
        return false;
    }

    // 订阅通知
    BLERemoteCharacteristic* pNotifyChar = pRemoteService->getCharacteristic(notifyUUID);
    if (pNotifyChar != nullptr && pNotifyChar->canNotify()) {
        pNotifyChar->registerForNotify(notifyCallback);
    }

    connected = true;
    Serial.println("✅ 蓝牙连接成功！准备接收串口指令...");
    return true;
}

// ── 指令构造 ──────────────────────────────────

// 开关指令：A4 09 [状态] [延迟H] [延迟L] [6字节密码]
void sendSwitchCommand(bool on) {
    if (!connected) {
        Serial.println("警告: 蓝牙未连接，指令由于丢失。");
        return;
    }
    
    uint8_t state = on ? 0xFF : 0x00;
    
    // 密码默认为 777777 (0x37 x 6)
    uint8_t cmd[] = {0xA4, 0x09, state, 0x00, 0x00, 0x37, 0x37, 0x37, 0x37, 0x37, 0x37};
    
    pRemoteCharacteristic->writeValue(cmd, sizeof(cmd), false);
    Serial.printf(">>> 发送控制指令: %s\n", on ? "开启 (ON)" : "关闭 (OFF)");
}

// 状态查询指令：A5 00
void sendStatusRequest() {
    if (!connected) return;
    uint8_t cmd[] = {0xA5, 0x00};
    pRemoteCharacteristic->writeValue(cmd, sizeof(cmd), false);
    Serial.println(">>> 发送状态查询请求...");
}

void setup() {
  Serial.begin(115200);
  Serial.println("===============================");
  Serial.println("两头乌 PigBot ESP32 网关启动");
  Serial.println("===============================");
  
  BLEDevice::init("PigBot_Gateway");
  doConnect = true;
}

void loop() {
  // 维护连接
  if (doConnect) {
    if (connectToServer()) {
      doConnect = false;
      delay(500);
      sendStatusRequest();
    } else {
      Serial.println("等待 5 秒后重试连接...");
      delay(5000); 
    }
  }

  // 接收来自 AI 端的串口指令
  if (Serial.available()) {
    char in = Serial.read();
    if (in == '1') {
      sendSwitchCommand(true);
    } else if (in == '0') {
      sendSwitchCommand(false);
    } else if (in == 's') {
      sendStatusRequest();
    }
  }

  // 断线重连
  if (connected && !pClient->isConnected()) {
    connected = false;
    doConnect = true;
    Serial.println("⚠️ 蓝牙连接断开，正在尝试重连...");
  }
  
  delay(10);
}
