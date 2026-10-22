"""Dispatch ISO-TP application payloads by J1979 service ID."""

from __future__ import annotations

from obd2_emulator.services import mode01, mode03, mode04, mode09
from obd2_emulator.state import DiagnosticsState, LiveSignalState, VehicleInfo


class ServiceRegistry:
    def __init__(
        self,
        state: LiveSignalState,
        diagnostics: DiagnosticsState | None = None,
        vehicle: VehicleInfo | None = None,
    ) -> None:
        self.state = state
        self.diagnostics = diagnostics or DiagnosticsState()
        self.vehicle = vehicle or VehicleInfo()

    def handle(self, payload: bytes) -> bytes | None:
        if not payload:
            return None
        sid = payload[0]
        if sid == 0x01:
            return mode01.handle_mode01(payload, self.state)
        if sid == 0x03:
            return mode03.handle_mode03(payload, self.diagnostics)
        if sid == 0x04:
            return mode04.handle_mode04(payload, self.diagnostics, self.state)
        if sid == 0x09:
            return mode09.handle_mode09(payload, self.vehicle)
        # Negative response: serviceNotSupported (0x11)
        return bytes([0x7F, sid, 0x11])
