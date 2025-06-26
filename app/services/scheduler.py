from dotenv import load_dotenv

from app.models.task import ScheduleRequest, ScheduleResponse

load_dotenv()


async def schedule(request: ScheduleRequest) -> ScheduleResponse:
    pass
