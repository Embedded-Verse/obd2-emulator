"""EmulatorSession: START / STOP / RESET, ISO-TP service loop, live stats.

Listens on ISO 15765-4 physical + functional IDs (11-bit and 29-bit) so
ELM327 ATSP0/6/7/8/9 style testers receive answers on 7E8 / 18DAF110.

Graceful hardware: tear down ISO-TP → shutdown bus → force-release USB handle →
settle before reopen. Always leave adapters unlocked on stop/exit.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import can

from obd2_emulator.bus.detect import DetectedChannel, EmulationMode, open_bus
from obd2_emulator.isotp.endpoints import (
    IsotpIds,
    make_ecu_endpoint_specs,
    make_stack,
)
from obd2_emulator.services.registry import ServiceRegistry
from obd2_emulator.state import DiagnosticsState, LiveSignalState, VehicleInfo

_BITS_PER_FRAME = 130
_USB_SETTLE_S = 0.50
_JOIN_TIMEOUT_S = 3.0


def force_release_bus(bus: can.BusABC | None) -> None:
    """Ensure USB backends fully release the device handle."""
    if bus is None:
        return
    try:
        bus.shutdown()
    except Exception:
        pass

    for attr in ("_device", "device", "gs_usb"):
        device = getattr(bus, attr, None)
        if device is None:
            continue
        try:
            if hasattr(device, "is_open") and not device.is_open:
                continue
        except Exception:
            pass
        for closer in ("close", "dispose", "release"):
            if hasattr(device, closer):
                try:
                    getattr(device, closer)()
                except Exception:
                    pass
                break

    for attr in ("_device", "device", "gs_usb", "channel"):
        if hasattr(bus, attr):
            try:
                setattr(bus, attr, None)
            except Exception:
                pass


@dataclass
class SessionStats:
    running: bool = False
    uptime_s: float = 0.0
    tx_count: int = 0
    rx_count: int = 0
    load_pct: float = 0.0
    bitrate: int = 500_000
    mode: EmulationMode = EmulationMode.VIRTUAL
    channel_label: str = ""
    request_id: int = 0x7E0
    response_id: int = 0x7E8


class _StatsListener(can.Listener):
    def __init__(self, on_rx: Any) -> None:
        self._on_rx = on_rx

    def on_message_received(self, msg: can.Message) -> None:
        self._on_rx()

    def on_error(self, exc: Exception) -> None:
        pass


class EmulatorSession:
    """OBD-II ECU emulator session (multi ISO-TP endpoints on one bus)."""

    def __init__(
        self,
        signals: LiveSignalState | None = None,
        *,
        diagnostics: DiagnosticsState | None = None,
        vehicle: VehicleInfo | None = None,
        bitrate: int = 500_000,
        mode: EmulationMode = EmulationMode.VIRTUAL,
        request_id: int = 0x7E0,
        response_id: int = 0x7E8,
        listen_functional: bool = True,
        listen_extended: bool = True,
    ) -> None:
        self.signals = signals or LiveSignalState()
        self.diagnostics = diagnostics or DiagnosticsState()
        self.vehicle = vehicle or VehicleInfo()
        self.registry = ServiceRegistry(
            self.signals, self.diagnostics, self.vehicle
        )
        self.bitrate = int(bitrate)
        self.mode = mode
        self.ids = IsotpIds(
            request_id=request_id,
            response_id=response_id,
            listen_functional=listen_functional,
            listen_extended=listen_extended,
        )

        self._lock = threading.RLock()
        self._stats_lock = threading.Lock()
        self._running = False
        self._bus: can.BusABC | None = None
        self._channel: DetectedChannel | None = None
        self._stacks: dict[str, Any] = {}
        self._reply_names: dict[str, str] = {}
        self._notifier: can.Notifier | None = None
        self._worker: threading.Thread | None = None
        self._stop_evt = threading.Event()
        self._started_at: float | None = None
        self._frozen_uptime = 0.0
        self._tx_count = 0
        self._rx_count = 0
        self._tx_window_start = 0.0
        self._tx_window_count = 0
        self._load_pct = 0.0

    @property
    def running(self) -> bool:
        return self._running

    def start(self, channel: DetectedChannel) -> None:
        with self._lock:
            if self._running:
                raise RuntimeError("Session already running — stop first")
            self._begin_locked(channel)

    def stop(self) -> None:
        with self._lock:
            if not self._running and self._bus is None:
                return
            self._stop_locked()

    def reset(self, channel: DetectedChannel | None = None) -> None:
        with self._lock:
            ch = channel or self._channel
            was_running = self._running
            if self._running or self._bus is not None:
                self._stop_locked()
            with self._stats_lock:
                self._tx_count = 0
                self._rx_count = 0
                self._load_pct = 0.0
                self._tx_window_count = 0
            self._frozen_uptime = 0.0
            if was_running and ch is not None:
                self._begin_locked(ch)

    def stats(self) -> SessionStats:
        with self._stats_lock:
            uptime = self._frozen_uptime
            if self._running and self._started_at is not None:
                uptime = time.monotonic() - self._started_at
            label = self._channel.label if self._channel else ""
            return SessionStats(
                running=self._running,
                uptime_s=uptime,
                tx_count=self._tx_count,
                rx_count=self._rx_count,
                load_pct=self._load_pct,
                bitrate=self.bitrate,
                mode=self.mode,
                channel_label=label,
                request_id=self.ids.request_id,
                response_id=self.ids.response_id,
            )

    def set_bitrate(self, bitrate: int) -> None:
        if self._running:
            raise RuntimeError("Stop the session before changing bitrate")
        self.bitrate = int(bitrate)

    def set_ids(self, request_id: int, response_id: int) -> None:
        if self._running:
            raise RuntimeError("Stop the session before changing CAN IDs")
        self.ids = IsotpIds(
            request_id=request_id,
            response_id=response_id,
            listen_functional=self.ids.listen_functional,
            listen_extended=self.ids.listen_extended,
            functional_id=self.ids.functional_id,
            ext_request_id=self.ids.ext_request_id,
            ext_response_id=self.ids.ext_response_id,
            ext_functional_id=self.ids.ext_functional_id,
        )

    def _begin_locked(self, channel: DetectedChannel) -> None:
        self.mode = channel.kind
        self._channel = channel
        self._stop_evt.clear()
        try:
            self._bus = open_bus(channel, bitrate=self.bitrate)
        except Exception:
            self._bus = None
            raise

        try:
            listener = _StatsListener(self._on_rx)
            self._notifier = can.Notifier(self._bus, [listener], timeout=0.1)
            self._stacks = {}
            self._reply_names = {}
            for spec in make_ecu_endpoint_specs(self.ids):
                stack = make_stack(self._bus, spec.address, notifier=self._notifier)
                stack.start()
                self._stacks[spec.name] = stack
                self._reply_names[spec.name] = spec.reply_name
            if not self._stacks:
                raise RuntimeError("No ISO-TP endpoints configured")
        except Exception:
            self._teardown_transport_locked()
            bus = self._bus
            self._bus = None
            force_release_bus(bus)
            raise

        now = time.monotonic()
        self._started_at = now
        with self._stats_lock:
            self._tx_count = 0
            self._rx_count = 0
            self._tx_window_start = now
            self._tx_window_count = 0
            self._load_pct = 0.0
        self._frozen_uptime = 0.0
        self._running = True
        self._worker = threading.Thread(
            target=self._service_loop, name="obd2-isotp", daemon=True
        )
        self._worker.start()

    def _service_loop(self) -> None:
        while not self._stop_evt.is_set():
            stacks = dict(self._stacks)
            reply_names = dict(self._reply_names)
            if not stacks:
                break
            got_any = False
            for name, stack in stacks.items():
                try:
                    payload = stack.recv(block=False)
                except Exception:
                    continue
                if not payload:
                    continue
                got_any = True
                try:
                    response = self.registry.handle(bytes(payload))
                except Exception:
                    continue
                if not response:
                    continue
                # Functional RX → physical TX so Flow Control arrives on 7E0 / 18DA10F1
                reply_name = reply_names.get(name, name)
                tx_stack = stacks.get(reply_name, stack)
                try:
                    tx_stack.send(response)
                    self._on_tx()
                except Exception:
                    pass
            if not got_any:
                time.sleep(0.005)

    def _teardown_transport_locked(self) -> None:
        self._stop_evt.set()
        worker = self._worker
        self._worker = None
        if worker is not None and worker.is_alive():
            self._lock.release()
            try:
                worker.join(timeout=_JOIN_TIMEOUT_S)
            finally:
                self._lock.acquire()

        stacks = list(self._stacks.values())
        self._stacks = {}
        self._reply_names = {}
        for stack in stacks:
            try:
                stack.stop()
            except Exception:
                pass

        notifier = self._notifier
        self._notifier = None
        if notifier is not None:
            try:
                notifier.stop(timeout=_JOIN_TIMEOUT_S)
            except Exception:
                try:
                    notifier.stop()
                except Exception:
                    pass

    def _stop_locked(self) -> None:
        if self._started_at is not None and self._running:
            self._frozen_uptime = time.monotonic() - self._started_at

        self._teardown_transport_locked()

        bus = self._bus
        iface = self._channel.interface if self._channel is not None else "virtual"
        self._bus = None
        self._running = False
        with self._stats_lock:
            self._load_pct = 0.0
        self._started_at = None

        closed_real = False
        if bus is not None:
            force_release_bus(bus)
            closed_real = iface != "virtual"

        if closed_real:
            self._lock.release()
            try:
                time.sleep(_USB_SETTLE_S)
            finally:
                self._lock.acquire()

    def _on_tx(self) -> None:
        with self._stats_lock:
            self._tx_count += 1
            self._tx_window_count += 1
            self._update_load_locked()

    def _on_rx(self) -> None:
        with self._stats_lock:
            self._rx_count += 1

    def _update_load_locked(self) -> None:
        now = time.monotonic()
        elapsed = now - self._tx_window_start
        if elapsed >= 0.5:
            bps = (self._tx_window_count * _BITS_PER_FRAME) / max(elapsed, 1e-6)
            self._load_pct = min(100.0, (bps / max(self.bitrate, 1)) * 100.0)
            self._tx_window_start = now
            self._tx_window_count = 0

    def __enter__(self) -> EmulatorSession:
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()
