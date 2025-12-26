import asyncio
from gpiozero import DistanceSensor
from gpiozero.pins.pigpio import PiGPIOFactory
import logging
from async_worker import AsyncWorker

MIN_WAIT_INTERVAL_s = 0.3

class DistanceMonitor:
    def __init__(self, echo_pin=24, trigger_pin=23, interval=MIN_WAIT_INTERVAL_s):
        self._sensor = DistanceSensor(
            echo=echo_pin, 
            trigger=trigger_pin, 
            pin_factory=PiGPIOFactory()
            )
        self._task: asyncio.Task | None = None
        self._stop_evt = asyncio.Event()
        self._interval = interval
        self._worker = AsyncWorker(
            work=self.print_distance_cm,
            interval=self._interval
        )

    def print_distance_cm(self):
        logging.info(f"Distance: {self.get_distance_cm()} cm")

    def get_distance_cm(self) -> float:
        return self._sensor.distance * 100

    def close(self):
        self._sensor.close()
    
    def monitor_start(self):
        self._worker.start()

    def monitor_stop(self):
        self._worker.stop()
