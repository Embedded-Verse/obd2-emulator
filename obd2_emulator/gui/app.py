"""NiceGUI localhost app — Bus Config, Live Data, Diagnostics, Vehicle."""

from __future__ import annotations

import webbrowser
from typing import Any

from nicegui import app, ui

from obd2_emulator import __version__
from obd2_emulator.bus.detect import (
    DetectedChannel,
    EmulationMode,
    detect_hardware,
    resolve_channel,
)
from obd2_emulator.bus.session import EmulatorSession
from obd2_emulator.config import load_config
from obd2_emulator.gui.styles import APP_CSS
from obd2_emulator.services.mode01_catalog import PID_META
from obd2_emulator.state import LiveSignalState, sync_mil_from_diagnostics

# Editable GUI signals grouped by virtual ECU (wire PIDs remain J1979-native)
_GUI_GROUPS: list[tuple[str, list[tuple[str, str, float, float, float]]]] = [
    (
        "Powertrain",
        [
            ("engine_rpm", "Engine RPM ($0C)", 0, 8000, 1),
            ("vehicle_speed_kph", "Speed km/h ($0D)", 0, 255, 1),
            ("coolant_c", "Coolant °C ($05)", -40, 215, 1),
            ("throttle_pct", "Throttle % ($11)", 0, 100, 1),
            ("calculated_load", "Calc load % ($04)", 0, 100, 1),
            ("timing_advance", "Timing adv ° ($0E)", -64, 63.5, 0.5),
            ("intake_air_c", "IAT °C ($0F)", -40, 215, 1),
            ("maf_gps", "MAF g/s ($10)", 0, 655, 0.01),
            ("absolute_load", "Abs load % ($43)", 0, 25000, 1),
            ("module_voltage", "Module V ($42)", 0, 65, 0.1),
            ("oil_temp_c", "Oil °C ($5C)", -40, 215, 1),
            ("fuel_rate_lph", "Fuel L/h ($5E)", 0, 500, 0.05),
            ("odometer_km", "Odometer km ($A6)", 0, 1e7, 0.1),
        ],
    ),
    (
        "Fuel & Trim",
        [
            ("stft_b1", "STFT B1 % ($06)", -100, 99, 0.5),
            ("ltft_b1", "LTFT B1 % ($07)", -100, 99, 0.5),
            ("stft_b2", "STFT B2 % ($08)", -100, 99, 0.5),
            ("ltft_b2", "LTFT B2 % ($09)", -100, 99, 0.5),
            ("fuel_pressure_kpa", "Fuel press kPa ($0A)", 0, 765, 3),
            ("map_kpa", "MAP kPa ($0B)", 0, 255, 1),
            ("fuel_level_pct", "Fuel level % ($2F)", 0, 100, 1),
            ("commanded_eq_ratio", "Cmd EQ ratio ($44)", 0, 2, 0.001),
            ("fuel_rail_kpa", "Rail kPa ($23)", 0, 655350, 10),
        ],
    ),
    (
        "Emissions / O2",
        [
            ("o2_0_v", "O2 B1S1 V ($14)", 0, 1.275, 0.005),
            ("o2_0_trim", "O2 B1S1 trim %", -100, 99, 0.5),
            ("wide_0_lambda", "Wide λ B1S1 ($24)", 0, 2, 0.001),
            ("wide_0_v", "Wide O2 V ($24)", 0, 8, 0.01),
            ("commanded_egr", "Cmd EGR % ($2C)", 0, 100, 1),
            ("barometric_kpa", "Baro kPa ($33)", 0, 255, 1),
            ("ambient_c", "Ambient °C ($46)", -40, 215, 1),
            ("catalyst_b1s1_c", "Cat B1S1 °C ($3C)", -40, 2000, 1),
        ],
    ),
]

BITRATE_OPTIONS = {
    125_000: "125 kbit/s",
    250_000: "250 kbit/s",
    500_000: "500 kbit/s (default)",
    1_000_000: "1000 kbit/s",
}

MODE_OPTIONS = {
    "real": "Real Hardware Emulation",
    "virtual": "Virtual Emulation",
}

