"""Mode $04 — clear/reset emission-related diagnostic information.

Positive response: single byte 0x44 (J1979 §8.4).
"""

from __future__ import annotations

from obd2_emulator.state import DiagnosticsState, LiveSignalState, sync_mil_from_diagnostics


def handle_mode04(
    request: bytes,
    diagnostics: DiagnosticsState,
    signals: LiveSignalState,
) -> bytes | None:
    if not request or request[0] != 0x04:
        return None
    diagnostics.clear()
    sync_mil_from_diagnostics(signals, diagnostics)
    return bytes([0x44])
