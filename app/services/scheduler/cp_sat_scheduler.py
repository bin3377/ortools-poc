from datetime import datetime
from typing import List

from dotenv import load_dotenv
from ortools.sat.python import cp_model

from app.models.inout import Optimization
from app.models.program import Vehicle
from app.services.database import get_program_crud
from app.services.direction import get_direction
from app.services.scheduler import Scheduler, Shuttle

load_dotenv()


class CpSatScheduler(Scheduler):
    _crud = None

    def _time_to_minutes(self, time: datetime) -> int:
        return time.hour * 60 + time.minute

    async def _get_crud(self):
        if not self._crud:
            self._crud = await get_program_crud()
        return self._crud

    async def _get_vehicles(self) -> List[Vehicle]:
        program_name = self.request.program_name
        if not program_name:
            for booking in self.request.bookings:
                program_name = booking.program_name
                break

        if not program_name:
            self.context.debug("No program name found")
            return []

        crud = await self._get_crud()
        program = await crud.get_program_by_name(program_name)
        if not program:
            self.context.debug("Program not found")
            return []

        self.context.debug(
            f"Found program {program_name} with {len(program.vehicles)} vehicles"
        )
        return program.vehicles

    async def _calculate(self) -> List[Shuttle]:
        vehicles = await self._get_vehicles()
        trips = await self._get_trips_from_bookings(self.request.bookings)
        optimization = self.request.optimization or Optimization()

        model = cp_model.CpModel()

        num_vehicles = len(vehicles)
        num_trips = len(trips)

        # boolvar x[i][j] means vehicle i is assigned to trip j
        x = {}
        for i in range(num_vehicles):
            for j in range(num_trips):
                x[i, j] = model.NewBoolVar(f"x_{i}_{j}")

        # boolvar vehicle_used[i] means vehicle i is used
        vehicle_used = {}
        for i in range(num_vehicles):
            vehicle_used[i] = model.NewBoolVar(f"vehicle_used_{i}")

        # intvar t[i][j] means vehicle i starts trip j at time t[i][j]
        t = {}
        for i in range(num_vehicles):
            for j in range(num_trips):
                t[i, j] = model.NewIntVar(0, 24 * 60, f"t_{i}_{j}")

        # constraint 1: each trip is assigned to exactly one vehicle
        for j in range(num_trips):
            model.Add(sum(x[i, j] for i in range(num_vehicles)) == 1)

        # constraint 2: mark vehicle used if assigned to any trip
        for i in range(num_vehicles):
            for j in range(num_trips):
                model.Add(vehicle_used[i] >= x[i, j])

        # constraint 3: mobility assistance compatibility
        for i in range(num_vehicles):
            for j in range(num_trips):
                model.Add(
                    vehicles[i].assistance.compatible(trips[j].assistance)
                ).OnlyEnforceIf(x[i, j])

        # constraint 4: time window
        for i in range(num_vehicles):
            for j in range(num_trips):
                # if vehicle i is assigned to trip j, then the start time must be within the pickup time window
                pickup_time = self._time_to_minutes(trips[j].pickup_time)
                model.Add(t[i, j] <= pickup_time).OnlyEnforceIf(x[i, j])

        # constraint 5: connection between trips
        for i in range(num_vehicles):
            for j1 in range(num_trips):
                for j2 in range(num_trips):
                    if j1 != j2:
                        finish_time_j1 = self._time_to_minutes(trips[j1].finish_time())
                        pickup_time_j2 = self._time_to_minutes(
                            trips[j2].latest_pickup_time()
                        )

                        # If trip j2 starts after trip j1 finishes, allow time for connection
                        if pickup_time_j2 > finish_time_j1:
                            direction = await get_direction(
                                trips[j1].dropoff_address, trips[j2].pickup_address
                            )
                            if direction:
                                service_time = (
                                    trips[j1].duration_in_sec
                                    + direction.duration_in_sec
                                ) // 60
                                model.Add(
                                    t[i, j2] >= t[i, j1] + service_time
                                ).OnlyEnforceIf([x[i, j1], x[i, j2]])

        if optimization.chain_bookings_for_same_pessenger:
            # constraint 6: optional - chain bookings for the same passenger
            for i in range(num_vehicles):
                for j1 in range(num_trips):
                    for j2 in range(num_trips):
                        if j1 != j2 and trips[j1].passenger == trips[j2].passenger:
                            model.Add(x[i, j1] == x[i, j2])

        # objective function
        if optimization.minimize_vehicles:
            # minimize the number of vehicles used
            model.Minimize(sum(vehicle_used[i] for i in range(num_vehicles)))
        elif optimization.minimize_total_duration:
            # minimize the total duration of all trips
            objective_terms = []
            for i in range(num_vehicles):
                first_start_time = int.max
                last_finish_time = 0
                for j in range(num_trips):
                    if x[i, j]:
                        first_start_time = min(
                            first_start_time,
                            self._time_to_minutes(trips[j].pickup_time),
                        )
                        last_finish_time = max(
                            last_finish_time,
                            self._time_to_minutes(trips[j].finish_time()),
                        )
                if first_start_time == int.max:
                    continue
                duration = last_finish_time - first_start_time
                objective_terms.append(duration)
            model.Minimize(sum(objective_terms))
        else:
            model.Minimize(sum(vehicle_used[i] for i in range(num_vehicles)))

        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            self.context.debug("Solution found, Status:", status)

            shuttles: List[Shuttle] = []
            total_vehicles_used = 0

            for i in range(num_vehicles):
                if solver.Value(vehicle_used[i]) == 1:
                    total_vehicles_used += 1

                    shuttle = Shuttle(
                        shuttle_name=vehicles[i].name,
                        trips=[],
                    )
                    shuttles.append(shuttle)

                    for j in range(num_trips):
                        if solver.Value(x[i, j]) == 1:
                            shuttle.trips.append(trips[j].to_trip())

                    if shuttle.trips:
                        # Sort trips by pickup time
                        shuttle.trips.sort(key=lambda x: x.pickup_time)
                        self.context.debug(
                            f"  {shuttle.shuttle_name}: {len(shuttle.trips)} trips"
                        )

            return shuttles
        else:
            raise ValueError(f"No feasible solution found, Status: {status}")
