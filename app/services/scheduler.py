import math
import os
from typing import Any, Dict, List, Optional

import googlemaps
from dotenv import load_dotenv
from ortools.sat.python import cp_model

from app.models.schedule import ScheduleRequest, ScheduleResponse

load_dotenv()


async def schedule(request: ScheduleRequest) -> ScheduleResponse:
    pass


class VehicleScheduler:
    def __init__(self):
        self.gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))
        self.distance_cache = {}
        self.duration_cache = {}

    def _time_to_minutes(self, time_str: str) -> int:
        """将时间字符串转换为分钟数"""
        try:
            hour, minute = map(int, time_str.split(":"))
            return hour * 60 + minute
        except Exception:
            return 0

    def _minutes_to_time(self, minutes: int) -> str:
        """将分钟数转换为时间字符串"""
        hour = minutes // 60
        minute = minutes % 60
        return f"{hour:02d}:{minute:02d}"

    def _check_mobility_compatibility(
        self, vehicle_seat_types: Dict, mobility_assistance: List[str]
    ) -> bool:
        """检查车辆座位类型是否支持乘客的移动辅助需求"""
        for assistance in mobility_assistance:
            assistance_lower = assistance.lower()
            if assistance_lower == "wheelchair" and not vehicle_seat_types.get(
                "wheelchair", False
            ):
                return False
            elif assistance_lower in [
                "cane or walker",
                "cane",
                "walker",
            ] and not vehicle_seat_types.get("cane_walker", False):
                return False
            elif assistance_lower == "stretcher" and not vehicle_seat_types.get(
                "stretcher", False
            ):
                return False
            # 对于"ambulatory"（行走正常），所有车辆都支持
        return True

    def get_distance_and_duration(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> tuple:
        """使用经纬度获取距离和时长"""
        cache_key = f"{origin_lat}_{origin_lng}_{dest_lat}_{dest_lng}"
        if cache_key in self.distance_cache:
            return self.distance_cache[cache_key], self.duration_cache[cache_key]

        try:
            origin = f"{origin_lat},{origin_lng}"
            destination = f"{dest_lat},{dest_lng}"
            result = self.gmaps.distance_matrix(origin, destination, mode="driving")
            distance = (
                result["rows"][0]["elements"][0]["distance"]["value"] / 1000
            )  # 转换为公里
            duration = math.ceil(
                result["rows"][0]["elements"][0]["duration"]["value"] / 60
            )  # 转换为分钟
            self.distance_cache[cache_key] = distance
            self.duration_cache[cache_key] = duration
            return distance, duration
        except Exception:
            # 如果API调用失败，使用简单的欧几里得距离估算
            distance = (
                math.sqrt((dest_lat - origin_lat) ** 2 + (dest_lng - origin_lng) ** 2)
                * 111
            )  # 大约转换为公里
            duration = max(5, int(distance * 2))  # 简单估算：每公里2分钟
            return distance, duration

    def schedule(
        self,
        vehicles: List[Dict],
        bookings: List[Dict],
        objective: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        # 处理输入数据（可能是Pydantic模型或字典）
        vehicles_dict = []
        for vehicle in vehicles:
            if hasattr(vehicle, "dict"):
                vehicles_dict.append(vehicle.dict())
            else:
                vehicles_dict.append(vehicle)

        bookings_dict = []
        for booking in bookings:
            if hasattr(booking, "dict"):
                bookings_dict.append(booking.dict())
            else:
                bookings_dict.append(booking)

        if objective is None:
            objective = {
                "minimize_vehicles": True,
                "minimize_cost": False,
                "minimize_time": False,
            }

        model = cp_model.CpModel()

        # 创建变量
        num_vehicles = len(vehicles_dict)
        num_bookings = len(bookings_dict)

        # 创建决策变量：x[i][j] 表示车辆i是否执行预订j
        x = {}
        for i in range(num_vehicles):
            for j in range(num_bookings):
                x[i, j] = model.NewBoolVar(f"x_{i}_{j}")

        # 创建车辆使用变量：vehicle_used[i] 表示车辆i是否被使用
        vehicle_used = {}
        for i in range(num_vehicles):
            vehicle_used[i] = model.NewBoolVar(f"vehicle_used_{i}")

        # 创建时间变量：t[i][j] 表示车辆i开始执行预订j的时间
        t = {}
        for i in range(num_vehicles):
            for j in range(num_bookings):
                t[i, j] = model.NewIntVar(0, 24 * 60, f"t_{i}_{j}")

        # 约束1：每个预订必须被一辆车执行
        for j in range(num_bookings):
            model.Add(sum(x[i, j] for i in range(num_vehicles)) == 1)

        # 约束2：车辆使用标记
        for i in range(num_vehicles):
            # 如果车辆i执行任何预订，则标记为使用
            for j in range(num_bookings):
                model.Add(vehicle_used[i] >= x[i, j])

        # 约束3：座位容量和移动辅助约束
        for i in range(num_vehicles):
            for j in range(num_bookings):
                # 座位数量约束
                model.Add(
                    vehicles_dict[i]["total_seats"]
                    >= bookings_dict[j]["total_seat_count"]
                ).OnlyEnforceIf(x[i, j])

                # 移动辅助兼容性约束
                mobility_compatible = self._check_mobility_compatibility(
                    vehicles_dict[i]["seat_types"],
                    bookings_dict[j]["mobility_assistance"],
                )
                if not mobility_compatible:
                    model.Add(x[i, j] == 0)

        # 约束4：时间约束
        for i in range(num_vehicles):
            for j in range(num_bookings):
                # 如果车辆i执行预订j，则车辆开始执行时间应该在预订时间之前
                pickup_time = self._time_to_minutes(bookings_dict[j]["pickup_time"])
                start_time = self._time_to_minutes(vehicles_dict[i]["start_time"])

                # 车辆必须在预订时间之前或同时到达
                model.Add(t[i, j] <= pickup_time).OnlyEnforceIf(x[i, j])
                # 车辆不能在自己的开始时间之前工作
                model.Add(t[i, j] >= start_time).OnlyEnforceIf(x[i, j])

        # 约束6：行程衔接约束（简化版本）
        for i in range(num_vehicles):
            for j1 in range(num_bookings):
                for j2 in range(num_bookings):
                    if j1 != j2:
                        # 简单的时间间隔约束，避免复杂的距离计算
                        pickup_time_j1 = self._time_to_minutes(
                            bookings_dict[j1]["pickup_time"]
                        )
                        pickup_time_j2 = self._time_to_minutes(
                            bookings_dict[j2]["pickup_time"]
                        )

                        # 如果两个预订时间很接近，确保有足够的间隔
                        if abs(pickup_time_j1 - pickup_time_j2) < 30:  # 30分钟内
                            service_time = 20  # 至少20分钟间隔
                            if pickup_time_j1 < pickup_time_j2:
                                model.Add(
                                    t[i, j2] >= t[i, j1] + service_time
                                ).OnlyEnforceIf([x[i, j1], x[i, j2]])

        # 目标函数：根据配置选择优化目标
        if objective.get("minimize_vehicles", True):
            # 默认目标：最小化使用的车辆数量
            model.Minimize(sum(vehicle_used[i] for i in range(num_vehicles)))
        elif objective.get("minimize_time", False):
            # 最小化总行程时间
            objective_terms = []
            for i in range(num_vehicles):
                for j in range(num_bookings):
                    _, duration = self.get_distance_and_duration(
                        bookings_dict[j]["pickup_latitude"],
                        bookings_dict[j]["pickup_longitude"],
                        bookings_dict[j]["dropoff_latitude"],
                        bookings_dict[j]["dropoff_longitude"],
                    )
                    objective_terms.append(duration * x[i, j])
            model.Minimize(sum(objective_terms))
        else:
            # 如果没有明确目标，默认最小化车辆数量
            model.Minimize(sum(vehicle_used[i] for i in range(num_vehicles)))

        # 求解
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # 构建结果
            schedules = []
            total_vehicles_used = 0
            total_passengers = 0

            for i in range(num_vehicles):
                if solver.Value(vehicle_used[i]) == 1:
                    total_vehicles_used += 1
                    vehicle_schedule = {
                        "vehicle_id": vehicles_dict[i]["id"],
                        "bookings": [],
                        "total_passengers": 0,
                    }

                    for j in range(num_bookings):
                        if solver.Value(x[i, j]) == 1:
                            vehicle_schedule["bookings"].append(
                                {
                                    "booking_id": bookings_dict[j]["booking_id"],
                                    "pickup_time": self._minutes_to_time(
                                        solver.Value(t[i, j])
                                    ),
                                    "pickup_address": bookings_dict[j][
                                        "pickup_address"
                                    ],
                                    "dropoff_address": bookings_dict[j][
                                        "dropoff_address"
                                    ],
                                    "passenger_count": bookings_dict[j][
                                        "total_seat_count"
                                    ],
                                }
                            )
                            vehicle_schedule["total_passengers"] += bookings_dict[j][
                                "total_seat_count"
                            ]
                            total_passengers += bookings_dict[j]["total_seat_count"]

                    if vehicle_schedule["bookings"]:
                        # 按时间排序预订
                        vehicle_schedule["bookings"].sort(
                            key=lambda x: x["pickup_time"]
                        )
                        schedules.append(vehicle_schedule)

            return {
                "schedules": schedules,
                "total_vehicles_used": total_vehicles_used,
                "total_passengers": total_passengers,
                "error": None,
            }
        else:
            return {
                "schedules": [],
                "total_vehicles_used": 0,
                "total_passengers": 0,
                "error": "No feasible solution found",
            }
