# System libraries
import math
import os
import time

import numpy as np

# Hardware libraries
from msl.equipment import (EquipmentRecord, ConnectionRecord, Backend)
from msl.equipment.resources.thorlabs import MotionControl

# Custom modules:
import _scan
import _calibration
import _sensor

# Editable Parameters:
global_polling_rate = 200
motor_1_limits = (270, 90)  # (Counter-Clockwise, Clockwise) limits of the motor 1 in [deg].
motor_2_limits = (0, 270)   # (Counter-Clockwise, Clockwise) limits of the motor 2 in [deg].
motor_3_limits = (270, 90)  # (Counter-Clockwise, Clockwise) limits of the motor 3 in [deg].

limit_margin = 2  # How far [deg] beyond limit can device legally move without stopping.

motor_1_speed = 50  # probably [deg/s]
motor_2_speed = 50  # probably [deg/s]
motor_3_speed = 50  # probably [deg/s]

motor_1_acceleration = 25  # probably [deg/s/s]
motor_2_acceleration = 25  # probably [deg/s/s]
motor_3_acceleration = 25  # probably [deg/s/s]

motor_1_homing_speed = 6  # probably [deg/s]
motor_2_homing_speed = 6  # probably [deg/s]
motor_3_homing_speed = 6  # probably [deg/s]

forward_homing_offset = -6.5  # [deg]
backwards_homing_offset = 3  # [deg]

# Non-editable parameters
motor_1_limits = (motor_1_limits[0] - limit_margin, motor_1_limits[1] + limit_margin)
motor_2_limits = (motor_2_limits[0] - limit_margin, motor_2_limits[1] + limit_margin)
motor_3_limits = (motor_3_limits[0] - limit_margin, motor_3_limits[1] + limit_margin)


class MotorController:
    """
    Class representing the motor controller hardware. Through this class you can control the motor setup as a whole set.
    Connecting and disconnecting. Performing measurements. Stopping all three motors at once.
    """

    def __init__(self, manufacturer: str, model: str, serial: str, address: str, backend: Backend):
        # ensure that the Kinesis folder is available on PATH
        os.environ["PATH"] += os.pathsep + "C:/Program Files/Thorlabs/Kinesis"

        # BSC203 Three Channel Benchtop Stepper Motor Controller model parameters
        self._manufacturer = manufacturer
        self._model = model
        self._serial = serial
        self._address = address
        self._backend = backend
        self._record = EquipmentRecord(
            manufacturer=self._manufacturer, model=self._model,  # update for your device
            serial=self._serial,  # update for your device
            connection=ConnectionRecord(address=self._address, backend=self._backend))
        self.active_controller = None  # The instance of BenchtopStepperMotor class. Needs to be initiated by connect().
        # There are 3 motors in our setup, so we add a variable for each motor. Motors get assigned by connect().
        # Before connecting the motors are declared as _VirtualMotor() class.
        self.motor_1 = _VirtualMotor(self, 1, motor_1_limits)
        self.motor_2 = _VirtualMotor(self, 2, motor_2_limits)
        self.motor_3 = _VirtualMotor(self, 3, motor_3_limits)
        self.motors = [None, self.motor_1, self.motor_2, self.motor_3]
        # List of available motors - motors are indexed from 1, so let 0 index be None, so the first motor is
        # on the index=1
        self.sensor = _sensor.Sensor()

        # Measurement parameters
        self.scan_type = '3D'  # Or '2D'

    # This function is crashing the code if no device is plugged in via USB
    def connect(self):
        """
        Creates the instance of BenchtopStepperMotor and opens it for communication.
        Allows us to access the 3 motors connected to BenchtopStepperMotor channels 1, 2, 3.
        The device has to be connected by USB to connect successfully.
        :return: 0 if connection was successful, 1 if connection was not successful
        """
        try:  # Has to be in try block in case USB is not connected
            MotionControl.build_device_list()  # Collect closed devices connected by USB
            print("Device list built successfully.")

            self.active_controller = self._record.connect()  # This creates the instance of BenchtopStepperMotor
            print("Record set up successfully.")
            time.sleep(1)  # Leave some time for connection to establish correctly

            # Connection to hardware was successful, therefore declare motors as _Motor() class.
            self.motor_1 = _Motor(self, 1, motor_1_limits)
            self.motor_2 = _Motor(self, 2, motor_2_limits)
            self.motor_3 = _Motor(self, 3, motor_3_limits)
            self.motors = [None, self.motor_1, self.motor_2, self.motor_3]
            print("Connected to hardware successfully.")

            return 0
        except OSError:
            print("No devices found.")
            # Connection to hardware was not successful, therefore motors stay as _VirtualMotor() class.
            self.motors = [None, self.motor_1, self.motor_2, self.motor_3]
            print("Connected to virtual controller.")
            return 0  # TODO: Set to 1 after debugging!

    def disconnect(self):
        """
        Disconnects the device and closes the communication with it.
        :return: None
        """
        if self.active_controller is not None:
            self.active_controller.disconnect()
            time.sleep(1)  # To make sure the serial communication is handled properly
            self.active_controller = None  # Remove the controller
            # Remove the motors
            self.motor_1 = None
            self.motor_2 = None
            self.motor_3 = None
            self.motors = [None, self.motor_1, self.motor_2, self.motor_3]
        print("Controller disconnected.")

    def calibrate(self, input_data):
        _calibration.calibration(self, input_data)

    def scanning(self, thread_signal):
        _scan.scan(self, thread_signal)

    def measure_scattering_here(self):
        scattering_value = self.sensor.measure_scattering()
        motor_positions = (self.motor_1.current_position, self.motor_2.current_position, self.motor_3.current_position)
        measurement_data = [motor_positions, scattering_value]
        return measurement_data

    def stop_motors_and_disconnect(self):
        print("Stopping motors!")
        for motor in self.motors:
            if isinstance(motor, _Motor):
                print(f"    Stopping motor: {motor.motor_id}")
                motor.stop()
        self.disconnect()  # TODO: Find a way to avoid this
        time.sleep(1)  # To ensure proper communication through USB

    def set_scan_type(self, scan_type: str):
        self.scan_type = scan_type


