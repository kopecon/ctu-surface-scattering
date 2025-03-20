# System libraries
import random

# Hardware libraries
import nidaqmx
from nidaqmx.constants import Edge, AcquisitionType

# NI-DAQmx 2025 Q1 has to be installed on the executing pc to run the scan.
# NI-DAQmx 2025 Q1 download: https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html?srsltid=AfmBOooJ-Ko5HpJHEr4yPzQEZKufBWdBc1JjWhomtdJ27QKXivgjvTBr#559060


class Sensor:
    def __init__(self):
        self.current_ad_0 = 0
        self.current_ad_1 = 0
        self.ad_0_history = []
        self.ad_1_history = []
        self.number_of_measurement_points = 500

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
                self.current_ad_0 = float(sensor_data[0])
                self.current_ad_1 = float(sensor_data[1])
                self.ad_0_history.append(self.current_ad_0)
                self.ad_1_history.append(self.current_ad_1)
                return self.current_ad_0, self.current_ad_1

        except nidaqmx.errors.DaqNotFoundError:
            # print("Controller not found. Returning random data.")
            return random.randint(42, 69), random.randint(69, 420)

    def get_last_measurement(self):
        return self.ad_0_history[-1], self.ad_1_history[-1]

    def set_number_of_measurement_points(self, value):
        self.number_of_measurement_points = value
