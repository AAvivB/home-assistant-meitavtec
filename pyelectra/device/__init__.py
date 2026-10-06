from __future__ import annotations

from typing import Any

from .const import OperationMode

REG_POWER = 1000
REG_MODE = 1001
REG_FAN = 1004
REG_SETPOINT = 1007
REG_ROOM_TEMP = 1011


class MeitavAirConditioner:
    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.regdate: str = data["regdate"]
        self.model = data["model"]
        self.mac: str = data["mac"]
        self.serial_number: str = data["sn"]
        self.manufactor: str = data["manufactor"]
        self.type: str = data["deviceTypeName"]
        self.status: str = data["status"]
        self.token: str = data["deviceToken"]
        self._time_delta: int = 0
        self.features: list = []
        self.collected_measure: int | None = None
        self._regs: dict[int, str] = {
            REG_POWER: "0",
            REG_MODE: str(OperationMode.MODE_COOL),
            REG_FAN: str(OperationMode.FAN_SPEED_AUTO),
            REG_SETPOINT: "24",
        }

    def is_disconnected(self, thresh_sec: int = 60) -> bool:
        return self._time_delta > thresh_sec

    def update_features(self) -> None:
        pass

    def get_sensor_temperature(self) -> int | None:
        return self.collected_measure

    def get_mode(self) -> int:
        return int(float(self._regs[REG_MODE]))

    def set_mode(self, mode: int) -> None:
        if mode in (OperationMode.MODE_FAN, OperationMode.MODE_COOL,
                    OperationMode.MODE_HEAT, OperationMode.MODE_AUTO):
            self._regs[REG_MODE] = str(mode)

    def is_on(self) -> bool:
        return self._regs[REG_POWER] == "1"

    def turn_on(self) -> None:
        self._regs[REG_POWER] = "1"

    def turn_off(self) -> None:
        self._regs[REG_POWER] = "0"

    def get_temperature(self) -> int:
        return int(float(self._regs[REG_SETPOINT]))

    def set_temperature(self, val: int) -> None:
        self._regs[REG_SETPOINT] = str(val)

    def get_fan_speed(self) -> int:
        return int(float(self._regs[REG_FAN]))

    def set_fan_speed(self, speed: int) -> None:
        if speed in (OperationMode.FAN_SPEED_AUTO, OperationMode.FAN_SPEED_LOW,
                     OperationMode.FAN_SPEED_MED, OperationMode.FAN_SPEED_HIGH):
            self._regs[REG_FAN] = str(speed)

    def update_operation_states(self, data: dict[str, Any]) -> None:
        self._time_delta = data["timeDelta"]
        reg_list_str: str = data["commandJson"]["REG_LIST"]
        # Format: "REG_LIST 1011=25.00;1000=0;1007=23;..."
        regs_part = reg_list_str[len("REG_LIST "):]
        for pair in regs_part.split(";"):
            if "=" in pair:
                reg_id, value = pair.split("=", 1)
                self._regs[int(reg_id.strip())] = value.strip()

        if REG_ROOM_TEMP in self._regs:
            self.collected_measure = int(float(self._regs[REG_ROOM_TEMP]))

    def get_operation_state(self) -> str:
        return (
            f"REG_WRITE "
            f"1004={self._regs[REG_FAN]};"
            f"1000={self._regs[REG_POWER]};"
            f"1001={self._regs[REG_MODE]};"
            f"1007={self._regs[REG_SETPOINT]};"
            "1024=0;1027=1;1035=0;"
        )


# Backward-compat alias used by api/__init__.py
ElectraAirConditioner = MeitavAirConditioner