class _Motor:
    """
    Class representing the motor hardware.
    Is not intended to work independently, but is instanced by the "connect()" method in MotorController class.
    This class allows us to access the motor functions such as moving and homing of each motor independently.
    """

    def __init__(self, parent: MotorController, motor_id: int, hardware_limits: tuple, polling_rate=200):
        # Motor parameters
        self.motor_id = motor_id  # Number corresponding to the channel number to which is this motor assigned
        self._parent = parent  # MotorController class instance
        self._polling_rate = polling_rate
        self.hardware_limits = hardware_limits  # Max angle of rotation in degrees
        self.parent_controller = parent.active_controller
        self.settings_loaded = False

        self._load_settings()

        # Movement status
        self.is_moving = False
        self.reached_left_limit = False
        self.reached_right_limit = False

        # Motor 2 has different hardware limits than motor 1 and 3. Therefore, setup motor 2 separately:
        if self.motor_id == 2:
            self.set_rotation_mode(mode=1, direction=1)  # "Move to position" moves clockwise for positive values
            self._set_backwards_homing()  # Always home anticlockwise

        self.current_position = 0

        # Measurement parameters
        self.scan_from = 0
        self.scan_to = 90
        self.scan_step = 30
        self.scan_positions = self.find_range(self.scan_from, self.scan_to)

    # -----------------------------------------------------------------------------------   Motor Information Collecting
    def _while_moving_do(self, value: int):
        # Works in combination with polling. "start polling, wait, stop polling" to perform tasks while moving.
        self.parent_controller.clear_message_queue(self.motor_id)
        message_type, message_id, _ = self.parent_controller.wait_for_message(self.motor_id)
        # Loop until the motor reaches the desired position and changes message type then stop while loop.
        while message_type != 2 or message_id != value:
            self.is_moving = True
            position = self.get_position()
            print(f"Motor {self.motor_id} At position {position[0]} [device units] {position[1]} [real-world units]")
            message_type, message_id, _ = self.parent_controller.wait_for_message(self.motor_id)
            movement_direction = self._check_for_movement_direction(position[1])
            illegal_position = self.check_for_illegal_position(position[1])
            if illegal_position and value != 0:
                if abs(position[1] - self.hardware_limits[1]) < abs(position[1] - self.hardware_limits[0]) \
                        and movement_direction == 'FORWARD':
                    self.stop()
                    print(f"Motor {self.motor_id} reached right limit. Stopping!")
                    self.reached_left_limit = False
                    self.reached_right_limit = True
                    break
                elif abs(position[1] - self.hardware_limits[0]) < abs(position[1] - self.hardware_limits[1]) \
                        and movement_direction == 'BACKWARD':
                    self.stop()
                    print(f"Motor {self.motor_id} reached left limit. Stopping!")
                    self.reached_left_limit = True
                    self.reached_right_limit = False
                    break

        self.is_moving = False
        self.set_velocity(velocity=50, acceleration=25)  # Set default velocity parameters
        if self.motor_id != 2:
            self.set_rotation_mode(mode=2, direction=0)  # Return to quickest pathing mode
        time.sleep(0.5)
        position = self.get_position()
        print(f"Motor {self.motor_id} At position {position[0]} [device units] {position[1]} [real-world units]")

    def _load_settings(self):
        """
        This method loads the setting for the current motor. Overrides every other setting set by the "_set..." Methods.
        It is called when creating the motor instance in __init__() when used MotorController.connect().
        :return:
        """
        self.parent_controller.load_settings(self.motor_id)
        # The SBC_Open(serialNo) function in Kinesis is non-blocking, and therefore we
        # Should add a delay for Kinesis to establish communication with the serial port
        time.sleep(1)
        self.settings_loaded = True
        print(f"    Motor {self.motor_id} setting loaded.")

    def _start_polling(self, rate=200):
        self.parent_controller.start_polling(self.motor_id, rate)

    def _stop_polling(self):
        self.parent_controller.stop_polling(self.motor_id)

    def get_position(self):
        if self.settings_loaded:
            position_device_unit = self.parent_controller.get_position(self.motor_id)
            position_real_unit = self.parent_controller.get_real_value_from_device_unit(
                self.motor_id, position_device_unit, "DISTANCE")
            return position_device_unit, position_real_unit
        else:
            return print("Settings need to be loaded first.")

    def get_velocity(self):
        # Default value for movement: vel = 50.0 deg/s, acc = 25.0003 deg/s/s  TODO: double check the units
        velocity_d_u, acceleration_d_u = self.parent_controller.get_vel_params(self.motor_id)
        velocity_real = self.parent_controller.get_real_value_from_device_unit(
            self.motor_id, velocity_d_u, "VELOCITY")
        acceleration_real = self.parent_controller.get_real_value_from_device_unit(
            self.motor_id, acceleration_d_u, "ACCELERATION")
        return velocity_real, acceleration_real

    def get_travel_time(self, distance):
        velocity = self.get_velocity()[0]
        acceleration = self.get_velocity()[1]
        current_velocity = 0.01
        travel_time = 0
        distance_needed_to_stop = 0
        traveled_distance = 0
        dt = 0.1
        while traveled_distance <= distance - distance_needed_to_stop:
            while current_velocity <= velocity and traveled_distance <= distance - distance_needed_to_stop:
                # Acceleration
                current_velocity = math.sqrt(2 * acceleration * travel_time)
                time.sleep(dt)
                travel_time = travel_time + dt
                traveled_distance = traveled_distance + current_velocity * dt
                distance_needed_to_stop = current_velocity / 2 / acceleration
            # Constant speed
            traveled_distance = traveled_distance + current_velocity * dt
            time.sleep(dt)
            travel_time = travel_time + dt
            distance_needed_to_stop = current_velocity / 2 / acceleration

        while current_velocity >= 0:
            # Deceleration
            traveled_distance = traveled_distance + current_velocity * dt
            current_velocity = current_velocity - 2*acceleration * dt

        return travel_time, traveled_distance

    def get_homing_velocity(self):
        if self.settings_loaded:
            velocity_device_units = self.parent_controller.get_homing_velocity(self.motor_id)
            velocity_real_units = self.parent_controller.get_real_value_from_device_unit(self.motor_id,
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
        limit_mode = self.parent_controller.get_soft_limit_mode(self.motor_id)
        return limit_mode

    def get_rotation_limits(self):
        # Call only after "load_settings()"
        min_angle_d_u = self.parent_controller.get_stage_axis_min_pos(self.motor_id)
        max_angle_d_u = self.parent_controller.get_stage_axis_max_pos(self.motor_id)
        min_angle_r_u = self.parent_controller.get_real_value_from_device_unit(self.motor_id,
                                                                               min_angle_d_u,
                                                                               'DISTANCE')
        max_angle_r_u = self.parent_controller.get_real_value_from_device_unit(self.motor_id,
                                                                               max_angle_d_u,
                                                                               'DISTANCE')
        return min_angle_r_u, max_angle_r_u

    def get_location_quadrant(self, target_location=None):
        # Checks in which quadrant is the motor arm located and returns the name of the quadrant in integer 0~4.
        # Or check in which quadrant is the target location located.
        position_r_u = target_location if target_location is not None else self.get_position()[1]
        if position_r_u == 0:
            # Home
            return 0
        if 0 < position_r_u < 90:
            # First quadrant
            return 1
        if 270 < position_r_u < 360:
            # Second quadrant
            return 2
        if 180 < position_r_u <= 270:
            # Fourth quadrant
            return 3
        if 90 <= position_r_u <= 180:
            # Third quadrant
            return 4
        else:
            return None

    def check_for_illegal_position(self, target_position):
        left_limit = self.hardware_limits[0]
        right_limit = self.hardware_limits[1]
        if self.motor_id != 2:
            if left_limit <= target_position <= 360 or 0 <= target_position <= right_limit:
                return False
            else:
                return True
        elif self.motor_id == 2:
            # Motor 2 can move to "negative" values of angles. Needs to be handled separately
            if left_limit <= target_position <= right_limit:
                return False
            else:
                print(left_limit, target_position, right_limit)
                return True

    def _check_for_movement_direction(self, previous_position):
        new_position = self.get_position()[1]
        if new_position > previous_position:
            return 'FORWARD'
        elif new_position < previous_position:
            return 'BACKWARD'

    def find_range(self, start, stop):
        # TODO: Test all range options and fix illegal combinations (m3 from 270 to 90 etc...)
        difference = stop - start
        if difference >= 0:
            dx = int((stop - start) / self.scan_step + 1)
            scan_positions = np.linspace(start, stop, endpoint=True, num=dx)
            return scan_positions
        else:
            first_half = self.find_range(start, 360)
            second_half = self.find_range(0, stop)
            scan_positions = np.concatenate((first_half, second_half), axis=0)
            # 360 and 0 are the same angle... remove one of those.
            scan_positions = np.delete(scan_positions, np.where(scan_positions == 0))
            return scan_positions

    # --------------------------------------------------------------------------------------    Setting Motor Parameters
    #  All parameters can be set only after "load_settings()" has been called or gets overwritten
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
            self.parent_controller.set_rotation_modes(self.motor_id, mode, direction)
        else:
            return print("Settings need to be loaded first.")

    def set_homing_parameters(self, direction, limit, velocity, offset):
        # direction: int ...
        if self.settings_loaded:
            velocity_device_units = self.parent_controller.get_device_unit_from_real_value(self.motor_id, velocity,
                                                                                           "VELOCITY")
            offset_device_units = self.parent_controller.get_device_unit_from_real_value(self.motor_id, offset,
                                                                                         "DISTANCE")
            self.parent_controller.set_homing_params_block(
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

    def set_velocity(self, velocity=20, acceleration=30):
        # Velocity over 10 is already very fast to keep up with polling rate 200ms
        velocity_device_units = self.parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                       velocity,
                                                                                       "VELOCITY")
        acceleration_device_units = self.parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                           acceleration,
                                                                                           "ACCELERATION")

        self.parent_controller.set_vel_params(self.motor_id, velocity_device_units, acceleration_device_units)

    def set_measurement_parameters(self, scan_from=None, scan_to=None, scan_step=None):
        # Check for illegal positions:
        if scan_from is not None:
            if self.check_for_illegal_position(scan_from):
                print(f'Motor {self.motor_id}: "from" is outside of the legal space.')
                return

        if scan_to is not None:
            if self.check_for_illegal_position(scan_to):
                print(f'Motor {self.motor_id}: "to" is outside of the legal space.')
                return

        # If statements allow us to change only one at the time and keep the previous values for the rest.
        self.scan_from = self.scan_from if scan_from is None else scan_from
        self.scan_to = self.scan_to if scan_to is None else scan_to
        self.scan_step = self.scan_step if scan_step is None else scan_step
        self.scan_positions = self.find_range(self.scan_from, self.scan_to)

    # ----------------------------------------------------------------------------------------------    Moving Functions

    def home(self, velocity=10):
        quadrant = self.get_location_quadrant()
        # Set the proper direction of homing based on the motor position
        if self.motor_id != 2:
            if quadrant == 0:
                pass
            elif quadrant == 1 or quadrant == 4:
                self.move_to_position(10)
                self._set_backwards_homing(velocity)
            elif quadrant == 2 or quadrant == 3:
                self.move_to_position(350)
                self._set_forward_homing(velocity)

        elif self.motor_id == 2:
            self.move_to_position(10)

        time.sleep(0.5)  # To make sure that controller has not been disconnected in the meantime.

        self._start_polling(rate=self._polling_rate)
        self.parent_controller.home(self.motor_id)
        print(f"Homing motor {self.motor_id}...")
        self._while_moving_do(0)
        position = self.get_position()
        if position[1] == 0:
            print(f"Motor {self.motor_id} successfully homed.")
            self.reached_left_limit = False
            self.reached_right_limit = False
        else:
            print(f"Motor {self.motor_id} failed to home.")
        self._stop_polling()
        self.current_position = self.get_position()[0]

    def move_to_position(self, position):
        illegal_position = self.check_for_illegal_position(position)
        print(f"Velocity: {self.get_velocity()[0]}, Acceleration: {self.get_velocity()[1]}")
        if not illegal_position:
            self._start_polling()
            position_in_device_unit = self.parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                             position,
                                                                                             "DISTANCE")
            start_time = time.time()
            self.parent_controller.move_to_position(self.motor_id, position_in_device_unit)
            self._while_moving_do(1)
            self._stop_polling()
            end_time = time.time()
            duration = abs(end_time - start_time)
            print("Movement duration:", duration)

            if self.motor_id != 2:
                if self.reached_left_limit and not self.is_moving:
                    print("Left limit handling")
                    self.set_velocity(velocity=10, acceleration=20)
                    self.set_rotation_mode(mode=2, direction=1)  # Forward direction
                    time.sleep(1)
                    self.reached_left_limit = False
                    self.move_to_position(position)  # Rotate clockwise
                elif self.reached_right_limit:
                    print("Right limit handling")
                    self.set_velocity(velocity=10, acceleration=20)
                    self.set_rotation_mode(mode=2, direction=2)  # Forward direction
                    time.sleep(1)
                    self.reached_right_limit = False
                    self.move_to_position(position)  # Rotate anticlockwise
        else:
            print("Movement would result in illegal position")
        self.current_position = self.get_position()[0]

    def stop(self):
        # stop_immediate(self, channel)  might be another option but following version works so far.
        # Based on documentation, stop_profiled is a controlled and safe way of stopping.
        # stop_immediate could lead to losing correct position reading, but probably would be faster.
        self.parent_controller.stop_profiled(self.motor_id)
        self.current_position = self.get_position()[0]
        print(f"        Motor {self.motor_id} stopped.")


