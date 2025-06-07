# Vehicle Scheduling System

这是一个使用Google OR-Tools实现的车辆调度系统，可以优化车辆排班方案，最小化运营成本。

## 功能特点

- 支持多种座位类型（普通座位、轮椅座位、担架座位）
- 考虑车辆容量限制
- 考虑时间窗口约束
- 考虑行程衔接
- 使用Google Maps API计算实际距离和行程时间
- 提供RESTful API接口

## 安装

1. 克隆仓库：
```bash
git clone <repository-url>
cd vehicle-scheduling-system
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 创建.env文件并添加Google Maps API密钥：
```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

## 运行

启动服务器：
```bash
python main.py
```

服务器将在 http://localhost:8000 运行。

## API使用

### 创建调度方案

**端点**: POST /schedule

**请求体示例**:
```json
{
  "vehicles": [
    {
      "id": "v1",
      "seats": {
        "regular": 10,
        "wheelchair": 2,
        "stretcher": 1
      },
      "hourly_rate": 100,
      "start_location": "北京市朝阳区",
      "start_time": 8
    }
  ],
  "bookings": [
    {
      "id": "b1",
      "pickup_time": 9,
      "pickup_location": "北京市海淀区",
      "dropoff_location": "北京市西城区",
      "required_seats": {
        "regular": 2,
        "wheelchair": 1,
        "stretcher": 0
      },
      "unloading_time": 5
    }
  ]
}
```

**响应示例**:
```json
{
  "schedules": [
    {
      "vehicle_id": "v1",
      "bookings": [
        {
          "booking_id": "b1",
          "start_time": 8,
          "pickup_location": "北京市海淀区",
          "dropoff_location": "北京市西城区"
        }
      ]
    }
  ],
  "total_cost": 150.5
}
```

## 注意事项

1. 确保有有效的Google Maps API密钥
2. 所有时间使用24小时制
3. 距离和时间计算基于实际道路情况
4. 系统会自动缓存距离和时间计算结果以提高性能 