_DEMO_DTCS = (
    ("P0301", "Cylinder 1 Misfire"),
    ("P0420", "Catalyst System Efficiency Below Threshold"),
    ("P0171", "System Too Lean (Bank 1)"),
)


class GuiState:
    def __init__(self, session: EmulatorSession) -> None:
        self.session = session
        self.mode = EmulationMode.VIRTUAL
        self.channels: list[DetectedChannel] = []
        self.channel_uid: str | None = None
        self.bitrate = 500_000
        self.host = "127.0.0.1"
        self.port = 8080
        self.open_browser = True
        self.preferred_channel: str | None = None
        self.ui_refs: dict[str, Any] = {}
        self.status_msg = "Ready"


def run_gui(
    config_path: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = True,
) -> None:
    signals = LiveSignalState()
    bitrate = 500_000
    mode = EmulationMode.VIRTUAL
    preferred_channel: str | None = None
    request_id, response_id = 0x7E0, 0x7E8
    diagnostics = None
    vehicle = None

    if config_path:
        cfg = load_config(config_path)
        signals = cfg.signals
        diagnostics = cfg.diagnostics
        vehicle = cfg.vehicle
        bitrate = cfg.bus.bitrate
        mode = cfg.bus.mode
        preferred_channel = cfg.bus.channel
        request_id = cfg.bus.request_id
        response_id = cfg.bus.response_id

    session = EmulatorSession(
        signals=signals,
        diagnostics=diagnostics,
        vehicle=vehicle,
        bitrate=bitrate,
        mode=mode,
        request_id=request_id,
        response_id=response_id,
    )
    state = GuiState(session)
    state.mode = mode
    state.bitrate = bitrate
    state.host = host
    state.port = int(port)
    state.open_browser = open_browser
    state.preferred_channel = preferred_channel

    @app.on_startup
    def _startup() -> None:
        if state.open_browser:
            try:
                webbrowser.open(f"http://{state.host}:{state.port}/")
            except Exception:
                pass

    @app.on_shutdown
    def _shutdown() -> None:
        session.stop()

    @ui.page("/")
    def index_page() -> None:
        ui.add_css(APP_CSS)
        _build_page(state)

    ui.run(
        host=host,
        port=port,
        title="OBD2 Emulator",
        reload=False,
        show=False,
    )


