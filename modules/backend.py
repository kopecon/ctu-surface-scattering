# System libraries
import math
import os
import time
import random
import warnings
import logging

# Math libraries:
import numpy as np
import pandas as pd

# Hardware libraries
#   Motors:
from msl.equipment import (EquipmentRecord, ConnectionRecord, Backend)
from msl.equipment.resources.thorlabs import MotionControl
#   Sensor:
import nidaqmx
from nidaqmx.constants import Edge, AcquisitionType

# NI-DAQmx 2025 Q1 has to be installed on the executing pc to run the scan.
# NI-DAQmx 2025 Q1 download:
# https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html?srsltid=AfmBOooJ-Ko5HpJHEr4yPzQEZKufBWdBc1JjWh
# omtdJ27QKXivgjvTBr#559060

# Custom modules:
from modules import _scan
from modules import _calibration
from modules import parameters as param
from modules.app_logger import log_this


logger = logging.getLogger(__name__)


# Non-editable parameters
motor_1_limits = (param.motor_1_limits[0] - param.limit_margin,
                  param.motor_1_limits[1] + param.limit_margin)

motor_2_limits = (param.motor_2_limits[0] - param.limit_margin,
                  param.motor_2_limits[1] + param.limit_margin)

motor_3_limits = (param.motor_3_limits[0] - param.limit_margin,
                  param.motor_3_limits[1] + param.limit_margin)


