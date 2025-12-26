import asyncio
import threading
from concurrent.futures import Future
from typing import Optional, Callable, Awaitable, Union
import contextlib
import logging
import inspect

WorkType = Union[Callable[[], None], Callable[[], Awaitable[None]]]

class AsyncWorker:
    def __init__(self, work: WorkType, interval: float = 1.0):
        self._work = work
        self._interval = interval
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_evt: Optional[asyncio.Event] = None
        self._task: Optional[asyncio.Task] = None
        self._started = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop_thread, name="async-worker-loop", daemon=True
        )
        self._thread.start()
        self._started.wait()

    def stop(self) -> None:
        if not self._loop or not self._thread:
            return
        # Schedula la set() nel loop (thread-safe)
        if self._stop_evt:
            self._loop.call_soon_threadsafe(self._stop_evt.set)
        # Cancella il task principale
        if self._task:
            self._task.cancel()
        # Ferma il loop
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        try:
            self._loop.close()
        finally:
            self._loop = None
            self._thread = None
            self._stop_evt = None
            self._task = None
            self._started.clear()

    def submit(self, coro_factory: Callable[[], Awaitable]):
        if not self._loop:
            raise RuntimeError("Loop not started.")
        return asyncio.run_coroutine_threadsafe(coro_factory(), self._loop)

    def _loop_thread(self):
        assert self._loop is not None
        asyncio.set_event_loop(self._loop)
        self._stop_evt = asyncio.Event()
        self._task = self._loop.create_task(self._run(), name="worker-task")
        self._started.set()
        try:
            self._loop.run_forever()
        finally:
            if self._task and not self._task.done():
                self._loop.run_until_complete(self._cancel_safely(self._task))

    async def _cancel_safely(self, task: asyncio.Task):
        try:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        except Exception:
            logging.exception("Error cancelling task")

    async def _run(self):
        try:
            while not self._stop_evt.is_set():
                try:
                    if self._work:
                        if inspect.iscoroutinefunction(self._work):
                            await self._work()  # async work
                        else:
                            # sync work -> executor
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(None, self._work)
                except Exception:
                    logging.exception("AsyncWorker work() raised")
                try:
                    await asyncio.wait_for(self._stop_evt.wait(), timeout=self._interval)
                except asyncio.TimeoutError:
                    pass
            print("Worker stopping.")
        except asyncio.CancelledError:
            logging.debug("Task cancelled.")
            raise
        finally:
            logging.debug("Task closed.")
