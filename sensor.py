"""Meitav Tec sensors — target temperature and fan speed."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ElectraSmartConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .pyelectra.device import MeitavAirConditioner
from .pyelectra.device.const import OperationMode

_LOGGER = logging.getLogger(__name__)

FAN_SPEED_LABELS = {
    OperationMode.FAN_SPEED_AUTO: "Auto",
    OperationMode.FAN_SPEED_LOW: "Low",
    OperationMode.FAN_SPEED_MED: "Medium",
    OperationMode.FAN_SPEED_HIGH: "High",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectraSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add Meitav Tec sensor entities."""
    api = entry.runtime_data
    entities: list[SensorEntity] = []
    for device in api.devices:
        entities.append(MeitavTargetTemperatureSensor(device))
        entities.append(MeitavFanSpeedSensor(device))
    async_add_entities(entities)


class _MeitavBaseSensor(SensorEntity):
    """Shared base for Meitav sensors — pushed by the climate entity, no polling."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, device: MeitavAirConditioner) -> None:
        self._device = device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac)},
            name=device.name,
            model=device.model,
            manufacturer=device.manufactor,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_STATE_UPDATED.format(self._device.mac),
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self._async_write_ha_state()


class MeitavTargetTemperatureSensor(_MeitavBaseSensor):
    """Tracks the temperature setpoint — useful for history graphs."""

    _attr_name = "Target temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-chevron-up"

    def __init__(self, device: MeitavAirConditioner) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{device.mac}_target_temp"

    @property
    def native_value(self) -> int | None:
        return self._device.get_temperature()


class MeitavFanSpeedSensor(_MeitavBaseSensor):
    """Tracks the fan speed setting — useful for history graphs."""

    _attr_name = "Fan speed"
    _attr_icon = "mdi:fan"

    def __init__(self, device: MeitavAirConditioner) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{device.mac}_fan_speed"

    @property
    def native_value(self) -> str | None:
        return FAN_SPEED_LABELS.get(self._device.get_fan_speed())
