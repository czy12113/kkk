/**
 * 飞控端接收示例代码 (C/C++)
 *
 * 此代码展示如何在飞控上解析从 RDK X5 等设备发送的雷达数据
 * 适用于 STM32、Arduino 等嵌入式平台
 *
 * 机载计算机侧（Linux）USB 转 TTL 接飞控时，串口设备名常见为：
 *   /dev/ttyCH343USB0
 * 与 ROS2 节点 lidar_serial_bridge / lidar_fc_bridge 的 serial_port 默认值一致。
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// 数据包类型
#define FRAME_HEADER_1      0xAA
#define FRAME_HEADER_2      0x55
#define FRAME_FOOTER_1      0x0D
#define FRAME_FOOTER_2      0x0A
#define HEARTBEAT_FLAG      0xFF

// 数据格式
#define DATA_8_DIRECTIONS   32  // 8个float，每个4字节
#define DATA_NEAREST        6   // 2字节角度 + 4字节距离

// 8方向数据结构
typedef struct {
    float front;        // 前方
    float front_right;  // 右前
    float right;        // 右侧
    float back_right;   // 右后
    float back;         // 后方
    float back_left;    // 左后
    float left;         // 左侧
    float front_left;   // 左前
} Directions8_t;

// 最近障碍物数据结构
typedef struct {
    float angle;        // 角度 (度)
    float distance;     // 距离 (米)
} NearestObstacle_t;

// 接收状态机
typedef enum {
    STATE_WAIT_HEADER1,
    STATE_WAIT_HEADER2,
    STATE_WAIT_LENGTH,
    STATE_RECEIVE_DATA,
    STATE_RECEIVE_CHECKSUM,
    STATE_RECEIVE_FOOTER1,
    STATE_RECEIVE_FOOTER2
} ReceiveState_t;

// 接收缓冲区
static uint8_t rx_buffer[256];
static uint16_t rx_index = 0;
static uint8_t data_length = 0;
static ReceiveState_t rx_state = STATE_WAIT_HEADER1;

// 数据存储
static Directions8_t directions_data;
static NearestObstacle_t nearest_data;
static uint32_t packet_count = 0;
static uint32_t error_count = 0;

/**
 * 计算校验和
 */
static uint8_t calculate_checksum(const uint8_t *data, uint16_t length) {
    uint32_t sum = 0;
    for (uint16_t i = 0; i < length; i++) {
        sum += data[i];
    }
    return (uint8_t)(sum & 0xFF);
}

/**
 * 解析8方向数据
 */
static void parse_8_directions(const uint8_t *data) {
    // 注意：需要根据平台字节序调整
    float *distances = (float *)data;
    
    directions_data.front = distances[0];
    directions_data.front_right = distances[1];
    directions_data.right = distances[2];
    directions_data.back_right = distances[3];
    directions_data.back = distances[4];
    directions_data.back_left = distances[5];
    directions_data.left = distances[6];
    directions_data.front_left = distances[7];
    
    packet_count++;
    
    // 在这里添加你的处理逻辑
    // 例如：避障、路径规划等
}

/**
 * 解析最近障碍物数据
 */
static void parse_nearest_obstacle(const uint8_t *data) {
    uint16_t angle_raw = (uint16_t)(data[0] | (data[1] << 8)); /* 小端 uint16 */
    nearest_data.angle = angle_raw / 10.0f;

    /* 距离为 float 小端，与 Python struct.pack('<f', ...) 一致 */
    memcpy(&nearest_data.distance, &data[2], sizeof(float));

    packet_count++;
    
    // 在这里添加你的处理逻辑
}

/**
 * 处理心跳包
 */
static void handle_heartbeat(void) {
    // 心跳包处理
    // 可以用于检测通信是否正常
}

/**
 * 串口接收中断处理函数
 * 每接收到一个字节调用一次
 */
