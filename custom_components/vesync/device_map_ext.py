"""Extra pyvesync device mappings not yet in upstream pyvesync.

pyvesync resolves devices by scanning the module-level ``purifier_modules``
list on every lookup, so appending to it before the first device list call
makes the new models discoverable without forking the library.
"""

import logging

from pyvesync import device_map
from pyvesync.const import (
    PurifierAutoPreference,
    PurifierFeatures,
    PurifierModes,
)
from pyvesync.device_map import PurifierMap

from . import pet_pro

_LOGGER = logging.getLogger(__name__)

# Levoit Vital Pet Pro. Uses the Vital 100S/200S (V2 bypass) API with a
# tolerant status parser, see pet_pro.py. The bare "LAP-P501S" entry also lets
# pyvesync's prefix fallback match any regional suffix not listed here.
VITAL_PET_PRO = PurifierMap(
    class_name="VeSyncAirPetPro",
    module=pet_pro,
    dev_types=[
        "LAP-P501S",
        "LAP-P501S-WUS",
        "LAP-P501S-AUS",
        "LAP-P501S-WUSR",
        "LAP-P501S-AUSR",
        "LAP-P501S-WEU",
        "LAP-P501S-AEUR",
    ],
    modes=[
        PurifierModes.SLEEP,
        PurifierModes.MANUAL,
        PurifierModes.AUTO,
        PurifierModes.PET,
    ],
    features=[PurifierFeatures.AIR_QUALITY],
    fan_levels=list(range(1, 5)),
    device_alias="Vital Pet Pro",
    auto_preferences=[
        PurifierAutoPreference.DEFAULT,
        PurifierAutoPreference.EFFICIENT,
        PurifierAutoPreference.QUIET,
    ],
    model_display="LAP-P501S Series",
    model_name="Vital Pet Pro",
    setup_entry="LAP-P501S",
)

EXTRA_PURIFIERS = [VITAL_PET_PRO]


def register_extra_devices() -> None:
    """Add extra device maps to pyvesync if it doesn't already know them."""
    for extra in EXTRA_PURIFIERS:
        if device_map.get_purifier(extra.setup_entry) is not None:
            _LOGGER.debug("pyvesync already supports %s", extra.model_name)
            continue
        device_map.purifier_modules.append(extra)
        _LOGGER.debug("Registered %s with pyvesync", extra.model_name)
