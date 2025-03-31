def calibration(controller):
    print("Calibration started.")
    motor_1 = controller.motor_1
    motor_2 = controller.motor_2
    motor_3 = controller.motor_3

    motor_1.move_to_position(motor_1.scan_from)
    motor_2.move_to_position(motor_2.scan_from)
    motor_3.move_to_position(motor_3.scan_from)
    print("Motors in position.")

    for step in motor_3.scan_positions:
        motor_3.move_to_position(step)
        controller.collect_sensor_data()
    print("Calibration finished.")
