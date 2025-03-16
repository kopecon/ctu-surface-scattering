# System libraries
import random

# Hardware libraries
import nidaqmx
from nidaqmx.constants import Edge, AcquisitionType


# NI-DAQmx 2025 Q1 has to be installed on the executing pc to run the scan.
# NI-DAQmx 2025 Q1 download: https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html?srsltid=AfmBOooJ-Ko5HpJHEr4yPzQEZKufBWdBc1JjWhomtdJ27QKXivgjvTBr#559060


def measure_scattering():
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
            sensor_data_1 = float(sensor_data[0])
            sensor_data_2 = float(sensor_data[1])

            return sensor_data_1, sensor_data_2
    except nidaqmx.errors.DaqNotFoundError:
        print("Controller not found. Returning random data.")
        return random.randint(0, 100), random.randint(101, 200)
