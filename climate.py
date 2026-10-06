"""Support for the Meitav Tec climate."""

from __future__ import annotations

from datetime import timedelta
import logging
import time
from typing import Any

from .pyelectra.api import STATUS_SUCCESS, Attributes, ElectraAPI, ElectraApiError
from .pyelectra.device import MeitavAirConditioner, OperationMode
from .pyelectra.device.const import MAX_TEMP, MIN_TEMP

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.logbook import async_log_entry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ElectraSmartConfigEntry
from .const import (
    API_DELAY,
    CONSECUTIVE_FAILURE_THRESHOLD,
    DOMAIN,
    SCAN_INTERVAL_SEC,
    SIGNAL_STATE_UPDATED,
    UNAVAILABLE_THRESH_SEC,
)

FAN_MEITAV_TO_HASS = {
    OperationMode.FAN_SPEED_AUTO: FAN_AUTO,
    OperationMode.FAN_SPEED_LOW: FAN_LOW,
    OperationMode.FAN_SPEED_MED: FAN_MEDIUM,
    OperationMode.FAN_SPEED_HIGH: FAN_HIGH,
}

FAN_HASS_TO_MEITAV = {
    FAN_AUTO: OperationMode.FAN_SPEED_AUTO,
    FAN_LOW: OperationMode.FAN_SPEED_LOW,
    FAN_MEDIUM: OperationMode.FAN_SPEED_MED,
    FAN_HIGH: OperationMode.FAN_SPEED_HIGH,
}

HVAC_MODE_MEITAV_TO_HASS = {
    OperationMode.MODE_COOL: HVACMode.COOL,
    OperationMode.MODE_HEAT: HVACMode.HEAT,
    OperationMode.MODE_FAN: HVACMode.FAN_ONLY,
    OperationMode.MODE_AUTO: HVACMode.AUTO,
}

HVAC_MODE_HASS_TO_MEITAV = {
    HVACMode.COOL: OperationMode.MODE_COOL,
    HVACMode.HEAT: OperationMode.MODE_HEAT,
    HVACMode.FAN_ONLY: OperationMode.MODE_FAN,
    HVACMode.AUTO: OperationMode.MODE_AUTO,
}

