"""Mode $09 — vehicle information (VIN / CALID) for ISO 15765-4.

Annex G / J1979 §8.9:
  InfoType $00 — supported bitmask (Annex A layout)
  InfoType $02 — VIN: 17 ASCII, one CAN response, no filler
  InfoType $04 — CALID: 16 ASCII per item (pad unused with $00)

CAN response shape (Table 212):
  49 <ITID> <NOfDataItems> <data…>
"""

from __future__ import annotations

from obd2_emulator.services.mode01 import supported_pid_bitmask_01_20
from obd2_emulator.state import VehicleInfo

# Core M5 set (message-count ITIDs not required on ISO 15765-4)
CORE_INFOTYPES: frozenset[int] = frozenset({0x02, 0x04})


def encode_infotype(itid: int, vehicle: VehicleInfo) -> bytes | None:
    """Return data bytes after SID+ITID for one InfoType, or None if unsupported."""
    if itid == 0x00:
        # Annex A bitmask for $01–$20
        return supported_pid_bitmask_01_20(CORE_INFOTYPES)

    if itid == 0x02:
        vin = vehicle.vin.strip().upper()
        if len(vin) != 17:
            vin = (vin + "?" * 17)[:17]
        # NOfDataItems = 1 VIN, then 17 ASCII (no filler on ISO 15765-4)
        return bytes([0x01]) + vin.encode("ascii", "replace")

    if itid == 0x04:
        cal = vehicle.calid.strip()[:16]
        # Pad to 16 with $00 at end per Annex G
        raw = cal.encode("ascii", "replace")
        raw = raw + b"\x00" * (16 - len(raw))
        return bytes([0x01]) + raw

    return None


def handle_mode09(request: bytes, vehicle: VehicleInfo) -> bytes | None:
    if not request or request[0] != 0x09:
        return None
    if len(request) < 2:
        return None
    out = bytearray([0x49])
    for itid in request[1:]:
        data = encode_infotype(int(itid), vehicle)
        if data is None:
            continue
        out.append(int(itid) & 0xFF)
        out.extend(data)
    if len(out) == 1:
        return None
    return bytes(out)
