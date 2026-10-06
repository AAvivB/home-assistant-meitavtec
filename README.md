# Meitav Tec for Home Assistant

A custom Home Assistant integration for controlling Meitav Tec air conditioners through the vendor's cloud API. The integration uses phone-number and SMS one-time-password authentication, discovers air conditioners on the account, and exposes climate controls and temperature/fan-speed sensors.

## Installation

Copy this repository into the Home Assistant custom integrations directory so the files are at `custom_components/meitav_tec/`:

```text
<config>/custom_components/meitav_tec/
```

Restart Home Assistant, then go to **Settings → Devices & services → Add integration** and search for **Meitav Tec**. Enter the phone number registered with the Meitav Tec app and the one-time password sent by SMS.

The integration requires internet access and a Meitav Tec account with the air conditioner registered in the vendor's app.

## Entities

Each discovered air conditioner provides a climate entity with on/off, operating mode, target temperature, and fan-speed controls. It also provides target-temperature and fan-speed sensors for history and automations. The integration polls the cloud service; control and state updates depend on the vendor API being available.

## How this repository relates to its upstream projects

This repository combines code derived from two projects:

- [Home Assistant Core's Electra Smart integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/electrasmart) provides the Home Assistant integration structure: config flow, climate platform, entity setup, and translation strings.
- [jafar-atili/pyElectra](https://github.com/jafar-atili/pyElectra) provides the Python client/API structure for authentication, cloud requests, device discovery, and climate commands.

The code here adapts those foundations for Meitav Tec. The integration domain and user-facing names are `meitav_tec` / Meitav Tec. The client uses the Meitav service endpoint and provider/command identifiers, authenticates with SMS OTP, and has a Meitav-specific device model and register mapping. In particular, the device implementation parses telemetry registers and constructs register-write commands for power, mode, fan speed, and setpoint. Home Assistant entity mappings and the additional sensors are also tailored to this integration.

This is an independent community integration. It is not an official Home Assistant or Meitav Tec project, and the upstream Electra integration should not be assumed to work with Meitav devices.

## Privacy

The integration stores the API token and generated device identifier in the Home Assistant config entry after authentication. It sends the phone number, OTP, and device identifier to the vendor's cloud API during setup, then uses the token and device identifier for subsequent requests. No Home Assistant URL, access token, or local configuration is needed by this integration.

## License and attribution

See [LICENSE](LICENSE). The repository contains adaptations based on the two upstream projects listed above; their respective notices and license terms apply to the portions derived from them.
