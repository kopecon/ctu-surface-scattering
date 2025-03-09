
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
    print("Scanning.")
    motor_3.move_to_position(motor_3_position + calibration_range)
    print("Scanning.")
    motor_3.move_to_position(motor_3_position - calibration_range)
    print("Scanning.")
