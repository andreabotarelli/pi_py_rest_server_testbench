from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
import time
import math

class Servo:
    def __init__(
        self, 
        pin, 
        initial_angle,
        min_angle, 
        max_angle, 
        min_pulse_width, 
        max_pulse_width, 
        frame_width
        ):
        self._factory = PiGPIOFactory()
        self._initial_angle = initial_angle
        self._servo = AngularServo(
            pin,
            initial_angle=initial_angle,
            pin_factory=self._factory,
            min_angle=min_angle, 
            max_angle=max_angle,
            min_pulse_width=min_pulse_width,
            max_pulse_width=max_pulse_width,
            frame_width=frame_width
        )

    def set_angle(self, angle):
        if angle < self._servo.min_angle:
            angle = self._servo.min_angle
        elif angle > self._servo.max_angle:
            angle = self._servo.max_angle
        self._servo.angle = angle
    
    def set_angle_sweep(self, angle, duration, update_hz=200.0):
        target = max(self._servo.min_angle, min(self._servo.max_angle, angle))
        if duration <= 0 or abs(target - self._initial_angle) < 1e-6:
            self.set_angle(target)
            self._initial_angle = target
            return

        start_angle = self._initial_angle
        delta = target - start_angle

        min_step_deg = 0.2
        dt = 1.0 / update_hz
        t0 = time.monotonic()
        t_end = t0 + duration
        last_sent = start_angle

        while True:
            now = time.monotonic()
            # Break when RT duration is over
            if now >= t_end:
                break
            u = (now - t0) / duration
            # ease-in-out (cosine)
            # - Angle (s) follows a cosine curve from 0 to 1
            # - Velocity (v=ds/dt) follows a sine curve from 0 to 1 to 0
            # - Acceleration (a=dv/dt) follows a cosine curve from 1 to 0 to -1
            # - This provides slow accelleration and deceleration at the start and end of the movement
            e = 0.5 - 0.5 * math.cos(math.pi * u)
            a = start_angle + delta * e

            if abs(a - last_sent) >= min_step_deg:
                self.set_angle(a)
                last_sent = a

            sleep_time = dt - ((time.monotonic() - now) % dt)
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.set_angle(target)
        self._initial_angle = target

    def cleanup(self):
        self._servo.close()
        self._factory.close()


class ServoS90(Servo):
    # S90 specs: http://www.ee.ic.ac.uk/pcheung/teaching/DE1_EE/stores/sg90_datasheet.pdf
    # Nominal PWM specifies min 1ms max 2 ms pulse over 20 ms frame but the following value actually provides full 180° rotation
    def __init__(self, pin, initial_angle=0):
        super().__init__(
            pin=pin,
            initial_angle=initial_angle,
            min_angle=0,
            max_angle=180,
            min_pulse_width=500e-6,
            max_pulse_width=2250e-6,
            frame_width=20e-3
        )
