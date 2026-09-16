"""sounddevice query helpers for listing and resolving audio devices."""

from __future__ import annotations

from versascribe import DeviceNotFoundError


def list_devices() -> list[dict]:
    import sounddevice as sd

    devices = sd.query_devices()
    result = []
    for i, d in enumerate(devices):
        result.append(
            {
                "index": i,
                "name": d["name"],
                "max_input_channels": d["max_input_channels"],
                "max_output_channels": d["max_output_channels"],
                "default_samplerate": d["default_samplerate"],
            }
        )
    return result


def find_device(name: str) -> int:
    """Return device index for the first input device whose name contains `name`."""
    import sounddevice as sd

    devices = sd.query_devices()
    name_lower = name.lower()
    for i, d in enumerate(devices):
        if name_lower in d["name"].lower() and d["max_input_channels"] > 0:
            return i
    raise DeviceNotFoundError(
        f"No input device matching '{name}' found. "
        f"Available input devices:\n"
        + "\n".join(
            f"  [{i}] {d['name']}"
            for i, d in enumerate(devices)
            if d["max_input_channels"] > 0
        )
    )


def is_device_available(name: str) -> bool:
    try:
        find_device(name)
        return True
    except DeviceNotFoundError:
        return False