class MotorController:
    """
    Class representing the motor controller hardware. Through this class you can control the motor setup as a whole set.
    Connecting and disconnecting. Performing measurements. Stopping all three motors at once.
    """

    def __init__(self, manufacturer: str, model: str, serial: str, address: str, backend: Backend):
        # ensure that the Kinesis folder is available on PATH
        os.environ["PATH"] += os.pathsep + "C:/Program Files/Thorlabs/Kinesis"

        # BSC203 Three Channel Benchtop Stepper Motor Controller model parameters
        self.name = 'BSC203'
        self.full_name = 'BSC203 Three Channel Benchtop Stepper Motor Controller'
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
        self.sensor = Sensor()

        # Measurement parameters
        self.scan_type = '3D'  # Or '2D'
        self.measurement_data = []

    def __repr__(self):
        return self.name

    # This function is crashing the code if no device is plugged in via USB
    @log_this
    def connect(self):
        """
        Creates the instance of BenchtopStepperMotor and opens it for communication.
        Allows us to access the 3 motors connected to BenchtopStepperMotor channels 1, 2, 3.
        The device has to be connected by USB to connect successfully.

        :return: 0 if connection was successful, 1 if connection was not successful
        """

        try:  # Has to be in try block in case USB is not connected
            MotionControl.build_device_list()  # Collect closed devices connected by USB
            logger.info(f'{log_this.space}Device list built successfully.')

            self.active_controller = self._record.connect()  # This creates the instance of BenchtopStepperMotor
            logger.info(f'{log_this.space}Record set up successfully.')
            time.sleep(1)  # Leave some time for connection to establish correctly

            # Connection to hardware was successful, therefore declare motors as _Motor() class.
            self.motor_1 = _Motor(self, 1, motor_1_limits)
            self.motor_2 = _Motor(self, 2, motor_2_limits)
            self.motor_3 = _Motor(self, 3, motor_3_limits)
            self.motors = [None, self.motor_1, self.motor_2, self.motor_3]
            logger.info(f'{log_this.space}Connected to hardware successfully.')

            return 0
        except OSError:
            logger.info(f'{log_this.space}Error: No devices found.')
            # Connection to hardware was not successful, therefore motors stay as _VirtualMotor() class.
            self.motors = [None, self.motor_1, self.motor_2, self.motor_3]
            logger.info(f'{log_this.space}Warning: Connected to virtual controller.')
            return 1

    @log_this
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
        logger.info(f'{log_this.space}Controller disconnected.')

    def collect_sensor_data(self):
        n = 0

        column_names = ["motor_1_position", "motor_2_position", "motor_3_position", "a0", "a1", "data_ratio"]
        scan_data_cluster = pd.DataFrame(columns=column_names)

        while n < self.sensor.number_of_measurement_points:
            self.sensor.toggle_graph_2D_timer.emit()
            sensor_data = self.sensor.measure_scattering()
            self.sensor.toggle_graph_2D_timer.emit()

            data_n = {
                "motor_1_position": self.motor_1.current_position,
                "motor_2_position": self.motor_2.current_position,
                "motor_3_position": self.motor_3.current_position,
                "a0": [sensor_data[0]],
                "a1": [sensor_data[1]],
                "data_ratio": [sensor_data[2]]}
            current_scan = pd.DataFrame(data_n)  # Get data from n-th scan
            scan_data_cluster = pd.concat((scan_data_cluster, current_scan), axis=0)  # Append current scan to previous

            # To prevent pandas FutureWarning spam:
            warnings.simplefilter(action='ignore', category=FutureWarning)

            n += 1

        # Now, each column has n number of values => get average value for every column
        scan_output = scan_data_cluster.mean()

        scan_output['data_ratio'] = scan_output['data_ratio']
        ''' Example of scan output:
        motor_1_position       0.0
        motor_2_position      90.0
        motor_3_position      60.0
        a0                55.614
        a1                249.95
        data_ratio           0.277
        '''
        self.measurement_data.append({'motor_1_position': self.motor_1.current_position,
                                      'motor_2_position': self.motor_2.current_position,
                                      'motor_3_position': self.motor_3.current_position,
                                      'a0': scan_output.iloc[3],
                                      'a1': scan_output.iloc[4]})

        return scan_output

    @log_this
    def calibrate(self):
        self.measurement_data.clear()
        _calibration.calibration(self)

    @log_this
    def scan(self, thread_signal_progress_status):
        self.measurement_data.clear()

        if self.scan_type == '1D':
            self.motor_1.scan_positions = [self.motor_1.scan_from]
            self.motor_2.scan_positions = [self.motor_2.scan_from]

        _scan.start_scanning(self, thread_signal_progress_status)

    @log_this
    def stop_motors(self):
        logger.info(f'{log_this.space}Stopping motors!')
        for motor in self.motors:
            if isinstance(motor, _Motor):
                logger.info(f'{log_this.space}Stopping motor: {motor.motor_id}')
                motor.stop()
        time.sleep(1)  # To ensure proper communication through USB

    @log_this
    def unstop_motors(self):
        # TODO: Find better name
        self.motor_1.stopped = False
        self.motor_2.stopped = False
        self.motor_3.stopped = False

    @log_this
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
        self.current_position = 0
        self.stopped = False

        # Motor 2 has different hardware limits than motor 1 and 3. Therefore, setup motor 2 separately:
        if self.motor_id == 2:
            self.set_rotation_mode(mode=1, direction=1)  # "Move to position" moves clockwise for positive values
            self._set_backwards_homing()  # Always home anticlockwise

        # Measurement parameters
        self.scan_from = 0
        self.scan_to = 90
        self.scan_step = 30
        self.scan_positions = self.find_range(self.scan_from, self.scan_to, self.scan_step)

    def __repr__(self):
        return f'Motor {self.motor_id}'

    # -----------------------------------------------------------------------------------   Motor Information Collecting
    @staticmethod
    def software_to_hardware_coordinates(software_position):
        # This should be used only for the motor 1 and motor 3.
        hardware_position = 90 - software_position
        if hardware_position < 0:
            hardware_position += 360
        return hardware_position

    @staticmethod
    def hardware_to_software_coordinates(hardware_position):
        # This should be used only for the motor 1 and motor 3.
        software_position = hardware_position
        if hardware_position < 0:
            hardware_position += 360
        return software_position

    def _while_moving_do(self, value: int):
        # Works in combination with polling. "start polling, wait, stop polling" to perform tasks while moving.
        self.parent_controller.clear_message_queue(self.motor_id)
        message_type, message_id, _ = self.parent_controller.wait_for_message(self.motor_id)
        # Loop until the motor reaches the desired position and changes message type then stop while loop.
        while message_type != 2 or message_id != value:
            if self.stopped:
                logger.info(f"{log_this.space}Can't move. Motor is stopped.")
            self.is_moving = True
            position = self.get_position()
            self.current_position = position[1]
            message_type, message_id, _ = self.parent_controller.wait_for_message(self.motor_id)
            movement_direction = self._check_for_movement_direction(position[1])
            illegal_position = self.check_for_illegal_position(position[1])
            if illegal_position and value != 0:
                if abs(position[1] - self.hardware_limits[1]) < abs(position[1] - self.hardware_limits[0]) \
                        and movement_direction == 'FORWARD':
                    self.stop()
                    logger.info(f'{log_this.space}Motor {self.motor_id} reached right limit. Stopping!')
                    self.reached_left_limit = False
                    self.reached_right_limit = True
                    break
                elif abs(position[1] - self.hardware_limits[0]) < abs(position[1] - self.hardware_limits[1]) \
                        and movement_direction == 'BACKWARD':
                    self.stop()
                    logger.info(f'{log_this.space}Motor {self.motor_id} reached left limit. Stopping!')
                    self.reached_left_limit = True
                    self.reached_right_limit = False
                    break

        self.is_moving = False
        self.set_velocity(velocity=50, acceleration=25)  # Set default velocity parameters
        if self.motor_id != 2:
            self.set_rotation_mode(mode=2, direction=0)  # Return to quickest pathing mode
        time.sleep(0.5)
        position = self.get_position()
        self.current_position = position[1]
        logger.info(f'{log_this.space}Motor {self.motor_id} At position {position[0]} [device units] {position[1]} '
                    f'[real-world units]')

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
        logger.info(f'{log_this.space}Motor {self.motor_id} setting loaded.')

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
            return logger.info(f'{log_this.space}Settings need to be loaded first.')

    def get_velocity(self):
        # Default value for movement: vel = 50.0 deg/s, acc = 25.0003 deg/s/s  TODO: double check the units
        velocity_d_u, acceleration_d_u = self.parent_controller.get_vel_params(self.motor_id)
        velocity_real = self.parent_controller.get_real_value_from_device_unit(
            self.motor_id, velocity_d_u, "VELOCITY")
        acceleration_real = self.parent_controller.get_real_value_from_device_unit(
            self.motor_id, acceleration_d_u, "ACCELERATION")
        return velocity_real, acceleration_real

    def get_travel_time(self, distance):
        # THIS METHOD IS NOT USED YET
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
            current_velocity = current_velocity - 2 * acceleration * dt

        return travel_time, traveled_distance

    def get_homing_velocity(self):
        if self.settings_loaded:
            velocity_device_units = self.parent_controller.get_homing_velocity(self.motor_id)
            velocity_real_units = self.parent_controller.get_real_value_from_device_unit(self.motor_id,
                                                                                         velocity_device_units,
                                                                                         "VELOCITY")
            return velocity_real_units, velocity_device_units
        else:
            return logger.info(f'{log_this.space}Settings need to be loaded first.')

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
                # logger.info(left_limit, target_position, right_limit)
                return True

    def _check_for_movement_direction(self, previous_position):
        new_position = self.get_position()[1]
        if new_position > previous_position:
            return 'FORWARD'
        elif new_position < previous_position:
            return 'BACKWARD'

    def find_range(self, start, stop, step):
        # TODO: Test all range options and fix illegal combinations (m3 from 270 to 90 etc...)
        difference = stop - start
        if difference >= 0:
            dx = int((stop - start) / step + 1)
            scan_positions = np.linspace(start, stop, endpoint=True, num=dx)
            return scan_positions
        else:
            first_half = self.find_range(start, 360, self.scan_step)
            second_half = self.find_range(0, stop, self.scan_step)
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
            return logger.info(f'{log_this.space}Settings need to be loaded first.')

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
            return logger.info(f'{log_this.space}Settings need to be loaded first.')

    def _set_forward_homing(self, velocity=6):
        # TODO: Calibrate offset
        if self.settings_loaded:
            self.set_homing_parameters(1, 1, velocity, -6.5)
        else:
            return logger.info(f'{log_this.space}Settings need to be loaded first.')

    def _set_backwards_homing(self, velocity=6):
        # TODO: Calibrate offset
        if self.settings_loaded:
            self.set_homing_parameters(2, 1, velocity, 3)
        else:
            return logger.info(f'{log_this.space}Settings need to be loaded first.')

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
                logger.info(f'Motor {self.motor_id}: "from" is outside of the legal space.')
                return

        if scan_to is not None:
            if self.check_for_illegal_position(scan_to):
                logger.info(f'Motor {self.motor_id}: "to" is outside of the legal space.')
                return

        # If statements allow us to change only one at the time and keep the previous values for the rest.
        self.scan_from = self.scan_from if scan_from is None else scan_from
        self.scan_to = self.scan_to if scan_to is None else scan_to
        self.scan_step = self.scan_step if scan_step is None else scan_step
        self.scan_positions = self.find_range(self.scan_from, self.scan_to, self.scan_step)

    # ----------------------------------------------------------------------------------------------    Moving Functions
    @log_this
    def home(self, velocity=10):
        if self.stopped:
            return 1
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
        logger.info(f'{log_this.space}Homing motor {self.motor_id}...')
        self._while_moving_do(0)
        position = self.get_position()
        if position[1] == 0:
            logger.info(f'{log_this.space}Motor {self.motor_id} successfully homed.')
            self.reached_left_limit = False
            self.reached_right_limit = False
        else:
            logger.info(f'{log_this.space}Motor {self.motor_id} failed to home.')
        self._stop_polling()
        self.current_position = self.get_position()[0]

    @log_this
    def move_to_position(self, position):
        if self.stopped:
            return 1
        illegal_position = self.check_for_illegal_position(position)
        logger.info(f'{log_this.space}Velocity: {self.get_velocity()[0]}, Acceleration: {self.get_velocity()[1]}')
        if not illegal_position:
            self._start_polling()
            position_in_device_unit = self.parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                             position,
                                                                                             'DISTANCE')
            start_time = time.time()
            self.parent_controller.move_to_position(self.motor_id, position_in_device_unit)
            self._while_moving_do(1)
            self._stop_polling()
            end_time = time.time()
            duration = abs(end_time - start_time)
            logger.info(f'{log_this.space}Movement duration:', duration)

            if self.motor_id != 2:
                if self.reached_left_limit and not self.is_moving:
                    logger.info(f'{log_this.space}Left limit handling')
                    self.set_velocity(velocity=10, acceleration=20)
                    self.set_rotation_mode(mode=2, direction=1)  # Forward direction
                    time.sleep(1)
                    self.reached_left_limit = False
                    self.move_to_position(position)  # Rotate clockwise
                elif self.reached_right_limit:
                    logger.info(f'{log_this.space}Right limit handling')
                    self.set_velocity(velocity=10, acceleration=20)
                    self.set_rotation_mode(mode=2, direction=2)  # Forward direction
                    time.sleep(1)
                    self.reached_right_limit = False
                    self.move_to_position(position)  # Rotate anticlockwise
        else:
            logger.info(f'{log_this.space}Movement would result in illegal position')
        self.current_position = self.get_position()[1]

    @log_this
    def stop(self):
        # stop_immediate(self, channel)  might be another option but following version works so far.
        # Based on documentation, stop_profiled is a controlled and safe way of stopping.
        # stop_immediate could lead to losing correct position reading, but probably would be faster.
        self.parent_controller.stop_profiled(self.motor_id)
        self.stopped = True
        self.current_position = self.get_position()[0]
        logger.info(f'{log_this.space}Motor {self.motor_id} stopped.')


