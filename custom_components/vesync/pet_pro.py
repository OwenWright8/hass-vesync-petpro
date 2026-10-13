"""Levoit Vital Pet Pro support on top of pyvesync's Vital (V2) purifier class.

The Pet Pro answers ``getPurifierStatus`` like the Vital 100S/200S but leaves
out fields such as ``lightDetectionSwitch``, which pyvesync's strict
``PurifierVitalDetailsResult`` model requires. This class reads the raw result
dict instead, so any missing field just leaves that state value unset.
"""

from __future__ import annotations

import logging
from typing import Any

from pyvesync.const import ConnectionStatus, DeviceStatus, PurifierModes
from pyvesync.devices.vesyncpurifier import VeSyncAirBaseV2
from pyvesync.utils.device_mixins import _get_inner_result
from pyvesync.utils.helpers import Helpers, Timer

_LOGGER = logging.getLogger(__name__)

# Device CIDs whose raw status payload has already been logged this run.
_LOGGED_PAYLOAD: set[str] = set()

# Candidate keys for the Pet Pro's VOC reading; the real name is unconfirmed.
_VOC_KEYS = ("TVOC", "tvoc", "VOC", "voc", "TVOCLevel", "VOCLevel")


def _int(result: dict[str, Any], key: str) -> int | None:
    value = result.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def pet_pro_value(device: object, key: str) -> Any:
    """Return a Pet Pro-only value, or None for any other device."""
    return getattr(device, "pet_pro_extra", {}).get(key)


class VeSyncAirPetPro(VeSyncAirBaseV2):
    """Levoit Vital Pet Pro (LAP-P501S).

    No ``__slots__`` here, so instances get a ``__dict__`` for ``pet_pro_extra``:
    readings pyvesync's PurifierState has no slot for.
    """

    pet_pro_extra: dict[str, Any]

    async def get_details(self) -> None:
        """Fetch purifier status and update state, tolerating missing fields."""
        r_dict = await self.call_bypassv2_api("getPurifierStatus")
        r_dict = Helpers.process_dev_response(_LOGGER, "get_details", self, r_dict)
        if r_dict is None:
            return
        result = _get_inner_result(self, _LOGGER, "get_details", r_dict)
        if not isinstance(result, dict):
            return

        if self.cid not in _LOGGED_PAYLOAD:
            _LOGGED_PAYLOAD.add(self.cid)
            _LOGGER.warning(
                "Vital Pet Pro status payload (please share to improve support): %s",
                result,
            )

        self._set_pet_pro_state(result)

    async def set_fan_speed(self, speed: int | None = None) -> bool:
        """Set manual fan speed, logging the raw reply if the device rejects it."""
        if speed is not None and speed not in self.fan_levels:
            _LOGGER.warning(
                "%s is invalid speed - valid speeds are %s", speed, self.fan_levels
            )
            return False
        if speed is None:
            speed = (
                self.fan_levels[0]
                if self.state.fan_level is None
                else Helpers.bump_level(self.state.fan_level, self.fan_levels)
            )

        payload = {"levelIdx": 0, "manualSpeedLevel": speed, "levelType": "wind"}
        r_dict = await self.call_bypassv2_api("setLevel", payload)
        outer = r_dict.get("result") if isinstance(r_dict, dict) else None
        inner_code = outer.get("code") if isinstance(outer, dict) else None
        if (
            Helpers.process_dev_response(_LOGGER, "set_fan_speed", self, r_dict) is None
            or inner_code not in (0, None)
        ):
            _LOGGER.warning(
                "Vital Pet Pro rejected setLevel %s (please share): %s", payload, r_dict
            )
            return False

        self.state.fan_set_level = speed
        self.state.fan_level = speed
        self.state.mode = PurifierModes.MANUAL
        self.state.device_status = DeviceStatus.ON
        self.state.connection_status = ConnectionStatus.ONLINE
        return True

    def _set_pet_pro_state(self, result: dict[str, Any]) -> None:
        state = self.state
        state.connection_status = ConnectionStatus.ONLINE
        state.device_status = DeviceStatus.from_int(_int(result, "powerSwitch"))
        if isinstance(result.get("workMode"), str):
            state.mode = result["workMode"]
        state.filter_life = _int(result, "filterLifePercent")

        fan_level = _int(result, "fanSpeedLevel")
        state.fan_level = 0 if fan_level == 255 else fan_level  # noqa: PLR2004
        state.fan_set_level = _int(result, "manualSpeedLevel")

        child_lock = _int(result, "childLockSwitch")
        state.child_lock = None if child_lock is None else bool(child_lock)

        state.air_quality_level = _int(result, "AQLevel")
        state.pm25 = _int(result, "PM25")
        state.pm1 = _int(result, "PM1")
        state.pm10 = _int(result, "PM10")
        state.aq_percent = _int(result, "AQPercent")
        state.voc = next(
            (v for k in _VOC_KEYS if (v := _int(result, k)) is not None), None
        )

        if "screenSwitch" in result:
            state.display_set_status = DeviceStatus.from_int(
                _int(result, "screenSwitch")
            )
        if "screenState" in result:
            state.display_status = DeviceStatus.from_int(_int(result, "screenState"))

        auto_pref = result.get("autoPreference")
        if isinstance(auto_pref, dict):
            state.auto_preference_type = auto_pref.get("autoPreferenceType")
            state.auto_room_size = auto_pref.get("roomSize")

        if (filter_open := _int(result, "filterOpenState")) is not None:
            state.filter_open_state = bool(filter_open)
        if (timer_remain := _int(result, "timerRemain")) and timer_remain > 0:
            state.timer = Timer(timer_remain, "off")

        auto_clean = result.get("autoCleanPreference")
        if not isinstance(auto_clean, dict):
            auto_clean = {}
        self.pet_pro_extra = {
            "odor_level": _int(result, "odorLevel"),
            "filter_days_remaining": _int(result, "filterRemainDay"),
            "auto_clean_state": _int(auto_clean, "autoCleanState"),
        }