class _VirtualMotor(_Motor):
    """
    Class representing the virtual motors. In case the hardware is not connected.
    This class is used mainly for developing purposes and debugging.
    """

    def __init__(self, parent: MotorController, motor_id: int, hardware_limits: tuple, polling_rate=200):
        super().__init__(parent, motor_id, hardware_limits, polling_rate)
        self.current_position = 0
        self.current_velocity = 20
        self.current_acceleration = 30

    def _load_settings(self):
        self.settings_loaded = True
        print(f"    Motor {self.motor_id} setting loaded.")

    def get_position(self):
        return self.current_position

    def get_velocity(self):
        return self.current_velocity, self.current_acceleration

    def get_homing_velocity(self):
        return self.current_velocity, self.current_acceleration

    def set_rotation_mode(self, mode=2, direction=0):
        return

    def _set_backwards_homing(self, velocity=6):
        return

    def set_velocity(self, velocity=20, acceleration=30):
        self.current_velocity = velocity
        self.current_acceleration = acceleration

    def home(self, velocity=10):
        time.sleep(1)
        self.current_position = 0
        print(f"Motor {self.motor_id} homed.")

    def move_to_position(self, position):
        time.sleep(1)
        # print(self.get_travel_time(abs(position)-self.get_position()))
        self.current_position = position
        print(f"Motor {self.motor_id} moved to {position}.")

    def stop(self):
        print(f"        Motor {self.motor_id} stopped.")


# Define motor controller object based on the hardware in the lab:
BSC203ThreeChannelBenchtopStepperMotorController = MotorController(
    manufacturer="Thorlabs",
    model="BSC203",
    serial="70224414",
    address="SDK::Thorlabs.MotionControl.Benchtop.StepperMotor.dll",
    backend=Backend.MSL)
