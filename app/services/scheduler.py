from dotenv import load_dotenv

from app.models.inout import ScheduleRequest, ScheduleResponse
from app.services.greedy_scheduler import Scheduler

load_dotenv()


async def schedule(request: ScheduleRequest) -> ScheduleResponse:
    """Schedule trips for a given request"""
    scheduler = Scheduler(request)
    return await scheduler.calculate()
