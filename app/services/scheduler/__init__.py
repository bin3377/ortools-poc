import os
from typing import List

from dotenv import load_dotenv

from app.models.inout import (
    ScheduleRequest,
    ScheduleResponse,
    ScheduleResult,
    ScheduleResultData,
    Shuttle,
)

load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "true") == "true"
DEFAULT_BEFORE_PICKUP_TIME = int(
    os.getenv("DEFAULT_BEFORE_PICKUP_TIME", "300")
)  # 5 minutes
DEFAULT_AFTER_PICKUP_TIME = int(
    os.getenv("DEFAULT_AFTER_PICKUP_TIME", "300")
)  # 5 minutes
DEFAULT_DROPOFF_UNLOADING_TIME = int(
    os.getenv("DEFAULT_DROPOFF_UNLOADING_TIME", "300")
)  # 5 minutes


class SchedulerContext:
    """Scheduler context containing configuration and request data"""

    def __init__(self, request: ScheduleRequest):
        self.request = request

    def date_str(self) -> str:
        return self.request.date

    def is_debug(self) -> bool:
        return self.request.debug or DEBUG_MODE

    def debug(self, *args):
        if self.is_debug():
            for arg in args:
                if isinstance(arg, str):
                    for line in arg.split("\n"):
                        print("DEBUG:", line)
                else:
                    print("DEBUG:", arg)

    def assert_condition(self, condition: bool, message: str):
        if not condition:
            print("ERROR:", message)
            if self.is_debug():
                raise AssertionError(message)

    def before_pickup_in_sec(self) -> int:
        """Driver can arrive earlier for outgoing trip (in seconds)"""
        return self.request.before_pickup_time or DEFAULT_BEFORE_PICKUP_TIME

    def after_pickup_in_sec(self) -> int:
        """Driver can arrive later for returning trip (in seconds)"""
        return self.request.after_pickup_time or DEFAULT_AFTER_PICKUP_TIME

    def dropoff_unloading_in_sec(self) -> int:
        """Extra time for dropoff unloading (in seconds)"""
        return self.request.dropoff_unloading_time or DEFAULT_DROPOFF_UNLOADING_TIME


class Scheduler:
    """Base class for scheduler"""

    def __init__(self, request: ScheduleRequest):
        self.request = request
        self.context = SchedulerContext(request)

    async def schedule(self) -> ScheduleResponse:
        """Schedule trips for a given request"""

        shuttles = await self._calculate()
        # Debug output
        self.context.debug(self._get_text_plan(shuttles))

        return self._get_response(shuttles)

    async def _calculate(self) -> List[Shuttle]:
        pass

    def _get_text_plan(self, shuttles: List[Shuttle]) -> str:
        """Generate text representation of the plan for debugging"""
        lines = [
            "=================================================",
            f" Plan of {self.context.date_str()}",
            f" Total shuttles: {len(shuttles)}",
            "======================BEGIN======================",
        ]

        for shuttle in shuttles:
            lines.append(shuttle.short())

        lines.append("=======================END=======================")
        return "\n".join(lines)

    def _get_response(self, shuttles: List[Shuttle]) -> ScheduleResponse:
        """Generate the final response"""

        return ScheduleResponse(
            result=ScheduleResult(
                error_code=0,
                message="Successfully retrieved trips data.",
                status="success",
                data=ScheduleResultData(vehicle_trip_list=shuttles),
            )
        )
