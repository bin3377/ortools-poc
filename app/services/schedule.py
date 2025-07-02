from app.models.inout import ScheduleRequest, ScheduleResponse
from app.services.scheduler.greedy_scheduler import GreedyScheduler


async def schedule(request: ScheduleRequest) -> ScheduleResponse:
    """Schedule trips for a given request"""
    if request.ortools:
        pass

    scheduler = GreedyScheduler(request)
    return await scheduler.schedule()