MEITAV_FAN_MODES = [FAN_AUTO, FAN_HIGH, FAN_MEDIUM, FAN_LOW]
MEITAV_HVAC_MODES = [
    HVACMode.OFF,
    HVACMode.HEAT,
    HVACMode.COOL,
    HVACMode.FAN_ONLY,
    HVACMode.AUTO,
]

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL_SEC)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectraSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add Meitav AC devices."""
    api = entry.runtime_data

    _LOGGER.debug("Discovered %i Meitav devices", len(api.devices))
    async_add_entities(
        (MeitavClimateEntity(device, api) for device in api.devices), True
    )


class MeitavClimateEntity(ClimateEntity):
    """Define a Meitav Tec climate entity."""

    _attr_fan_modes = MEITAV_FAN_MODES
    _attr_target_temperature_step = 1
    _attr_max_temp = MAX_TEMP
    _attr_min_temp = MIN_TEMP
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = MEITAV_HVAC_MODES
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, device: MeitavAirConditioner, api: ElectraAPI) -> None:
        """Initialize Meitav climate entity."""
        self._api = api
        self._ac_device = device
        self._attr_unique_id = device.mac
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._ac_device.mac)},
            name=device.name,
            model=self._ac_device.model,
            manufacturer=self._ac_device.manufactor,
        )

        self._last_state_update = 0
        self._consecutive_failures = 0
        self._skip_update = True
        self._was_available = True

        _LOGGER.debug("Added %s Meitav AC device", device.name)

    @property
    def available(self) -> bool:
        """Return True if the AC is available."""
        return (
            not self._ac_device.is_disconnected(UNAVAILABLE_THRESH_SEC)
            and super().available
        )

    async def async_update(self) -> None:
        """Update Meitav device."""
        if self._last_state_update and int(time.time()) < (
            self._last_state_update + API_DELAY
        ):
            _LOGGER.debug("Skipping state update, keeping old values")
            return

        self._last_state_update = 0

        try:
            if self._skip_update:
                self._skip_update = False
            else:
                await self._api.get_last_telemtry(self._ac_device)

            if not self.available:
                if self._was_available:
                    _LOGGER.warning(
                        "Meitav AC %s (%s) is not available, check its status in the Meitav Tec mobile app",
                        self.name,
                        self._ac_device.mac,
                    )
                    self._was_available = False
                return

            if not self._was_available:
                _LOGGER.debug(
                    "%s (%s) is now available",
                    self._ac_device.mac,
                    self.name,
                )
                self._was_available = True

            _LOGGER.debug(
                "%s (%s) state updated: %s",
                self._ac_device.mac,
                self.name,
                self._ac_device.__dict__,
            )
        except ElectraApiError as exp:
            self._consecutive_failures += 1
            _LOGGER.warning(
                "Failed to get %s state: %s (try #%i since last success), keeping old state",
                self.name,
                exp,
                self._consecutive_failures,
            )

            if self._consecutive_failures >= CONSECUTIVE_FAILURE_THRESHOLD:
                raise HomeAssistantError(
                    f"Failed to get {self.name} state: {exp} for the {self._consecutive_failures} time",
                ) from ElectraApiError

        self._consecutive_failures = 0
        self._update_device_attrs()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set AC fan mode."""
        self._ac_device.set_fan_speed(FAN_HASS_TO_MEITAV[fan_mode])
        await self._async_operate_ac()
        async_log_entry(
            self.hass,
            self._ac_device.name,
            f"set fan speed to {fan_mode}",
            DOMAIN,
            self.entity_id,
            self._context,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode."""
        if hvac_mode == HVACMode.OFF:
            self._ac_device.turn_off()
        else:
            self._ac_device.set_mode(HVAC_MODE_HASS_TO_MEITAV[hvac_mode])
            self._ac_device.turn_on()

        await self._async_operate_ac()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            raise ValueError("No target temperature provided")

        self._ac_device.set_temperature(int(temperature))
        await self._async_operate_ac()
        async_log_entry(
            self.hass,
            self._ac_device.name,
            f"set target temperature to {int(temperature)}°C",
            DOMAIN,
            self.entity_id,
            self._context,
        )

    async def async_turn_on(self) -> None:
        """Power on the AC, restoring the last active mode."""
        self._ac_device.turn_on()
        await self._async_operate_ac()

    def _update_device_attrs(self) -> None:
        self._attr_fan_mode = FAN_MEITAV_TO_HASS[self._ac_device.get_fan_speed()]
        self._attr_current_temperature = self._ac_device.get_sensor_temperature()
        self._attr_target_temperature = self._ac_device.get_temperature()

        self._attr_hvac_mode = (
            HVACMode.OFF
            if not self._ac_device.is_on()
            else HVAC_MODE_MEITAV_TO_HASS[self._ac_device.get_mode()]
        )

        async_dispatcher_send(
            self.hass, SIGNAL_STATE_UPDATED.format(self._ac_device.mac)
        )

    async def _async_operate_ac(self) -> None:
        """Send HVAC parameters to API."""
        # Block polls immediately so a concurrent update doesn't overwrite the
        # optimistic state while we wait for the server response
        self._last_state_update = int(time.time())

        self._update_device_attrs()
        self._async_write_ha_state()

        try:
            resp = await self._api.set_state(self._ac_device)
        except ElectraApiError as exp:
            raise HomeAssistantError(
                f"Error communicating with Meitav API: {exp}"
            ) from exp

        if not (
            resp[Attributes.STATUS] == STATUS_SUCCESS
            and resp[Attributes.DATA][Attributes.RES] == STATUS_SUCCESS
        ):
            raise HomeAssistantError(f"Failed to update {self.name}, error: {resp}")
