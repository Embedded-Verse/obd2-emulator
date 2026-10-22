"""CLI entry: --gui | interactive session for automation / ELM327 benches."""

from __future__ import annotations

import argparse
import atexit
import sys
import warnings

from obd2_emulator import __version__
from obd2_emulator.bus.detect import (
    DetectedChannel,
    EmulationMode,
    detect_hardware,
    find_channel,
)
from obd2_emulator.bus.session import EmulatorSession
from obd2_emulator.config import load_config
from obd2_emulator.state import sync_mil_from_diagnostics


def _quiet_third_party_noise() -> None:
    warnings.filterwarnings(
        "ignore",
        message=".*doesn't match a supported version.*",
        module="requests",
    )


def format_channel_table(
    channels: list[DetectedChannel],
    *,
    mode: EmulationMode | str,
) -> str:
    mode_s = mode.value if isinstance(mode, EmulationMode) else str(mode)
    title = "Virtual" if mode_s == "virtual" else "Real"
    lines = [f"Available {title} CAN channels ({len(channels)}):", ""]
    if not channels:
        lines.append("  (none found — plug in an adapter, or use --mode virtual)")
        return "\n".join(lines)
    lines.append("  #   Adapter")
    lines.append("  --  -----------------------------------------------")
    for i, ch in enumerate(channels, start=1):
        lines.append(f"  {i:<3} {ch.label}")
    lines.append("")
    lines.append("Example:")
    lines.append(
        f"  python -m obd2_emulator --config examples/ecu.toml "
        f"--mode {mode_s} --channel 1 --bitrate 500000"
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="obd2_emulator",
        description="SAE J1979 OBD-II Light-Vehicle ECU Emulator",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--gui", action="store_true", help="Open NiceGUI (default :8080)")
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--config", "-c", type=str, help="TOML ECU config")
    p.add_argument("--mode", choices=["real", "virtual"])
    p.add_argument("--channel", type=str, help="Channel number from --list-channels")
    p.add_argument(
        "--bitrate",
        type=int,
        choices=[125000, 250000, 500000, 1000000],
    )
    p.add_argument("--list-channels", "-l", action="store_true")
    p.add_argument("--no-start", action="store_true")
    return p


_HELP = """\
channels [real|virtual]  — list adapters
channel [N]              — select channel number
mode [real|virtual]      — show/set mode
bitrate [Hz]             — 125000|250000|500000|1000000
status                   — uptime / TX / RX / load
pid list | pid set <key> <value> | pid get <key>
  keys: engine_rpm … or signal names (maf_gps, odometer_km, …) or hex PID 0C
  pid meta [XX] — list catalog / one PID
dtc list | dtc add <CODE> [desc…] | dtc remove <CODE> | dtc clear
  demo: dtc add P0301 | dtc add P0420 | dtc add P0171
vin get | vin set <17chars>
calid get | calid set <≤16chars>
start | stop | reset | help | quit
"""


def main(argv: list[str] | None = None) -> int:
    _quiet_third_party_noise()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gui:
        from obd2_emulator.gui.app import run_gui

        run_gui(
            config_path=args.config,
            host=args.host,
            port=int(args.port),
            open_browser=not args.no_browser,
        )
        return 0

    mode = EmulationMode(args.mode) if args.mode else EmulationMode.VIRTUAL
    bitrate = args.bitrate or 500_000
    signals = None
    diagnostics = None
    vehicle = None
    request_id, response_id = 0x7E0, 0x7E8
    preferred = args.channel

    if args.config:
        cfg = load_config(args.config)
        signals = cfg.signals
        diagnostics = cfg.diagnostics
        vehicle = cfg.vehicle
        if args.mode is None:
            mode = cfg.bus.mode
        if args.bitrate is None:
            bitrate = cfg.bus.bitrate
        if preferred is None:
            preferred = cfg.bus.channel
        request_id = cfg.bus.request_id
        response_id = cfg.bus.response_id

    if args.list_channels:
        channels = detect_hardware(mode=mode)
        print(format_channel_table(channels, mode=mode))
        return 0

    session = EmulatorSession(
        signals=signals,
        diagnostics=diagnostics,
        vehicle=vehicle,
        bitrate=bitrate,
        mode=mode,
        request_id=request_id,
        response_id=response_id,
    )
    atexit.register(session.stop)

    channel: DetectedChannel | None = None
    if preferred:
        try:
            channel = find_channel(mode, preferred)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        channels = detect_hardware(mode=mode)
        channel = channels[0] if channels else None

    if not args.no_start:
        if channel is None:
            print("error: no channel available", file=sys.stderr)
            return 2
        try:
            session.start(channel)
            print(f"STARTED on {channel.label} @ {bitrate} bit/s")
        except Exception as exc:
            print(f"error: start failed: {exc}", file=sys.stderr)
            session.stop()
            return 1

    print("OBD2 emulator CLI — type help. Hardware is released on quit/stop.")
    try:
        return _repl(session, mode)
    finally:
        session.stop()


def _repl(session: EmulatorSession, mode: EmulationMode) -> int:
    current_mode = mode
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        try:
            if cmd in ("quit", "exit", "q"):
                break
            if cmd == "help":
                print(_HELP)
            elif cmd == "status":
                st = session.stats()
                print(
                    f"running={st.running} uptime={st.uptime_s:.1f}s "
                    f"tx={st.tx_count} rx={st.rx_count} load={st.load_pct:.1f}% "
                    f"bitrate={st.bitrate} channel={st.channel_label!r} "
                    f"dtcs={len(session.diagnostics.list_codes())} "
                    f"vin={session.vehicle.vin!r}"
                )
            elif cmd == "channels":
                m = EmulationMode(parts[1]) if len(parts) > 1 else current_mode
                print(format_channel_table(detect_hardware(mode=m), mode=m))
            elif cmd == "mode":
                if len(parts) == 1:
                    print(current_mode.value)
                else:
                    if session.running:
                        print("error: stop first")
                        continue
                    current_mode = EmulationMode(parts[1])
                    print(current_mode.value)
            elif cmd == "bitrate":
                if len(parts) == 1:
                    print(session.bitrate)
                else:
                    session.set_bitrate(int(parts[1]))
                    print(session.bitrate)
            elif cmd == "channel":
                if len(parts) < 2:
                    print("usage: channel <N>")
                    continue
                if session.running:
                    print("error: stop first")
                    continue
                ch = find_channel(current_mode, parts[1])
                print(f"selected {ch.label}")
                session._channel = ch  # noqa: SLF001 — intentional CLI stash
            elif cmd == "start":
                ch = session._channel  # noqa: SLF001
                if ch is None:
                    chs = detect_hardware(mode=current_mode)
                    ch = chs[0] if chs else None
                if ch is None:
                    print("error: no channel")
                    continue
                session.start(ch)
                print(f"STARTED {ch.label}")
            elif cmd == "stop":
                session.stop()
                print("STOPPED (hardware released)")
            elif cmd == "reset":
                session.reset(session._channel)  # noqa: SLF001
                print("RESET")
            elif cmd == "pid":
                _cmd_pid(session, parts)
            elif cmd == "dtc":
                _cmd_dtc(session, parts)
            elif cmd == "vin":
                if len(parts) >= 2 and parts[1] == "get":
                    print(session.vehicle.vin)
                elif len(parts) >= 3 and parts[1] == "set":
                    session.vehicle.set_vin(parts[2])
                    print(session.vehicle.snapshot())
                else:
                    print("usage: vin get | vin set <17chars>")
            elif cmd == "calid":
                if len(parts) >= 2 and parts[1] == "get":
                    print(session.vehicle.calid)
                elif len(parts) >= 3 and parts[1] == "set":
                    session.vehicle.set_calid(" ".join(parts[2:]))
                    print(session.vehicle.snapshot())
                else:
                    print("usage: calid get | calid set <≤16chars>")
            else:
                print(f"unknown command: {cmd} (help)")
        except Exception as exc:
            print(f"error: {exc}")
    return 0


def _cmd_pid(session: EmulatorSession, parts: list[str]) -> None:
    from obd2_emulator.services.mode01 import encode_pid
    from obd2_emulator.services.mode01_catalog import PID_META

    if len(parts) >= 2 and parts[1] == "list":
        print(session.signals.snapshot())
        return
    if len(parts) >= 2 and parts[1] == "meta":
        if len(parts) >= 3:
            pid = int(parts[2], 0)
            m = PID_META.get(pid)
            print(m if m else f"unknown PID {pid:#x}")
        else:
            for pid in sorted(PID_META):
                m = PID_META[pid]
                print(f"  {m.pid:02X}  {m.nbytes}B  [{m.group}]  {m.name}")
            print(f"({len(PID_META)} PIDs)")
        return
    if len(parts) >= 3 and parts[1] == "get":
        key = parts[2]
        if key.lower().startswith("0x") or (
            len(key) <= 2 and all(c in "0123456789abcdefABCDEF" for c in key)
        ):
            pid = int(key, 16) if key.lower().startswith("0x") else int(key, 16)
            data = encode_pid(pid, session.signals)
            print(f"PID {pid:02X} → {data.hex() if data else None}")
        else:
            print(key, "=", session.signals.get_pid(key))
        return
    if len(parts) >= 4 and parts[1] == "set":
        key = parts[2]
        raw = parts[3]
        if key == "mil_on":
            val: float | int | bool = raw.lower() in ("1", "true", "on", "yes")
        elif key in ("dtc_count",) or key.endswith("_s") or key.endswith("_min"):
            try:
                val = int(raw)
            except ValueError:
                val = float(raw)
        else:
            val = float(raw) if "." in raw or "e" in raw.lower() else (
                int(raw) if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()) else float(raw)
            )
        session.signals.set(key, val)
        print(session.signals.snapshot())
        return
    print("usage: pid list | pid get <key|XX> | pid set <key> <value> | pid meta [XX]")


def _cmd_dtc(session: EmulatorSession, parts: list[str]) -> None:
    if len(parts) >= 2 and parts[1] == "list":
        print(session.diagnostics.snapshot())
        return
    if len(parts) >= 3 and parts[1] == "add":
        code = parts[2]
        desc = " ".join(parts[3:]) if len(parts) > 3 else ""
        session.diagnostics.add(code, desc)
        sync_mil_from_diagnostics(session.signals, session.diagnostics)
        print(session.diagnostics.snapshot())
        return
    if len(parts) >= 3 and parts[1] == "remove":
        ok = session.diagnostics.remove(parts[2])
        sync_mil_from_diagnostics(session.signals, session.diagnostics)
        print("removed" if ok else "not found", session.diagnostics.snapshot())
        return
    if len(parts) >= 2 and parts[1] == "clear":
        session.diagnostics.clear()
        sync_mil_from_diagnostics(session.signals, session.diagnostics)
        print(session.diagnostics.snapshot())
        return
    print("usage: dtc list | dtc add <CODE> [desc] | dtc remove <CODE> | dtc clear")


if __name__ == "__main__":
    raise SystemExit(main())