void uart_rx_callback(uint8_t byte) {
    switch (rx_state) {
        case STATE_WAIT_HEADER1:
            if (byte == FRAME_HEADER_1) {
                rx_state = STATE_WAIT_HEADER2;
            }
            break;
            
        case STATE_WAIT_HEADER2:
            if (byte == FRAME_HEADER_2) {
                rx_state = STATE_WAIT_LENGTH;
                rx_index = 0;
            } else {
                rx_state = STATE_WAIT_HEADER1;
            }
            break;
            
        case STATE_WAIT_LENGTH:
            data_length = byte;
            
            // 心跳包
            if (data_length == HEARTBEAT_FLAG) {
                rx_state = STATE_RECEIVE_DATA;  // 读取flag字节
            }
            // 8方向数据
            else if (data_length == DATA_8_DIRECTIONS) {
                rx_state = STATE_RECEIVE_DATA;
            }
            // 最近障碍物数据
            else if (data_length == DATA_NEAREST) {
                rx_state = STATE_RECEIVE_DATA;
            }
            // 未知数据
            else {
                rx_state = STATE_WAIT_HEADER1;
            }
            break;
            
        case STATE_RECEIVE_DATA:
            rx_buffer[rx_index++] = byte;
            
            // 心跳包只有1个字节
            if (data_length == HEARTBEAT_FLAG && rx_index >= 1) {
                rx_state = STATE_RECEIVE_CHECKSUM;
            }
            // 其他数据包
            else if (rx_index >= data_length) {
                rx_state = STATE_RECEIVE_CHECKSUM;
            }
            break;
            
        case STATE_RECEIVE_CHECKSUM: {
            /* 8方向/最近障碍: 与 Python sum(payload) & 0xFF 一致;
               心跳: 与 lidar_serial_bridge 的 sum([0xFF,0x00]) & 0xFF 一致 */
            uint8_t expected;
            if (data_length == HEARTBEAT_FLAG) {
                expected = (uint8_t)(HEARTBEAT_FLAG + rx_buffer[0]);
            } else {
                expected = calculate_checksum(rx_buffer, rx_index);
            }
            if (byte == expected) {
                rx_state = STATE_RECEIVE_FOOTER1;
            } else {
                error_count++;
                rx_state = STATE_WAIT_HEADER1;
            }
            break;
        }
            
        case STATE_RECEIVE_FOOTER1:
            if (byte == FRAME_FOOTER_1) {
                rx_state = STATE_RECEIVE_FOOTER2;
            } else {
                rx_state = STATE_WAIT_HEADER1;
            }
            break;
            
        case STATE_RECEIVE_FOOTER2:
            if (byte == FRAME_FOOTER_2) {
                // 完整数据包接收成功
                if (data_length == HEARTBEAT_FLAG) {
                    handle_heartbeat();
                } else if (data_length == DATA_8_DIRECTIONS) {
                    parse_8_directions(rx_buffer);
                } else if (data_length == DATA_NEAREST) {
                    parse_nearest_obstacle(rx_buffer);
                }
            }
            rx_state = STATE_WAIT_HEADER1;
            break;
    }
}

/**
 * 获取8方向数据
 */
void get_directions_data(Directions8_t *data) {
    *data = directions_data;
}

/**
 * 获取最近障碍物数据
 */
void get_nearest_obstacle(NearestObstacle_t *data) {
    *data = nearest_data;
}

/**
 * 获取统计信息
 */
void get_statistics(uint32_t *packets, uint32_t *errors) {
    *packets = packet_count;
    *errors = error_count;
}

/**
 * 示例：避障逻辑
 */
void obstacle_avoidance_example(void) {
    // 获取8方向数据
    Directions8_t dirs;
    get_directions_data(&dirs);
    
    // 定义安全距离 (米)
    const float SAFE_DISTANCE = 1.0f;
    
    // 检查各方向
    bool front_clear = dirs.front > SAFE_DISTANCE;
    bool left_clear = dirs.left > SAFE_DISTANCE;
    bool right_clear = dirs.right > SAFE_DISTANCE;
    
    // 简单避障逻辑
    if (!front_clear) {
        // 前方有障碍物
        if (left_clear && !right_clear) {
            // 向左转
        } else if (!left_clear && right_clear) {
            // 向右转
        } else if (left_clear && right_clear) {
            // 选择距离更远的方向
            if (dirs.left > dirs.right) {
                // 向左转
            } else {
                // 向右转
            }
        } else {
            // 停止或后退
        }
    }
}

/**
 * 主循环示例
 */
void main_loop(void) {
    while (1) {
        // 你的主循环代码
        
        // 定期调用避障逻辑
        obstacle_avoidance_example();
        
        // 延时
        // delay_ms(100);
    }
}
