from _scan import _measure_scattering


def calibration(motors, input_data):
    print("Calibration started.")
    motor_1 = motors[1]
    motor_2 = motors[2]
    motor_3 = motors[3]
    motor_1_position = float(input_data[0])
    motor_2_position = float(input_data[1])
    motor_3_position = float(input_data[2])
    calibration_range = float(input_data[3])
    motor_1.move_to_position(motor_1_position)
    motor_2.move_to_position(motor_2_position)
    motor_3.move_to_position(motor_3_position)
    print("Motors in position.")

    measurement_data, data_ratio = _measure_scattering(
        motor_1.parent_controller,
        motor_1_position,
        motor_2_position,
        motor_3_position,
        number_of_measurement_points=5)

    motor_3.move_to_position(motor_3_position + calibration_range)

    measurement_data, data_ratio = _measure_scattering(
        motor_1.parent_controller,
        motor_1_position,
        motor_2_position,
        motor_3_position,
        number_of_measurement_points=5)

    motor_3.move_to_position(motor_3_position - calibration_range)

    measurement_data, data_ratio = _measure_scattering(
        motor_1.parent_controller,
        motor_1_position,
        motor_2_position,
        motor_3_position,
        number_of_measurement_points=5)
