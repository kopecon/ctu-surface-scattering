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


# Class representing the motor hardware.
# Is not intended to work independently, but is instanced by the "connect()" method in MotorController class.
class _Motor:
    def __init__(self, parent, motor_id, polling_rate=200):
        self.motor_id = motor_id
        self._parent = parent
        self._polling_rate = polling_rate
        self._controller = parent.connectedController
        self.settings_loaded = False

    # -----------------------------------------------------------------------------------   Motor Information collecting
    def _wait(self, value: int):
        # Works in combination with polling. "start polling, wait, stop polling" to print positions of the motor
        # while moving.
        self._controller.clear_message_queue(self.motor_id)
        message_type, message_id, _ = self._controller.wait_for_message(self.motor_id)
        while message_type != 2 or message_id != value:
            position = self.get_position()
            print(f"At position {position[0]} [device units] {position[1]} [real-world units]")
            message_type, message_id, _ = self._controller.wait_for_message(self.motor_id)
        else:
            print("Different message: ", message_id, message_type, _)

    def _load_settings(self):
        self._controller.load_settings(self.motor_id)
        # the SBC_Open(serialNo) function in Kinesis is non-blocking, and therefore we
        # should add a delay for Kinesis to establish communication with the serial port
        time.sleep(1)
        self.settings_loaded = True
        print("Motor setting loaded.")

    def _start_polling(self, rate=200):
        self._controller.start_polling(self.motor_id, rate)

    def _stop_polling(self):
        self._controller.stop_polling(self.motor_id)

    def get_position(self):
        if self.settings_loaded:
            position_device_unit = self._controller.get_position(self.motor_id)
            position_real_unit = self._controller.get_real_value_from_device_unit(
                self.motor_id, position_device_unit, "DISTANCE")
            return position_device_unit, position_real_unit
        else:
            return print("Settings need to be loaded first.")

    def get_homing_velocity(self):
        if self.settings_loaded:
            velocity_device_units = self._controller.get_homing_velocity(self.motor_id)
            velocity_real_units = self._controller.get_real_value_from_device_unit(self.motor_id,
                                                                                   velocity_device_units,
                                                                                   "VELOCITY")
            return velocity_real_units, velocity_device_units
        else:
            return print("Settings need to be loaded first.")

    def get_limit_approach_policy(self):
        # DisallowIllegalMoves = 0
        # AllowPartialMoves = 1
        # AllowAllMoves = 2
        # By default 0
        limit_mode = self._controller.get_soft_limit_mode(self.motor_id)
        return limit_mode

    def get_rotation_limits(self):
        # Call only after "load_settings()"
        min_angle_d_u = self._controller.get_stage_axis_min_pos(self.motor_id)
        max_angle_d_u = self._controller.get_stage_axis_max_pos(self.motor_id)
        min_angle_r_u = self._controller.get_real_value_from_device_unit(self.motor_id,
                                                                         min_angle_d_u,
                                                                         'DISTANCE')
        max_angle_r_u = self._controller.get_real_value_from_device_unit(self.motor_id,
                                                                         max_angle_d_u,
                                                                         'DISTANCE')
        return min_angle_r_u, max_angle_r_u

    def get_location(self, left_limit=270, right_limit=90):
        _, position_r_u = self.get_position()
        if position_r_u == 0:
            # Home
            return 0
        if 0 < position_r_u < right_limit:
            # First quadrant
            return 1
        if left_limit < position_r_u < 360:
            # Second quadrant
            return 2
        if 180 < position_r_u <= left_limit:
            # Third quadrant
            return 3
        if right_limit <= position_r_u <= 180:
            # Fourth quadrant
            return 4
        else:
            return None

    # --------------------------------------------------------------------------------------    Setting Motor Parameters
    #  All parameters can be set only after "load_settings()" has been called or gets overwritten
    def set_limit_parameters(self, min_angle=0, max_angle=360):
        # TODO: DONT UNDERSTAND, DOESNT WORK
        min_angle_d_u = self._controller.get_device_unit_from_real_value(self.motor_id,
                                                                         min_angle,
                                                                         'DISTANCE')
        max_angle_d_u = self._controller.get_device_unit_from_real_value(self.motor_id,
                                                                         max_angle,
                                                                         'DISTANCE')

        self._controller.set_limit_switch_params(self.motor_id, 2, 2, max_angle_d_u, min_angle_d_u, 2)
        print(self.get_rotation_limits())

    def set_limits_approach_policy(self, mode: int):
        # TODO: DONT UNDERSTAND, DOESNT WORK
        # DisallowIllegalMoves = 0
        # AllowPartialMoves = 1
        # AllowAllMoves = 2
        # By default = 0
        self._controller.set_limits_software_approach_policy(self.motor_id, mode)

    def set_rotation_limits(self, min_angle=0, max_angle=360):
        # TODO: DONT UNDERSTAND, DOESNT WORK
        # Angles in degrees
        min_angle_d_u = self._controller.get_device_unit_from_real_value(self.motor_id,
                                                                         min_angle,
                                                                         'DISTANCE')
        max_angle_d_u = self._controller.get_device_unit_from_real_value(self.motor_id,
                                                                         max_angle,
                                                                         'DISTANCE')
        self._controller.set_stage_axis_limits(self.motor_id, min_angle_d_u, max_angle_d_u)

    def set_rotation_mode(self, mode=2, direction=0):
        # mode: int ... 0,1,2
        #   0 ... linear mode !Do not use!
        #   1 ... rotation only in one direction
        #   2 ... rotation with access to both directions
        # direction: int ... 0,1,2
        #   0 ... quickest
        #   1 ... forward
        #   2 ... reverse
        # Does not affect homing directions
        if self.settings_loaded:
            self._controller.set_rotation_modes(self.motor_id, mode, direction)
        else:
            return print("Settings need to be loaded first.")

    def set_homing_parameters(self, direction, limit, velocity, offset):
        # direction: int ...
        if self.settings_loaded:
            velocity_device_units = self._controller.get_device_unit_from_real_value(self.motor_id, velocity, "VELOCITY")
            offset_device_units = self._controller.get_device_unit_from_real_value(self.motor_id, offset, "DISTANCE")
            self._controller.set_homing_params_block(
                self.motor_id, direction, limit, velocity_device_units, offset_device_units)
        else:
            return print("Settings need to be loaded first.")

    def _set_forward_homing(self, velocity=6):
        # TODO: Calibrate offset
        if self.settings_loaded:
            self.set_homing_parameters(1, 1, velocity, -6.5)
        else:
            return print("Settings need to be loaded first.")

    def _set_backwards_homing(self, velocity=6):
        # TODO: Calibrate offset
        if self.settings_loaded:
            self.set_homing_parameters(2, 1, velocity, 3)
        else:
            return print("Settings need to be loaded first.")

    # ----------------------------------------------------------------------------------------------    Moving Functions

    def home(self, velocity):
        if self._parent is not None:
            self._load_settings()
            location = self.get_location(240, 120)
            if location == 0:
                pass
            elif location == 1:
                self.move_to_position(355)
                self._set_backwards_homing(velocity)
            elif location == 2:
                self.move_to_position(5)
                self._set_forward_homing(velocity)
            else:
                print(location, "ERROR: Wrong location to home")
                return
            self._start_polling(rate=self._polling_rate)

            print("Initial position:")
            self.get_position()
            # TODO Add limit checking and direction change based on position
            self._controller.home(self.motor_id)
            print(f"Homing motor {self.motor_id}...")
            self._wait(0)
            self.get_position()
            self._stop_polling()
            print(f"Finishing homing motor {self.motor_id}...")
        else:
            print("Not connected to controller.")

    def move_to_position(self, position):
        # 90 deg in GUI = 360 - 90 in motor angles. The motor rotates anticlockwise.
        anti_clockwise_rotation = 360 - position
        position = anti_clockwise_rotation  # TODO: find if there is a better way

        self._load_settings()

        self._start_polling()
        position_in_device_unit = self._controller.get_device_unit_from_real_value(self.motor_id, position, "DISTANCE")
        # TODO Add limit checking and direction change based on position
        self._controller.move_to_position(self.motor_id, position_in_device_unit)
        self._wait(1)
        self._stop_polling()

    def stop(self):
        # stop_immediate(self, channel)  might be another option but following version works so far.
        # Based on documentation, stop_profiled is a controlled and safe way of stopping.
        # stop_immediate could lead to losing correct position reading, but probably would be faster.
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
            MotionControl.build_device_list()  # Collect closed devices connected by USB
            print("Device list built successfully.")

            self.connectedController = self._record.connect()
            print("Record set up successfully.")
            time.sleep(1)  # Leave some time for connection to establish correctly

            self.channels = list(
                range(0, self.connectedController.max_channel_count()))  # Scan how many channels are on the device
            print("Identifying motors...")
            self.motors = [None]  # Erase previously loaded motors
            # Create list of available motors
            for i, chanel in enumerate(self.channels):
                self.motors.append(_Motor(self, i + 1))  # i starts indexing from 0 but motor ID starts from 1 => i+1
                print(f"    Motor {i + 1} identified.")

            # TODO fix motor assignment when no channels found
            # Assign variable for each motor separately
            self.motor_1 = self.motors[1]
            self.motor_2 = self.motors[2]
            self.motor_3 = self.motors[3]
            print("Connection done.")
            return 0  # Successful
        except OSError:
            print("No devices found.")
            return 1  # Error

    def disconnect(self):
        self.connectedController.disconnect()
        # To make sure the serial communication is handled properly
        time.sleep(1)

    def scanning_1d(self, input_data, on_progress, on_progress2):
        scan_1d(self.motors, input_data, on_progress, on_progress2)

    def scanning_3d(self, input_data, on_progress, on_progress2):
        scan_3d(self.motors, input_data, on_progress, on_progress2)

    def stop_motors(self):
        print("Stopping motors!")
        for motor in self.motors:
            if isinstance(motor, _Motor):
                print(f"    Stopping motor: {motor.motor_id}")
                motor.stop()
                print(f"    {motor.motor_id} stopped.")


# Define motor controller object based on the hardware in the lab:
BSC203ThreeChannelBenchtopStepperMotorController = MotorController(
    manufacturer="Thorlabs",
    model="BSC203",
    serial="70224414",
    address="SDK::Thorlabs.MotionControl.Benchtop.StepperMotor.dll",
    backend=Backend.MSL)
