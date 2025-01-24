import os
import time

from msl.equipment import (
    EquipmentRecord,
    ConnectionRecord,
    Backend,
)
from msl.equipment.resources.thorlabs import MotionControl


# Custom modules:
from _surface_scattering_scan import scan_1d, scan_3d


# Class representing the motor hardware
class Motor:
    def __init__(self, parent, motor_id, polling_rate=200):
        self.motor_id = motor_id
        self._parent = parent
        self._position_device_unit = None
        self._position_real_unit = None
        self._polling_rate = polling_rate
        self._controller = parent.connectedController

    def _wait(self, value: int):
        self._controller.clear_message_queue(self.motor_id)
        message_type, message_id, _ = self._controller.wait_for_message(self.motor_id)
        while message_type != 2 or message_id != value:
            position = self.get_position()
            print(f"At position {position[0]} [device units] {position[1]} [real-world units]")
            message_type, message_id, _ = self._controller.wait_for_message(self.motor_id)

    # ---------------------------------------------------------------------------    Wrappers for controlling the motors
    def _load_settings(self):
        if self._parent is not None:
            self._controller.load_settings(self.motor_id)
            print("Motor setting loaded.")
            time.sleep(2)  # TODO Check if delay is necessary and how long
        else:
            print("Not connected to controller.")

    def _start_polling(self, rate=200):
        if self._parent is not None:
            self._controller.start_polling(self.motor_id, rate)
            print("Polling started...")
        else:
            print("Not connected to controller.")

    def _stop_polling(self):
        if self._parent is not None:
            self._controller.stop_polling(self.motor_id)
            print("Polling stopped.")
        else:
            print("Not connected to controller.")

    def get_position(self):
        self._position_device_unit = self._controller.get_position(self.motor_id)
        self._position_real_unit = self._controller.get_real_value_from_device_unit(
            self.motor_id, self._position_device_unit, "DISTANCE")
        print(f"At position: {self._position_device_unit} [device units], {self._position_real_unit} [real units]")
        return self._position_device_unit, self._position_real_unit

    def home(self):
        if self._parent is not None:
            self._load_settings()
            self._start_polling(rate=self._polling_rate)

            print("Initial position:")
            self.get_position()
            print("Homing parameters:")
            print(self._controller.is_calibration_active(self.motor_id))
            # TODO Add limit checking and direction change based on position
            self._controller.home(self.motor_id)
            print(f"Homing motor {self.motor_id}...")
            self._wait(0)
            time.sleep(1)
            self.get_position()
            self._stop_polling()
            print(f"Finishing homing motor {self.motor_id}...")
        else:
            print("Not connected to controller.")
    # ------------------------------------------------------------------------------------------------------------------

    def move_to_position(self, position):
        self._load_settings()
        time.sleep(1)  # TODO find if necessary
        self._start_polling()
        position_in_device_unit = self._controller.get_device_unit_from_real_value(self.motor_id, position, "DISTANCE")
        # TODO Add limit checking and direction change based on position
        self._controller.move_to_position(self.motor_id, position_in_device_unit)
        self._wait(1)  # TODO find if necessary
        self._stop_polling()

    def stop(self):
        # TODO: check if stop_immediate(self, channel) is better
        self._controller.stop_profiled(self.motor_id)


# Class representing the motor controller hardware
class MotorController:
    def __init__(self, manufacturer: str, model: str, serial: str, address: str, backend: Backend):
        # ensure that the Kinesis folder is available on PATH
        os.environ["PATH"] += os.pathsep + "C:/Program Files/Thorlabs/Kinesis"

        # Model parameters
        self._manufacturer = manufacturer
        self._model = model
        self._serial = serial
        self._address = address
        self._backend = backend
        self._record = EquipmentRecord(
            manufacturer=self._manufacturer, model=self._model,  # update for your device
            serial=self._serial,  # update for your device
            connection=ConnectionRecord(address=self._address, backend=self._backend))
        self.connectedController = None
        self.channels = []  # List of available channels
        self.motors = [None]  # List of available motors - motors are indexed from 1, so let 0 index be None, so the
        # first motor is on the index=1

        # But we know there are 3 motors in our setup, so we add a variable for each motor
        self.motor_1 = None
        self.motor_2 = None
        self.motor_3 = None

    # This function is crashing the code if no device is plugged in via USB
    def connect(self):
        try:
            MotionControl.build_device_list()
            print("Device list built successfully.")

            self.connectedController = self._record.connect()
            print("Record set up successfully.")

            self.channels = list(
                range(0, self.connectedController.max_channel_count()))  # Scan how many channels are on the device
            print("Identifying motors...")
            self.motors = [None]  # Erase previously loaded motors
            # Create list of available motors
            for i, chanel in enumerate(self.channels):
                self.motors.append(Motor(self, i+1))  # i starts indexing from 0 but motor ID starts from 1 => i+1
                print(f"    Motor {i+1} identified.")

            # TODO fix motor assignment when no channels found
            # Assign variable for each motor separately
            self.motor_1 = self.motors[1]
            self.motor_2 = self.motors[2]
            self.motor_3 = self.motors[3]
            print("Connection done.")

        except OSError:
            print("No devices found.")

    def disconnect(self):
        if self.connectedController:
            self.connectedController.disconnect()
        else:
            print("Unable to disconnect. controller is not connected.")

    def scanning_1d(self, input_data, on_progress, on_progress2):
        scan_1d(self.motors, input_data, on_progress, on_progress2)

    def scanning_3d(self, input_data, on_progress, on_progress2):
        scan_3d(self.motors, input_data, on_progress, on_progress2)

    def stop_motors(self):
        print("Stopping motors!")
        for motor in self.motors:
            if isinstance(motor, Motor):
                print(f"    Stopping motor: {motor}")
                motor.stop()
                print(f"    {motor} stopped.")


# Define motor controller object based on the hardware in the lab:
BSC203ThreeChannelBenchtopStepperMotorController = MotorController(
    manufacturer="Thorlabs",
    model="BSC203",
    serial="70224414",
    address="SDK::Thorlabs.MotionControl.Benchtop.StepperMotor.dll",
    backend=Backend.MSL)
