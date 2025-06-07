from scheduler import VehicleScheduler
from test_data import test_vehicles, test_bookings
import json

def test_scheduling():
    scheduler = VehicleScheduler()
    result = scheduler.schedule(test_vehicles, test_bookings)
    
    # 打印结果
    print("\n调度结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 分析结果
    if result.get('error'):
        print(f"\n错误: {result['error']}")
    else:
        print("\n调度分析:")
        print(f"总成本: {result['total_cost']} 元")
        print("\n车辆分配情况:")
        for schedule in result['schedules']:
            print(f"\n车辆 {schedule['vehicle_id']} 的行程:")
            for booking in schedule['bookings']:
                print(f"  - 预订 {booking['booking_id']}:")
                print(f"    开始时间: {booking['start_time']}:00")
                print(f"    起点: {booking['pickup_location']}")
                print(f"    终点: {booking['dropoff_location']}")

if __name__ == "__main__":
    test_scheduling() 