"""Load TOML ECU configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from obd2_emulator.bus.detect import EmulationMode
from obd2_emulator.state import (
    DiagnosticsState,
    DtcEntry,
    LiveSignalState,
    VehicleInfo,
    sync_mil_from_diagnostics,
)

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


@dataclass
class BusConfig:
    bitrate: int = 500_000
    request_id: int = 0x7E0
    response_id: int = 0x7E8
    mode: EmulationMode = EmulationMode.VIRTUAL
    channel: str | None = None


@dataclass
class EmulatorConfig:
    bus: BusConfig = field(default_factory=BusConfig)
    signals: LiveSignalState = field(default_factory=LiveSignalState)
    diagnostics: DiagnosticsState = field(default_factory=DiagnosticsState)
    vehicle: VehicleInfo = field(default_factory=VehicleInfo)

    @property
    def vin(self) -> str:
        return self.vehicle.vin


def _as_int(v: Any, default: int) -> int:
    if v is None:
        return default
    if isinstance(v, str):
        return int(v, 0)
    return int(v)


def load_config(path: str | Path) -> EmulatorConfig:
    raw = Path(path).read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    bus_raw = data.get("bus", {}) or {}
    live = data.get("live", {}) or {}
    vehicle_raw = data.get("vehicle", {}) or {}
    diag_raw = data.get("diagnostics", {}) or {}

    mode_s = str(bus_raw.get("mode", "virtual")).lower()
    mode = EmulationMode.REAL if mode_s == "real" else EmulationMode.VIRTUAL

    bus = BusConfig(
        bitrate=_as_int(bus_raw.get("bitrate"), 500_000),
        request_id=_as_int(bus_raw.get("request_id"), 0x7E0),
        response_id=_as_int(bus_raw.get("response_id"), 0x7E8),
        mode=mode,
        channel=bus_raw.get("channel"),
    )
    signals = LiveSignalState(
        engine_rpm=float(live.get("engine_rpm", 800.0)),
        vehicle_speed_kph=float(live.get("vehicle_speed_kph", 0.0)),
        coolant_c=float(live.get("coolant_c", 90.0)),
        throttle_pct=float(live.get("throttle_pct", 0.0)),
        mil_on=bool(live.get("mil_on", False)),
        dtc_count=int(live.get("dtc_count", 0)),
    )

    vin = str(vehicle_raw.get("vin", "1HGCM82633A004352"))
    calid = str(vehicle_raw.get("calid", "OBD2EMU-CAL-0001"))
    vehicle = VehicleInfo(vin=vin[:17], calid=calid[:16])

    diagnostics = DiagnosticsState()
    dtc_rows = diag_raw.get("dtc") or data.get("diagnostics.dtc") or []
    # TOML [[diagnostics.dtc]] → data["diagnostics"]["dtc"] list
    if isinstance(dtc_rows, list):
        for row in dtc_rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("code", "")).strip()
            if not code:
                continue
            diagnostics.add(code, str(row.get("description", "")))

    # Align PID $01 with configured DTCs unless live explicitly set a count
    if diagnostics.list_codes() and "dtc_count" not in live:
        sync_mil_from_diagnostics(signals, diagnostics)
    elif diagnostics.list_codes():
        signals.set("dtc_count", len(diagnostics.list_codes()))

    return EmulatorConfig(
        bus=bus, signals=signals, diagnostics=diagnostics, vehicle=vehicle
    )
