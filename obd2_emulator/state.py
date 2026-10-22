"""Live OBD-II emulator state (PIDs, DTCs, vehicle info)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class DtcEntry:
    """One emission-related DTC (SAE J2012 style code, e.g. P0301)."""

    code: str
    description: str = ""

    def normalized(self) -> str:
        return self.code.strip().upper()


@dataclass
class LiveSignalState:
    """Mode $01 live values — named starters + extensible PID value map."""

    engine_rpm: float = 800.0
    vehicle_speed_kph: float = 0.0
    coolant_c: float = 90.0
    throttle_pct: float = 0.0
    mil_on: bool = False
    dtc_count: int = 0
    monitor_status_b: int = 0x07
    monitor_status_c: int = 0x00
    monitor_status_d: int = 0x00
    # Extra engineering values keyed by signal name (Annex B)
    pid_values: dict[str, float | int] = field(default_factory=dict)
    # Optional raw payload overrides by PID number
    raw_overrides: dict[int, bytes] = field(default_factory=dict)
    _listeners: list[Callable[[], None]] = field(default_factory=list, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    # Named field aliases used by CLI / older code
    _NAMED = frozenset(
        {
            "engine_rpm",
            "vehicle_speed_kph",
            "coolant_c",
            "throttle_pct",
            "mil_on",
            "dtc_count",
            "monitor_status_b",
            "monitor_status_c",
            "monitor_status_d",
        }
    )

    def on_change(self, cb: Callable[[], None]) -> None:
        with self._lock:
            self._listeners.append(cb)

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:
                pass

    def get_pid(self, key: str, default: float | int = 0) -> float | int:
        with self._lock:
            if key in self._NAMED:
                return getattr(self, key)  # type: ignore[no-any-return]
            if key in self.pid_values:
                return self.pid_values[key]
            return default

    def set_pid(self, key: str, value: float | int | bool) -> None:
        with self._lock:
            if key in self._NAMED:
                setattr(self, key, value)
            else:
                self.pid_values[key] = value  # type: ignore[assignment]
            self._notify()

    def set(self, key: str, value: float | int | bool) -> None:
        """Backward-compatible setter (named fields or pid_values)."""
        self.set_pid(key, value)

    def set_raw(self, pid: int, data: bytes) -> None:
        with self._lock:
            self.raw_overrides[int(pid) & 0xFF] = bytes(data)
            self._notify()

    def clear_raw(self, pid: int) -> None:
        with self._lock:
            self.raw_overrides.pop(int(pid) & 0xFF, None)
            self._notify()

    def snapshot(self) -> dict[str, float | int | bool]:
        with self._lock:
            out: dict[str, float | int | bool] = {
                "engine_rpm": float(self.engine_rpm),
                "vehicle_speed_kph": float(self.vehicle_speed_kph),
                "coolant_c": float(self.coolant_c),
                "throttle_pct": float(self.throttle_pct),
                "mil_on": bool(self.mil_on),
                "dtc_count": int(self.dtc_count),
            }
            out.update(self.pid_values)
            return out


@dataclass
class DiagnosticsState:
    """Mode $03 / $04 stored emission-related DTCs."""

    dtcs: list[DtcEntry] = field(default_factory=list)
    _listeners: list[Callable[[], None]] = field(default_factory=list, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def on_change(self, cb: Callable[[], None]) -> None:
        with self._lock:
            self._listeners.append(cb)

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:
                pass

    def list_codes(self) -> list[str]:
        with self._lock:
            return [d.normalized() for d in self.dtcs]

    def snapshot(self) -> list[dict[str, str]]:
        with self._lock:
            return [
                {"code": d.normalized(), "description": d.description}
                for d in self.dtcs
            ]

    def add(self, code: str, description: str = "") -> None:
        code_n = code.strip().upper()
        if not code_n:
            raise ValueError("empty DTC code")
        with self._lock:
            for d in self.dtcs:
                if d.normalized() == code_n:
                    d.description = description or d.description
                    self._notify()
                    return
            self.dtcs.append(DtcEntry(code=code_n, description=description))
            self._notify()

    def remove(self, code: str) -> bool:
        code_n = code.strip().upper()
        with self._lock:
            before = len(self.dtcs)
            self.dtcs = [d for d in self.dtcs if d.normalized() != code_n]
            changed = len(self.dtcs) != before
            if changed:
                self._notify()
            return changed

    def clear(self) -> None:
        with self._lock:
            if not self.dtcs:
                return
            self.dtcs.clear()
            self._notify()

    def replace(self, entries: list[DtcEntry]) -> None:
        with self._lock:
            self.dtcs = [
                DtcEntry(code=e.code.strip().upper(), description=e.description)
                for e in entries
            ]
            self._notify()


@dataclass
class VehicleInfo:
    """Mode $09 vehicle information (VIN / CALID)."""

    vin: str = "1HGCM82633A004352"
    calid: str = "OBD2EMU-CAL-0001"
    _listeners: list[Callable[[], None]] = field(default_factory=list, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def on_change(self, cb: Callable[[], None]) -> None:
        with self._lock:
            self._listeners.append(cb)

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:
                pass

    def set_vin(self, vin: str) -> None:
        v = vin.strip().upper()
        if len(v) != 17:
            raise ValueError("VIN must be exactly 17 characters")
        with self._lock:
            self.vin = v
            self._notify()

    def set_calid(self, calid: str) -> None:
        c = calid.strip()
        if not c:
            raise ValueError("CALID must be non-empty")
        if len(c) > 16:
            raise ValueError("CALID max 16 ASCII characters")
        with self._lock:
            self.calid = c
            self._notify()

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            return {"vin": self.vin, "calid": self.calid}


def sync_mil_from_diagnostics(
    signals: LiveSignalState, diagnostics: DiagnosticsState
) -> None:
    """Keep Mode $01 PID $01 DTC count / MIL aligned with stored DTCs."""
    codes = diagnostics.list_codes()
    n = len(codes)
    signals.set("dtc_count", n)
    if n == 0:
        signals.set("mil_on", False)
    elif not signals.mil_on and n > 0:
        signals.set("mil_on", True)
