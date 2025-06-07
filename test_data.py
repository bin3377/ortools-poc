test_vehicles = [
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
    },
    {
        "id": "v2",
        "seats": {
            "regular": 8,
            "wheelchair": 1,
            "stretcher": 0
        },
        "hourly_rate": 80,
        "start_location": "北京市海淀区",
        "start_time": 7
    },
    {
        "id": "v3",
        "seats": {
            "regular": 15,
            "wheelchair": 3,
            "stretcher": 2
        },
        "hourly_rate": 150,
        "start_location": "北京市西城区",
        "start_time": 9
    }
]

test_bookings = [
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
    },
    {
        "id": "b2",
        "pickup_time": 10,
        "pickup_location": "北京市朝阳区",
        "dropoff_location": "北京市海淀区",
        "required_seats": {
            "regular": 4,
            "wheelchair": 0,
            "stretcher": 0
        },
        "unloading_time": 3
    },
    {
        "id": "b3",
        "pickup_time": 11,
        "pickup_location": "北京市西城区",
        "dropoff_location": "北京市朝阳区",
        "required_seats": {
            "regular": 1,
            "wheelchair": 0,
            "stretcher": 1
        },
        "unloading_time": 8
    },
    {
        "id": "b4",
        "pickup_time": 13,
        "pickup_location": "北京市海淀区",
        "dropoff_location": "北京市西城区",
        "required_seats": {
            "regular": 3,
            "wheelchair": 1,
            "stretcher": 0
        },
        "unloading_time": 4
    },
    {
        "id": "b5",
        "pickup_time": 14,
        "pickup_location": "北京市朝阳区",
        "dropoff_location": "北京市海淀区",
        "required_seats": {
            "regular": 6,
            "wheelchair": 0,
            "stretcher": 0
        },
        "unloading_time": 3
    }
]

# 测试数据说明：
# 1. 车辆信息：
#    - v1: 大型车辆，有担架座位，从朝阳区出发
#    - v2: 中型车辆，无担架座位，从海淀区出发
#    - v3: 特大型车辆，有多个担架座位，从西城区出发
#
# 2. 预订信息：
#    - b1: 需要轮椅座位的预订
#    - b2: 普通团体预订
#    - b3: 需要担架座位的预订
#    - b4: 需要轮椅座位的团体预订
#    - b5: 大型团体预订
#
# 3. 时间安排：
#    - 预订时间从9点到14点
#    - 卸载时间根据乘客类型不同而不同
#
# 4. 地点分布：
#    - 所有地点都在北京市内
#    - 形成了朝阳区、海淀区、西城区之间的循环路线 