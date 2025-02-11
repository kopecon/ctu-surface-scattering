import math
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
        self.channels = []  # List of available channels
        self.motors = [None]  # List of available motors - motors are indexed from 1, so let 0 index be None, so the
        # first motor is on the index=1

        # There are 3 motors in our setup, so we add a variable for each motor. Motors get assigned by connect().
        self.motor_1 = None
        self.motor_2 = None
        self.motor_3 = None

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

            self.channels = list(
                range(0, self.active_controller.max_channel_count()))  # Scan how many channels are on the device
            print("Identifying motors...")
            self.motors = [None]  # Erase previously loaded motors
            # Create list of available motors
            for i, chanel in enumerate(self.channels):
                print(f"    Motor {i + 1} identified.")
                # i starts indexing from 0 but motor ID starts from 1 => i+1
                self.motors.append(_Motor(self, motor_id=i + 1))

            # Assign variable for each motor separately
            self.motor_1 = self.motors[1]  # Motor holding the laser
            self.motor_2 = self.motors[2]  # Motor rotating around the sample
            self.motor_3 = self.motors[3]  # Motor holding the sensor
            print("Connection done.")
            # Set the hardware limits of each motor independently
            self.motor_1.hardware_limits = (270, 90)
            self.motor_2.hardware_limits = (0, 330)  # TODO: Ask if it really can be more than 330...
            self.motor_2.set_rotation_mode(mode=1, direction=1)
            self.motor_3.hardware_limits = (270, 90)
            print("Motor settings loaded.")
            return 0  # Successful
        except OSError:
            print("No devices found.")
            return 1  # Error

    def disconnect(self):
        """
        Disconnects the device and closes the communication with it.
        :return: None
        """
        if hasattr(self.active_controller, 'disconnect'):
            self.active_controller.disconnect()
            # To make sure the serial communication is handled properly
            time.sleep(1)
            print("Controller disconnected.")

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
        time.sleep(1)