def _build_page(state: GuiState) -> None:
    session = state.session
    signals = session.signals
    diagnostics = session.diagnostics
    vehicle = session.vehicle

    def refresh_channels() -> None:
        state.channels = detect_hardware(mode=state.mode, timeout=6.0)
        if state.preferred_channel and state.channel_uid is None:
            pref = state.preferred_channel.strip()
            if pref.isdigit():
                idx = int(pref)
                if 1 <= idx <= len(state.channels):
                    state.channel_uid = state.channels[idx - 1].uid
            else:
                for ch in state.channels:
                    if pref in (ch.uid, ch.label) or pref == str(
                        ch.bus_kwargs.get("channel")
                    ):
                        state.channel_uid = ch.uid
                        break
        if state.channel_uid is None and state.channels:
            for ch in state.channels:
                if ch.interface in ("candle", "gs_usb"):
                    state.channel_uid = ch.uid
                    break
            if state.channel_uid is None:
                state.channel_uid = state.channels[0].uid
        sel = state.ui_refs.get("channel_select")
        if sel is not None:
            opts = {ch.uid: ch.label for ch in state.channels} or {"": "(none)"}
            sel.set_options(
                opts,
                value=state.channel_uid
                if state.channel_uid in opts
                else next(iter(opts)),
            )

    def selected_channel() -> DetectedChannel | None:
        return resolve_channel(state.channels, uid=state.channel_uid)

    def do_start() -> None:
        ch = selected_channel()
        if ch is None:
            state.status_msg = "No channel selected"
            return
        try:
            session.bitrate = state.bitrate
            session.start(ch)
            state.status_msg = f"RUNNING on {ch.label}"
        except Exception as exc:
            state.status_msg = f"START failed: {exc}"

    def do_stop() -> None:
        try:
            session.stop()
            state.status_msg = "STOPPED (hardware released)"
        except Exception as exc:
            state.status_msg = f"STOP failed: {exc}"

    def do_reset() -> None:
        ch = selected_channel()
        try:
            session.bitrate = state.bitrate
            session.reset(ch)
            state.status_msg = "RESET complete"
        except Exception as exc:
            state.status_msg = f"RESET failed: {exc}"

    def do_quit() -> None:
        try:
            session.stop()
        finally:
            app.shutdown()

    def refresh_dtc_table() -> None:
        rows = diagnostics.snapshot()
        table = state.ui_refs.get("dtc_table")
        if table is not None:
            table.rows = rows
            table.update()
        mil_lbl = state.ui_refs.get("dtc_summary")
        if mil_lbl is not None:
            mil_lbl.set_text(
                f"{len(rows)} stored · MIL={'ON' if signals.mil_on else 'OFF'} · "
                f"PID $01 count={signals.dtc_count}"
            )

    def inject_demo() -> None:
        for code, desc in _DEMO_DTCS:
            diagnostics.add(code, desc)
        sync_mil_from_diagnostics(signals, diagnostics)
        refresh_dtc_table()
        state.status_msg = "Injected demo DTCs (P0301, P0420, P0171)"

    def clear_dtcs() -> None:
        diagnostics.clear()
        sync_mil_from_diagnostics(signals, diagnostics)
        refresh_dtc_table()
        state.status_msg = "Cleared all DTCs (Mode $04 equivalent)"

    def add_dtc() -> None:
        code_in = state.ui_refs.get("dtc_code_input")
        desc_in = state.ui_refs.get("dtc_desc_input")
        code = (code_in.value if code_in else "") or ""
        desc = (desc_in.value if desc_in else "") or ""
        try:
            diagnostics.add(str(code), str(desc))
            sync_mil_from_diagnostics(signals, diagnostics)
            refresh_dtc_table()
            state.status_msg = f"Added {str(code).upper()}"
        except Exception as exc:
            state.status_msg = f"DTC add failed: {exc}"

    def apply_vin() -> None:
        vin_in = state.ui_refs.get("vin_input")
        try:
            vehicle.set_vin(str(vin_in.value if vin_in else ""))
            state.status_msg = f"VIN set to {vehicle.vin}"
        except Exception as exc:
            state.status_msg = f"VIN failed: {exc}"

    def apply_calid() -> None:
        cal_in = state.ui_refs.get("calid_input")
        try:
            vehicle.set_calid(str(cal_in.value if cal_in else ""))
            state.status_msg = f"CALID set to {vehicle.calid}"
        except Exception as exc:
            state.status_msg = f"CALID failed: {exc}"

    with ui.element("div").classes("obd2-root"):
        with ui.element("div").classes("topbar"):
            with ui.element("div").classes("brand-section"):
                with ui.element("div").classes("brand-icon"):
                    ui.label("O2")
                ui.label("OBD-II / SAE J1979 Light-Vehicle ECU Emulator").classes(
                    "brand-title"
                )
                ui.label(f"v{__version__}").classes("badge-subtle")
            status_pill = ui.element("div").classes("status-pill stopped")
            with status_pill:
                ui.element("span").classes("status-dot")
                status_text = ui.label("ECU STOPPED")
            port_lbl = ui.label(f"PORT :{state.port}").classes("badge-subtle")
            ui.button("QUIT", on_click=do_quit).classes("action-btn btn-quit")

        with ui.element("div").classes("obd2-main"):
            with ui.element("div").classes("card"):
                ui.label("Bus Config").style("font-weight:800;margin-bottom:8px")
                with ui.row().classes("w-full items-end").style(
                    "gap:14px;flex-wrap:wrap"
                ):
                    with ui.column():
                        ui.label("Emulation mode").classes("field-label")

                        def on_mode(e: Any) -> None:
                            state.mode = EmulationMode(str(e.value))
                            state.channel_uid = None
                            refresh_channels()

                        ui.select(
                            MODE_OPTIONS,
                            value=state.mode.value,
                            on_change=on_mode,
                        ).style("min-width:220px")
                    with ui.column():
                        ui.label("Interface / Channel").classes("field-label")
                        channel_select = ui.select(
                            {"": "(detecting…)"},
                            value="",
                            on_change=lambda e: setattr(
                                state, "channel_uid", e.value or None
                            ),
                        ).style("min-width:280px")
                        state.ui_refs["channel_select"] = channel_select
                    with ui.column():
                        ui.label("Bitrate").classes("field-label")
                        ui.select(
                            BITRATE_OPTIONS,
                            value=state.bitrate,
                            on_change=lambda e: setattr(
                                state, "bitrate", int(e.value)
                            ),
                        ).style("min-width:180px")
                    ui.button("Refresh", on_click=refresh_channels).classes(
                        "action-btn btn-restart"
                    )
                    ui.button("START", on_click=do_start).classes(
                        "action-btn btn-start"
                    )
                    ui.button("STOP", on_click=do_stop).classes("action-btn btn-stop")
                    ui.button("RESET", on_click=do_reset).classes(
                        "action-btn btn-restart"
                    )

                stats_line = (
                    ui.label("Uptime 0s · TX 0 · RX 0 · Load 0%")
                    .classes("font-mono")
                    .style("margin-top:10px;color:#5B6775")
                )
                msg_line = ui.label("").style("margin-top:4px;color:#0B6BCB")

            with ui.tabs().classes("w-full") as tabs:
                tab_live = ui.tab("Live Data")
                tab_diag = ui.tab("Diagnostics")
                tab_veh = ui.tab("Vehicle")

            with ui.tab_panels(tabs, value=tab_live).classes("w-full"):
                with ui.tab_panel(tab_live):
                    with ui.element("div").classes("card"):
                        ui.label(
                            f"Live Data — Mode $01 full catalog ({len(PID_META)} PIDs)"
                        ).style("font-weight:800;margin-bottom:4px")
                        ui.label(
                            "Virtual ECU groups are UX only; responses stay J1979DA-native. "
                            "All Annex B PIDs answer on the bus (CLI: pid meta)."
                        ).style("color:#5B6775;font-size:12px;margin-bottom:8px")
                        with ui.row():
                            with ui.column():
                                ui.label("MIL ($01)").classes("field-label")
                                ui.switch(
                                    "MIL on",
                                    value=signals.mil_on,
                                    on_change=lambda e: signals.set(
                                        "mil_on", bool(e.value)
                                    ),
                                )
                            _num(
                                "DTC count ($01)",
                                signals.dtc_count,
                                0,
                                127,
                                lambda v: signals.set("dtc_count", int(v)),
                                step=1,
                            )
                        with ui.tabs().classes("w-full") as ecu_tabs:
                            ecu_tab_refs = [
                                ui.tab(name) for name, _ in _GUI_GROUPS
                            ]
                        with ui.tab_panels(
                            ecu_tabs, value=ecu_tab_refs[0]
                        ).classes("w-full"):
                            for tab_ref, (gname, fields) in zip(
                                ecu_tab_refs, _GUI_GROUPS
                            ):
                                with ui.tab_panel(tab_ref):
                                    with ui.element("div").classes("live-grid"):
                                        for key, label, mn, mx, step in fields:
                                            cur = float(
                                                signals.get_pid(
                                                    key,
                                                    getattr(signals, key, 0)
                                                    if hasattr(signals, key)
                                                    else 0,
                                                )
                                            )
                                            _num(
                                                label,
                                                cur,
                                                mn,
                                                mx,
                                                lambda v, k=key: signals.set(
                                                    k, float(v)
                                                ),
                                                step=step,
                                            )

                with ui.tab_panel(tab_diag):
                    with ui.element("div").classes("card"):
                        ui.label("Diagnostics — Mode $03 / $04").style(
                            "font-weight:800;margin-bottom:8px"
                        )
                        dtc_summary = ui.label("").classes("font-mono").style(
                            "margin-bottom:8px;color:#5B6775"
                        )
                        state.ui_refs["dtc_summary"] = dtc_summary
                        with ui.row().style("gap:10px;flex-wrap:wrap;margin-bottom:8px"):
                            dtc_code = ui.input(
                                "Code", placeholder="P0301"
                            ).style("min-width:120px")
                            dtc_desc = ui.input(
                                "Description", placeholder="optional"
                            ).style("min-width:220px")
                            state.ui_refs["dtc_code_input"] = dtc_code
                            state.ui_refs["dtc_desc_input"] = dtc_desc
                            ui.button("Add", on_click=add_dtc).classes(
                                "action-btn btn-start"
                            )
                            ui.button("Inject demo", on_click=inject_demo).classes(
                                "action-btn btn-restart"
                            )
                            ui.button("Clear all ($04)", on_click=clear_dtcs).classes(
                                "action-btn btn-stop"
                            )
                        dtc_table = ui.table(
                            columns=[
                                {
                                    "name": "code",
                                    "label": "Code",
                                    "field": "code",
                                    "sortable": True,
                                },
                                {
                                    "name": "description",
                                    "label": "Description",
                                    "field": "description",
                                },
                            ],
                            rows=diagnostics.snapshot(),
                            row_key="code",
                        ).classes("w-full")
                        state.ui_refs["dtc_table"] = dtc_table
                        refresh_dtc_table()

                with ui.tab_panel(tab_veh):
                    with ui.element("div").classes("card"):
                        ui.label("Vehicle — Mode $09").style(
                            "font-weight:800;margin-bottom:8px"
                        )
                        with ui.element("div").classes("live-grid"):
                            with ui.column():
                                ui.label("VIN ($02) — 17 chars").classes(
                                    "field-label"
                                )
                                vin_input = ui.input(value=vehicle.vin).style(
                                    "min-width:260px"
                                )
                                state.ui_refs["vin_input"] = vin_input
                                ui.button("Apply VIN", on_click=apply_vin).classes(
                                    "action-btn btn-start"
                                )
                            with ui.column():
                                ui.label("CALID ($04) — ≤16 ASCII").classes(
                                    "field-label"
                                )
                                calid_input = ui.input(value=vehicle.calid).style(
                                    "min-width:220px"
                                )
                                state.ui_refs["calid_input"] = calid_input
                                ui.button(
                                    "Apply CALID", on_click=apply_calid
                                ).classes("action-btn btn-start")
                        ui.label(
                            "InfoType $00 reports support for $02 and $04 "
                            "(ISO 15765-4 single-message VIN/CALID)."
                        ).style("margin-top:10px;color:#5B6775;font-size:12px")

        with ui.element("div").classes("footer"):
            footer_left = ui.label(f"{state.bitrate} bit/s")
            footer_right = ui.label(
                f"TX 0 · RX 0 · DTCs 0 · obd2-emulator v{__version__}"
            )

    def tick() -> None:
        st = session.stats()
        if st.running:
            status_pill.classes(replace="status-pill running")
            status_text.set_text("ECU RUNNING")
        else:
            status_pill.classes(replace="status-pill stopped")
            status_text.set_text("ECU STOPPED")
        n_dtc = len(diagnostics.list_codes())
        stats_line.set_text(
            f"Uptime {st.uptime_s:.1f}s · TX {st.tx_count} · RX {st.rx_count} · "
            f"Load {st.load_pct:.1f}% · {st.channel_label or '—'} · DTCs {n_dtc}"
        )
        msg_line.set_text(state.status_msg)
        port_lbl.set_text(f"PORT :{state.port}")
        footer_left.set_text(f"{st.bitrate} bit/s")
        footer_right.set_text(
            f"TX {st.tx_count} · RX {st.rx_count} · DTCs {n_dtc} · "
            f"obd2-emulator v{__version__}"
        )
        # Keep Diagnostics tab in sync if Mode $04 cleared from the bus
        table = state.ui_refs.get("dtc_table")
        if table is not None:
            rows = diagnostics.snapshot()
            if table.rows != rows:
                table.rows = rows
                table.update()
        mil_lbl = state.ui_refs.get("dtc_summary")
        if mil_lbl is not None:
            mil_lbl.set_text(
                f"{n_dtc} stored · MIL={'ON' if signals.mil_on else 'OFF'} · "
                f"PID $01 count={signals.dtc_count}"
            )

    refresh_channels()
    ui.timer(0.5, tick)


def _num(
    label: str,
    value: float | int,
    mn: float,
    mx: float,
    on_change: Any,
    step: float = 1,
) -> None:
    with ui.column():
        ui.label(label).classes("field-label")
        ui.number(
            value=value,
            min=mn,
            max=mx,
            step=step,
            on_change=lambda e: on_change(e.value),
        ).style("min-width:160px")
