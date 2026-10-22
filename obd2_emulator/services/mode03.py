"""Mode $03 — request emission-related diagnostic trouble codes.

ISO 15765-4 response (J1979 §8.3):
  43 <n> <DTC_hi> <DTC_lo> …   (n DTCs, 2 bytes each)
"""

from __future__ import annotations

from obd2_emulator.services.dtc_codec import encode_dtc
from obd2_emulator.state import DiagnosticsState


def handle_mode03(request: bytes, diagnostics: DiagnosticsState) -> bytes | None:
    if not request or request[0] != 0x03:
        return None
    codes = diagnostics.list_codes()
    out = bytearray([0x43, len(codes) & 0xFF])
    for code in codes:
        out.extend(encode_dtc(code))
    return bytes(out)