class _Motor:
    """
    Class representing the motor hardware.
    Is not intended to work independently, but is instanced by the "connect()" method in MotorController class.
    This class allows us to access the motor functions such as moving and homing of each motor independently.
    """

    def __init__(self, parent: MotorController, motor_id: int, polling_rate=200, hardware_limits=(270, 90)):
        # Motor parameters
        self.motor_id = motor_id  # Number corresponding to the channel number to which is this motor assigned
        self._parent = parent  # MotorController class instance
        self._polling_rate = polling_rate
        self.hardware_limits = hardware_limits  # Max angle of rotation in degrees
        self._parent_controller = parent.active_controller
        self.settings_loaded = False
        self._load_settings()

        # Movement status
        self.is_moving = False
        self.reached_left_limit = False
        self.reached_right_limit = False
        self.crossed_zero_from_left = False
        self.crossed_zero_from_right = False
        self.crossing_zero_tolerance = 30

    # -----------------------------------------------------------------------------------   Motor Information Collecting
    def _while_moving_do(self, value: int, to_position=None):
        # Works in combination with polling. "start polling, wait, stop polling" to print positions of the motor
        # while moving.
        self._parent_controller.clear_message_queue(self.motor_id)
        message_type, message_id, _ = self._parent_controller.wait_for_message(self.motor_id)
        # Loop until the motor reaches the desired position and changes message type
        latest_positions = [0]
        while message_type != 2 or message_id != value:
            self.is_moving = True
            position = self.get_position()
            print(f"Motor {self.motor_id} At position {position[0]} [device units] {position[1]} [real-world units]")
            message_type, message_id, _ = self._parent_controller.wait_for_message(self.motor_id)
            movement_direction = self._check_for_movement_direction(position[1])
            illegal_position = self._check_for_illegal_position(position[1])
            if illegal_position and self.motor_id != 2:  # TODO: Solve limits for motor 2
                if abs(position[1] - self.hardware_limits[1]) < abs(position[1] - self.hardware_limits[0]) \
                        and movement_direction == 'FORWARD':
                    self.stop()
                    print(f"Motor {self.motor_id} movement resulted in illegal position. Stopping!")
                    self.reached_right_limit = True
                    break
                elif abs(position[1] - self.hardware_limits[0]) < abs(position[1] - self.hardware_limits[1]) \
                        and movement_direction == 'BACKWARD':
                    self.stop()
                    print(f"Motor {self.motor_id} movement resulted in illegal position. Stopping!")
                    self.reached_left_limit = True
                    break

        # print("Different message: ", message_id, message_type, _)
        self.is_moving = False

    def _load_settings(self):
        """
        This method loads the setting for the current motor. Overrides every other setting set by the "_set..." Methods.
        It is called when creating the motor instance in __init__() when used MotorController.connect().
        :return:
        """
        self._parent_controller.load_settings(self.motor_id)
        # The SBC_Open(serialNo) function in Kinesis is non-blocking, and therefore we
        # Should add a delay for Kinesis to establish communication with the serial port
        time.sleep(1)
        self.settings_loaded = True
        print(f"    Motor {self.motor_id} setting loaded.")

    def _start_polling(self, rate=200):
        self._parent_controller.start_polling(self.motor_id, rate)

    def _stop_polling(self):
        self._parent_controller.stop_polling(self.motor_id)

    def get_position(self):
        if self.settings_loaded:
            position_device_unit = self._parent_controller.get_position(self.motor_id)
            position_real_unit = self._parent_controller.get_real_value_from_device_unit(
                self.motor_id, position_device_unit, "DISTANCE")
            return position_device_unit, position_real_unit
        else:
            return print("Settings need to be loaded first.")

    def get_homing_velocity(self):
        if self.settings_loaded:
            velocity_device_units = self._parent_controller.get_homing_velocity(self.motor_id)
            velocity_real_units = self._parent_controller.get_real_value_from_device_unit(self.motor_id,
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
        limit_mode = self._parent_controller.get_soft_limit_mode(self.motor_id)
        return limit_mode

    def get_rotation_limits(self):
        # Call only after "load_settings()"
        min_angle_d_u = self._parent_controller.get_stage_axis_min_pos(self.motor_id)
        max_angle_d_u = self._parent_controller.get_stage_axis_max_pos(self.motor_id)
        min_angle_r_u = self._parent_controller.get_real_value_from_device_unit(self.motor_id,
                                                                                min_angle_d_u,
                                                                                'DISTANCE')
        max_angle_r_u = self._parent_controller.get_real_value_from_device_unit(self.motor_id,
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

    def _check_for_illegal_position(self, target_position):
        left_limit = self.hardware_limits[0]
        right_limit = self.hardware_limits[1]
        if left_limit < target_position < 360 or 0 < target_position < right_limit:
            return False
        else:
            return True

    def _check_for_movement_direction(self, previous_position):
        new_position = self.get_position()[1]
        if new_position > previous_position:
            return 'FORWARD'
        elif new_position < previous_position:
            return 'BACKWARD'

    def _check_for_crossing_zero(self):
        '''
        if math.isclose(self.get_position()[1], 0, abs_tol=5):
            return True
        else:
            return False
        '''


    # --------------------------------------------------------------------------------------    Setting Motor Parameters
    #  All parameters can be set only after "load_settings()" has been called or gets overwritten
    def set_limit_parameters(self, min_angle=0, max_angle=360):
        # TODO: DONT UNDERSTAND, DOESNT WORK
        min_angle_d_u = self._parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                min_angle,
                                                                                'DISTANCE')
        max_angle_d_u = self._parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                max_angle,
                                                                                'DISTANCE')

        self._parent_controller.set_limit_switch_params(self.motor_id, 2, 2, max_angle_d_u, min_angle_d_u, 2)
        print(self.get_rotation_limits())

    def set_limits_approach_policy(self, mode: int):
        # TODO: DONT UNDERSTAND, DOESNT WORK
        # DisallowIllegalMoves = 0
        # AllowPartialMoves = 1
        # AllowAllMoves = 2
        # By default = 0
        self._parent_controller.set_limits_software_approach_policy(self.motor_id, mode)

    def set_rotation_limits(self, min_angle=0, max_angle=360):
        # TODO: DONT UNDERSTAND, DOESNT WORK
        # Angles in degrees
        min_angle_d_u = self._parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                min_angle,
                                                                                'DISTANCE')
        max_angle_d_u = self._parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                max_angle,
                                                                                'DISTANCE')
        self._parent_controller.set_stage_axis_limits(self.motor_id, min_angle_d_u, max_angle_d_u)

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
            self._parent_controller.set_rotation_modes(self.motor_id, mode, direction)
        else:
            return print("Settings need to be loaded first.")

    def set_homing_parameters(self, direction, limit, velocity, offset):
        # direction: int ...
        if self.settings_loaded:
            velocity_device_units = self._parent_controller.get_device_unit_from_real_value(self.motor_id, velocity,
                                                                                            "VELOCITY")
            offset_device_units = self._parent_controller.get_device_unit_from_real_value(self.motor_id, offset,
                                                                                          "DISTANCE")
            self._parent_controller.set_homing_params_block(
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

        # Set the proper direction of homing based on crossing zero direction
        elif self.motor_id == 2:
            if not self.crossed_zero_from_right:
                self.move_to_position(10)
                self._set_backwards_homing()
            elif self.crossed_zero_from_right:
                self.move_to_position(350)
                self._set_forward_homing()

        self._start_polling(rate=self._polling_rate)

        self._parent_controller.home(self.motor_id)
        print(f"Homing motor {self.motor_id}...")
        self._while_moving_do(0)
        time.sleep(1)
        position = self.get_position()
        print(f"Motor {self.motor_id} At position {position[0]} [device units] {position[1]} [real-world units]")
        if position[1] == 0:
            self.crossed_zero_from_left = False
            self.crossed_zero_from_right = False
            print(f"Motor {self.motor_id} successfully homed.")
        else:
            print(f"Motor {self.motor_id} not homed successfully.")
        self._stop_polling()

    def move_to_position(self, position):
        illegal_position = self._check_for_illegal_position(position)
        override = 1  # TODO remove after debugging
        if not illegal_position or override == 1:
            self._start_polling()
            position_in_device_unit = self._parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                              position,
                                                                                              "DISTANCE")
            self._parent_controller.move_to_position(self.motor_id, position_in_device_unit)
            self._while_moving_do(1, position)
            self._stop_polling()
        else:
            print("Movement would result in illegal position")

    def stop(self):
        # stop_immediate(self, channel)  might be another option but following version works so far.
        # Based on documentation, stop_profiled is a controlled and safe way of stopping.
        # stop_immediate could lead to losing correct position reading, but probably would be faster.
        self._parent_controller.stop_profiled(self.motor_id)


# Define motor controller object based on the hardware in the lab:
BSC203ThreeChannelBenchtopStepperMotorController = MotorController(
    manufacturer="Thorlabs",
    model="BSC203",
    serial="70224414",
    address="SDK::Thorlabs.MotionControl.Benchtop.StepperMotor.dll",
    backend=Backend.MSL)
