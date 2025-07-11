from app.models.inout import ScheduleRequest, ScheduleResponse
from app.services.scheduler.greedy_scheduler import GreedyScheduler
from app.services.scheduler.ortools_scheduler import ORToolsScheduler


async def schedule(request: ScheduleRequest) -> ScheduleResponse:
    """Schedule trips for a given request"""
    if request.optimization:
        scheduler = ORToolsScheduler(request)
    else:
        scheduler = GreedyScheduler(request)

    return await scheduler.schedule()
