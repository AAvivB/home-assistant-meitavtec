from dataclasses import dataclass

MAX_TEMP = 30
MIN_TEMP = 10


@dataclass
class OperationMode:
    MODE_FAN = 0
    MODE_COOL = 1
    MODE_HEAT = 2
    MODE_AUTO = 3
    FAN_SPEED_AUTO = 0
    FAN_SPEED_LOW = 1
    FAN_SPEED_MED = 2
    FAN_SPEED_HIGH = 3
    ON = 1
    OFF = 0
