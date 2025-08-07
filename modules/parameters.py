from pathlib import Path


# File structure
project_dir: Path = Path('.').parent  # Path to the root directory
output_path: Path = project_dir / 'DataOutput'
output_path_1d = output_path / "data_1D"
output_path_3d = output_path / "data_3D"


# Logger
logging_configs_path: Path = project_dir / 'logging_configs'
logs_folder_path: Path = project_dir / 'logs'
default_log_config: str = 'default_log_config.json'


# Motor parameters
global_polling_rate = 200
motor_1_limits = (270, 90)  # (Counter-Clockwise, Clockwise) limits of the motor 1 in [deg].
motor_2_limits = (0, 270)  # (Counter-Clockwise, Clockwise) limits of the motor 2 in [deg].
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

# By default, use the default configuration of the logger. Edit this path if custom logger is provided.
logger_config_path: Path = logging_configs_path / default_log_config

logger_backup_count: int = 3  # Logger creates at most 3 backup log files.
# Log file is backed up when it exceeds its size.
# After reaching this size, the full log file is backed up and a new log file is started.
logger_max_size: int = 1000000

# GUI
gui_update_rate = 500  # [ms]  How often does the information on the screen updates (such as motor position etc.)