class _VirtualMotor(_Motor):
    """
    Class representing the virtual motors. In case the hardware is not connected.
    This class is used mainly for developing purposes and debugging.
    """

    def __init__(self, parent: MotorController, motor_id: int, hardware_limits: tuple, polling_rate=200):
        super().__init__(parent, motor_id, hardware_limits, polling_rate)
        self.current_velocity = 20
        self.current_acceleration = 30

    def __repr__(self):
        return f'Motor {self.motor_id}'

    def _load_settings(self):
        self.settings_loaded = True
        logger.info(f'{log_this.space}Motor {self.motor_id} setting loaded.')

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

    @log_this
    def home(self, velocity=10):
        time.sleep(1)
        self.current_position = 0
        logger.info(f'{log_this.space}Motor {self.motor_id} homed.')

    @log_this
    def move_to_position(self, position):
        if self.stopped:
            logger.info(f"{log_this.space}Can't move. Motor is stopped.")
            return 1
        time.sleep(1)
        # logger.info(self.get_travel_time(abs(position)-self.get_position()))
        self.current_position = position
        logger.info(f'{log_this.space}Motor {self.motor_id} moved to {position}.')

    @log_this
    def stop(self):
        logger.info(f'{log_this.space}Motor {self.motor_id} stopped.')
        self.stopped = True


