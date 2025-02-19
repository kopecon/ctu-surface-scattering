# System libraries
import os
import time

# Hardware libraries
from msl.equipment import (EquipmentRecord, ConnectionRecord, Backend)
from msl.equipment.resources.thorlabs import MotionControl

# Custom modules:
from _surface_scattering_scan import scan


# Editable Parameters:
hardware_limit_margin = 5  # How far [deg] beyond limit can device legally move without stopping.


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
        self.motors = [None, None, None, None]
        # List of available motors - motors are indexed from 1, so let 0 index be None, so the first motor is
        # on the index=1

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
            self.motor_1.hardware_limits = (270-hardware_limit_margin, 90+hardware_limit_margin)
            self.motor_2.hardware_limits = (0-hardware_limit_margin, 270+hardware_limit_margin)
            self.motor_3.hardware_limits = (270-hardware_limit_margin, 90+hardware_limit_margin)
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

    def scanning_1d(self, input_data, thread_signal):
        scan_1d(self.motors, input_data, thread_signal)

    def scanning_3d(self, input_data, thread_signal):
        scan(self.motors, input_data, thread_signal)

    def stop_motors(self):
        print("Stopping motors!")
        for motor in self.motors:
            if isinstance(motor, _Motor):
                print(f"    Stopping motor: {motor.motor_id}")
                motor.stop()
                print(f"    {motor.motor_id} stopped.")
        self.active_controller.disconnect()
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

        # Motor 2 has different hardware limits than motor 1 and 3. Therefore, setup motor 2 separately:
        if self.motor_id == 2:
            self.set_rotation_mode(mode=1, direction=1)  # "Move to position" moves clockwise for positive values
            self._set_backwards_homing()  # Always home anticlockwise

    # -----------------------------------------------------------------------------------   Motor Information Collecting
    def _while_moving_do(self, value: int):
        # Works in combination with polling. "start polling, wait, stop polling" to perform tasks while moving.
        self._parent_controller.clear_message_queue(self.motor_id)
        message_type, message_id, _ = self._parent_controller.wait_for_message(self.motor_id)
        # Loop until the motor reaches the desired position and changes message type then stop while loop.
        while message_type != 2 or message_id != value:
            self.is_moving = True
            position = self.get_position()
            print(f"Motor {self.motor_id} At position {position[0]} [device units] {position[1]} [real-world units]")
            message_type, message_id, _ = self._parent_controller.wait_for_message(self.motor_id)
            movement_direction = self._check_for_movement_direction(position[1])
            illegal_position = self._check_for_illegal_position(position[1])
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

    def get_velocity(self):
        # Default value for movement: vel = 50.0 deg/s, acc = 25.0003 deg/s/s  TODO: double check the units
        velocity_d_u, acceleration_d_u = self._parent_controller.get_vel_params(self.motor_id)
        velocity_real = self._parent_controller.get_real_value_from_device_unit(
            self.motor_id, velocity_d_u, "VELOCITY")
        acceleration_real = self._parent_controller.get_real_value_from_device_unit(
            self.motor_id, acceleration_d_u, "ACCELERATION")
        return velocity_real, acceleration_real

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
                return True

    def _check_for_movement_direction(self, previous_position):
        new_position = self.get_position()[1]
        if new_position > previous_position:
            return 'FORWARD'
        elif new_position < previous_position:
            return 'BACKWARD'

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

    def set_velocity(self, velocity=20, acceleration=30):
        # Velocity over 10 is already very fast to keep up with polling rate 200ms
        # TODO: Test proper velocities
        velocity_device_units = self._parent_controller.get_device_unit_from_real_value(self.motor_id, velocity,
                                                                                        "VELOCITY")
        acceleration_device_units = self._parent_controller.get_device_unit_from_real_value(self.motor_id, acceleration,
                                                                                            "ACCELERATION")

        self._parent_controller.set_vel_params(self.motor_id, velocity_device_units, acceleration_device_units)

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

        elif self.motor_id == 2:
            self.move_to_position(10)

        self._start_polling(rate=self._polling_rate)

        self._parent_controller.home(self.motor_id)
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

    def move_to_position(self, position):
        illegal_position = self._check_for_illegal_position(position)
        print(f"Velocity: {self.get_velocity()[0]}, Acceleration: {self.get_velocity()[1]}")
        if not illegal_position:
            self._start_polling()
            position_in_device_unit = self._parent_controller.get_device_unit_from_real_value(self.motor_id,
                                                                                              position,
                                                                                              "DISTANCE")
            start_time = time.time()
            self._parent_controller.move_to_position(self.motor_id, position_in_device_unit)
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
