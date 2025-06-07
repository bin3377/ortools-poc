from ortools.sat.python import cp_model
import googlemaps
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
import math

load_dotenv()

class VehicleScheduler:
    def __init__(self):
        self.gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
        self.distance_cache = {}
        self.duration_cache = {}

    def get_distance_and_duration(self, origin: str, destination: str) -> tuple:
        cache_key = f"{origin}_{destination}"
        if cache_key in self.distance_cache:
            return self.distance_cache[cache_key], self.duration_cache[cache_key]

        try:
            result = self.gmaps.distance_matrix(origin, destination, mode="driving")
            distance = result['rows'][0]['elements'][0]['distance']['value'] / 1000  # 转换为公里
            duration = math.ceil(result['rows'][0]['elements'][0]['duration']['value'] / 60)  # 转换为分钟
            self.distance_cache[cache_key] = distance
            self.duration_cache[cache_key] = duration
            return distance, duration
        except Exception as e:
            raise Exception(f"Error getting distance/duration: {str(e)}")

    def schedule(self, vehicles: List[Dict], bookings: List[Dict]) -> Dict[str, Any]:
        # 将Pydantic模型转换为字典
        vehicles_dict = [vehicle.dict() for vehicle in vehicles]
        bookings_dict = [booking.dict() for booking in bookings]

        model = cp_model.CpModel()
        
        # 创建变量
        num_vehicles = len(vehicles_dict)
        num_bookings = len(bookings_dict)
        
        # 创建决策变量：x[i][j] 表示车辆i是否执行预订j
        x = {}
        for i in range(num_vehicles):
            for j in range(num_bookings):
                x[i, j] = model.NewBoolVar(f'x_{i}_{j}')

        # 创建时间变量：t[i][j] 表示车辆i开始执行预订j的时间
        t = {}
        for i in range(num_vehicles):
            for j in range(num_bookings):
                t[i, j] = model.NewIntVar(0, 24 * 60, f't_{i}_{j}')

        # 约束1：每个预订必须被一辆车执行
        for j in range(num_bookings):
            model.Add(sum(x[i, j] for i in range(num_vehicles)) == 1)

        # 约束2：座位容量约束
        for i in range(num_vehicles):
            for j in range(num_bookings):
                # 如果车辆i执行预订j，则必须满足座位要求
                model.Add(vehicles_dict[i]['seats']['regular'] >= bookings_dict[j]['required_seats']['regular']).OnlyEnforceIf(x[i, j])
                model.Add(vehicles_dict[i]['seats']['wheelchair'] >= bookings_dict[j]['required_seats']['wheelchair']).OnlyEnforceIf(x[i, j])
                model.Add(vehicles_dict[i]['seats']['stretcher'] >= bookings_dict[j]['required_seats']['stretcher']).OnlyEnforceIf(x[i, j])

        # 约束3：时间约束
        for i in range(num_vehicles):
            for j in range(num_bookings):
                # 如果车辆i执行预订j，则必须满足时间要求
                pickup_time = bookings_dict[j]['pickup_time'] * 60  # 转换为分钟
                model.Add(t[i, j] <= pickup_time).OnlyEnforceIf(x[i, j])

        # 约束4：车辆可用性约束
        for i in range(num_vehicles):
            for j in range(num_bookings):
                start_time = vehicles_dict[i]['start_time'] * 60  # 转换为分钟
                model.Add(t[i, j] >= start_time).OnlyEnforceIf(x[i, j])

        # 约束5：行程衔接约束
        for i in range(num_vehicles):
            for j1 in range(num_bookings):
                for j2 in range(num_bookings):
                    if j1 != j2:
                        # 如果车辆i执行预订j1和j2，则必须满足时间衔接
                        duration, _ = self.get_distance_and_duration(
                            bookings_dict[j1]['dropoff_location'],
                            bookings_dict[j2]['pickup_location']
                        )
                        # 将浮点数转换为整数（分钟）
                        duration_minutes = math.ceil(duration * 60)
                        model.Add(
                            t[i, j2] >= t[i, j1] + duration_minutes + bookings_dict[j1]['unloading_time']
                        ).OnlyEnforceIf(x[i, j1], x[i, j2])

        # 目标函数：最小化总成本
        objective_terms = []
        for i in range(num_vehicles):
            for j in range(num_bookings):
                duration, _ = self.get_distance_and_duration(
                    bookings_dict[j]['pickup_location'],
                    bookings_dict[j]['dropoff_location']
                )
                # 将浮点数转换为整数（分钟）
                duration_minutes = math.ceil(duration * 60)
                # 计算成本（转换为整数，以分为单位）
                cost = math.ceil((duration_minutes / 60) * vehicles_dict[i]['hourly_rate'] * 100)
                objective_terms.append(cost * x[i, j])

        model.Minimize(sum(objective_terms))

        # 求解
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # 构建结果
            schedules = []
            total_cost = 0

            for i in range(num_vehicles):
                vehicle_schedule = {
                    'vehicle_id': vehicles_dict[i]['id'],
                    'bookings': []
                }
                
                for j in range(num_bookings):
                    if solver.Value(x[i, j]) == 1:
                        vehicle_schedule['bookings'].append({
                            'booking_id': bookings_dict[j]['id'],
                            'start_time': solver.Value(t[i, j]) // 60,  # 转换回小时
                            'pickup_location': bookings_dict[j]['pickup_location'],
                            'dropoff_location': bookings_dict[j]['dropoff_location']
                        })
                        duration, _ = self.get_distance_and_duration(
                            bookings_dict[j]['pickup_location'],
                            bookings_dict[j]['dropoff_location']
                        )
                        total_cost += (duration / 60) * vehicles_dict[i]['hourly_rate']

                if vehicle_schedule['bookings']:
                    schedules.append(vehicle_schedule)

            return {
                'schedules': schedules,
                'total_cost': total_cost,
                'error': None
            }
        else:
            return {
                'schedules': [],
                'total_cost': 0,
                'error': 'No feasible solution found'
            } 