class Sensor:
    def __init__(self):
        self.current_a0 = 0
        self.current_a1 = 0
        self.history_length = 5
        self.a0_history = [0.0]
        self.a1_history = [0.0]
        self.max_value_a0 = 0
        self.max_value_a1 = 0
        self.number_of_measurement_points = 500
        self.measure_scattering()  # Obtain initial values
        self.toggle_graph_2D_timer = None  # Gets assigned in GUI

    def measure_scattering(self):
        try:
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan(
                    "myDAQ1/ai0:1"
                )
                task.timing.cfg_samp_clk_timing(
                    100000,
                    source="",
                    active_edge=Edge.RISING,
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=10,
                )

                sensor_data = task.read()
                self.current_a0 = float(sensor_data[0])
                self.current_a1 = float(sensor_data[1])
                # Save only last 5 (history_length) values
                if len(self.a0_history) > self.history_length:
                    self.a0_history = self.a0_history[1:]
                if len(self.a1_history) > self.history_length:
                    self.a1_history = self.a0_history[1:]
                self.a0_history.append(self.current_a0)
                self.a1_history.append(self.current_a1)
                if self.current_a0 > self.max_value_a0:
                    self.max_value_a0 = self.current_a0
                data_ratio = self.current_a0 / self.current_a1
                return self.current_a0, self.current_a1, data_ratio

        except nidaqmx.errors.DaqNotFoundError:
            # This part is for debugging, when accessing measurement without the hardware.
            # The type of the nidaqmx.error to except seems to be changing based on which PC the program runs on.
            self.current_a0 = random.randint(42, 70)
            self.current_a1 = random.randint(71, 420)
            if len(self.a0_history) > self.history_length:
                self.a0_history = self.a0_history[1:]
            if len(self.a1_history) > self.history_length:
                self.a1_history = self.a0_history[1:]
            self.a0_history.append(self.current_a0)
            self.a1_history.append(self.current_a1)
            if self.current_a0 > self.max_value_a0:
                self.max_value_a0 = self.current_a0
            data_ratio = self.current_a0 / self.current_a1
            return self.current_a0, self.current_a1, data_ratio

    def get_last_measurement(self):
        return self.a0_history[-1], self.a1_history[-1], self.a0_history[-1] / self.a1_history[-1]

    def set_number_of_measurement_points(self, value):
        self.number_of_measurement_points = int(value)


# Define motor controller object based on the hardware in the lab:
motor_controller = MotorController(
    manufacturer="Thorlabs",
    model="BSC203",
    serial="70224414",
    address="SDK::Thorlabs.MotionControl.Benchtop.StepperMotor.dll",
    backend=Backend.MSL)
