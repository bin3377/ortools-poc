import asyncio
import os
from datetime import datetime, timedelta
from typing import List

from dotenv import load_dotenv

from app.models.task import TaskCRUD, TaskStatus
from app.services.database import get_task_crud
from app.services.scheduler import schedule

load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "true") == "true"
PROCESSOR_INTERVAL = os.getenv("PROCESSOR_INTERVAL", "5000")  # Default: 5 seconds
PROCESSOR_BATCH_SIZE = int(os.getenv("PROCESSOR_BATCH_SIZE", "10"))  # Default: 10


class TaskProcessor:
    """Background task processor using asyncio"""

    def __init__(self):
        self.is_running = False
        self._task: asyncio.Task = None
        self._crud: TaskCRUD = None

    async def get_crud(self):
        if not self._crud:
            self._crud = await get_task_crud()
        return self._crud

    async def process_task(self, id: str):
        """
        Process a single task

        Args:
            id: Task ID

        Raises:
            Exception: If processing fails
        """
        print(f"📝 Processing task {id} ...")

        crud = await self.get_crud()

        task = await crud.get_task(id)

        if not task:
            raise Exception(f"cannot find task id {id}")

        try:
            print("  - Mark as processing...")
            await crud.update_task(id, TaskStatus.PROCESSING)

            # Run scheduler
            response = await schedule(task.request)

            # Write back success result
            print("  - Mark as completed...")
            await crud.update_task(
                id=id,
                status=TaskStatus.COMPLETED,
                response=response,
            )

        except Exception as error:
            # Write back error result
            error_message = str(error)
            print(f"  - Mark as failed: {error_message}")
            await crud.update_task(
                id=id,
                status=TaskStatus.FAILED,
                error_message=error_message,
            )
            raise error

    async def fetch_and_process_pending_tasks(self) -> List[str]:
        """
        Fetch pending tasks and process them

        Returns:
            List of processed task IDs
        """
        crud = await self.get_crud()

        # Get pending task IDs
        ids = await crud.get_pending_tasks(limit=PROCESSOR_BATCH_SIZE)

        if not ids:
            if DEBUG_MODE:
                next_time = datetime.now() + timedelta(
                    milliseconds=int(PROCESSOR_INTERVAL)
                )
                print(
                    f"⏳ No pending doc, next check will be {next_time.strftime('%H:%M:%S')}"
                )
            return []

        # Process tasks concurrently
        tasks = [self.process_task(str(doc_id)) for doc_id in ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log results
        processed_task_ids = []
        for i, result in enumerate(results):
            id = ids[i]
            if isinstance(result, Exception):
                print(f"❌ Processing task {id} failed: {result}")
            else:
                print(f"✅ Processing task {id} succeeded, task id: {result}")
                processed_task_ids.append(result)

        return processed_task_ids

    async def run_processor_loop(self):
        """Run the main processor loop"""
        print("⚙️  Processor start...")
        self.is_running = True

        while self.is_running:
            try:
                await self.fetch_and_process_pending_tasks()
            except Exception as e:
                print(f"❌ Error in processor loop: {e}")

            # Wait for next interval
            await asyncio.sleep(int(PROCESSOR_INTERVAL) / 1000)  # Convert ms to seconds

    def start(self):
        """Start the processor in the background"""
        if not self.is_running:
            self._task = asyncio.create_task(self.run_processor_loop())

    async def stop(self):
        """Stop the processor"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


# Global processor instance
_processor: TaskProcessor = None


def start_processor():
    """Start the global task processor"""
    global _processor
    if _processor is None:
        _processor = TaskProcessor()
        _processor.start()


async def stop_processor():
    """Stop the global task processor"""
    global _processor
    if _processor:
        await _processor.stop()
        _processor = None
