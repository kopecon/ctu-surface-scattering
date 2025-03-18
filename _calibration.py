from _scan import _find_range
import _sensor
import matplotlib
from matplotlib import pyplot as plt
matplotlib.use('agg')  # To safely use matplotlib outside the main thread


def plot_data(x_value, y_value):
    plt.plot(x_value, y_value)
    plt.savefig('calibration_graph.png')


def calibration(motors, input_data):
    print("Calibration started.")
    motor_1 = motors[1]
    motor_2 = motors[2]
    motor_3 = motors[3]

    motor_1_position = float(input_data[0])
    motor_2_position = float(input_data[1])
    motor_3_position = float(input_data[2])
    calibration_range = float(input_data[3])
    motor_3_step = float(input_data[4])/10
    number_of_measurement_points = int(input_data[5])

    calibration_steps = _find_range(
        motor_3_position-calibration_range, motor_3_position+calibration_range, motor_3_step)
    motor_1.move_to_position(motor_1_position)
    motor_2.move_to_position(motor_2_position)
    motor_3.move_to_position(motor_3_position)
    print("Motors in position.")

    scattering_data = []
    scattering_data_avg = []

    for step in calibration_steps:
        motor_3.move_to_position(step)
        for point in range(number_of_measurement_points):
            scattering_value = _sensor.measure_scattering()[0]
            scattering_data.append(scattering_value)
        scattering_data_avg.append(sum(scattering_data)/len(scattering_data))
    plot_data(calibration_steps, scattering_data_avg)
    print("Calibration finished.")
