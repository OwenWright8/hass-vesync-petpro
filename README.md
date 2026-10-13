# VeSync (Vital Pet Pro fork)

A copy of Home Assistant's built-in `vesync` integration (from the `dev` branch, pyvesync 3.4.2)
that adds the **Levoit Vital Pet Pro (LAP-P501S)** air purifier.

Feature request: https://github.com/orgs/home-assistant/discussions/3802

## How it works

pyvesync only creates devices whose model code is in its device map. The Pet Pro
is missing, so the device never appears in Home Assistant. This fork's
`custom_components/vesync/device_map_ext.py` registers `LAP-P501S` (any regional
suffix) with pyvesync's `VeSyncAirBaseV2` class, the same one the Vital 100S/200S use.
Everything else is the stock integration.

Because it uses the `vesync` domain, it **overrides** the built-in integration.
Your existing VeSync config entry and entities stay as they are.

## Install

**HACS:** add this repo as a custom repository (category *Integration*), install it, then restart.

**Manual:** copy `custom_components/vesync` into `<config>/custom_components/`, then restart.

## Expected entities

| Entity | Source |
|---|---|
| Fan (on/off, speed 1–4, auto / sleep / pet presets) | `fan` |
| Filter life (%) | `sensor` |
| PM2.5, air quality | `sensor` |
| Display | `switch` |
| Child lock | `switch` |

**Not included:** TVOC and the Auto-Clean pre-filter scraper. pyvesync has no fields
for them, and adding them needs the device's raw API responses.

## Debugging

If the device still doesn't appear, or its values look wrong, turn on debug logging:

```yaml
logger:
  logs:
    pyvesync: debug
    custom_components.vesync: debug
```

Then download the integration's diagnostics. Look for:

- `Device type ... not found in device map`: the device reports a different model code.
  Add that code to `dev_types` in `device_map_ext.py`.
- `Invalid details model passed to _set_state`: the Pet Pro's API differs from the
  Vital series, so it needs its own pyvesync class.

## Removing

Once upstream pyvesync/Home Assistant supports the Pet Pro, delete
`custom_components/vesync` and restart to go back to the built-in integration.
