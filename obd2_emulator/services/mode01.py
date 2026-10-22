"""Mode $01 — current powertrain data (full Annex B catalog).

Encodings from SAE J1979 Digital Annex 201702 (Annex B Scaling/bit).
Support bitmasks per Annex A. All PIDs in mode01_catalog.PID_META are answered.
"""

from __future__ import annotations

from obd2_emulator.services import pid_formulas as F
from obd2_emulator.services.mode01_catalog import (
    PID_META,
    SUPPORTED_PIDS,
    supported_bitmask,
)
from obd2_emulator.state import LiveSignalState


def _g(state: LiveSignalState, key: str, default: float | int) -> float | int:
    return state.get_pid(key, default)


def _o2_pair(state: LiveSignalState, v_key: str, t_key: str) -> bytes:
    return F.o2_voltage_v(float(_g(state, v_key, 0.45))) + F.fuel_trim_pct(
        float(_g(state, t_key, 0.0))
    )


def _wide_v(state: LiveSignalState, lam_key: str, v_key: str) -> bytes:
    return F.eq_ratio(float(_g(state, lam_key, 1.0))) + F.wide_o2_voltage_v(
        float(_g(state, v_key, 0.45))
    )


def _wide_i(state: LiveSignalState, lam_key: str, ma_key: str) -> bytes:
    return F.eq_ratio(float(_g(state, lam_key, 1.0))) + F.wide_o2_current_ma(
        float(_g(state, ma_key, 0.0))
    )


def _pad(data: bytes, nbytes: int) -> bytes:
    if len(data) >= nbytes:
        return data[:nbytes]
    return data + bytes(nbytes - len(data))


def _support_flags_sensors(
    support: int, *sensor_chunks: bytes, nbytes: int
) -> bytes:
    return _pad(bytes([support & 0xFF]) + b"".join(sensor_chunks), nbytes)


def encode_pid(pid: int, state: LiveSignalState) -> bytes | None:
    """Return data bytes for one PID (no service/PID echo), or None if unknown."""
    if pid in state.raw_overrides:
        meta = PID_META.get(pid)
        raw = state.raw_overrides[pid]
        if meta:
            return _pad(raw, meta.nbytes)
        return raw

    # --- Support bitmasks ---
    if pid % 0x20 == 0 and pid in PID_META:
        return supported_bitmask(pid, SUPPORTED_PIDS)

    if pid == 0x01:
        a = (0x80 if state.mil_on else 0x00) | (int(state.dtc_count) & 0x7F)
        return bytes(
            [
                a & 0xFF,
                int(state.monitor_status_b) & 0xFF,
                int(state.monitor_status_c) & 0xFF,
                int(state.monitor_status_d) & 0xFF,
            ]
        )

    if pid == 0x02:
        return bytes(
            [
                int(_g(state, "freeze_dtc_hi", 0)) & 0xFF,
                int(_g(state, "freeze_dtc_lo", 0)) & 0xFF,
            ]
        )

    if pid == 0x03:
        return bytes(
            [
                int(_g(state, "fuel_system_a", 0x02)) & 0xFF,  # closed loop
                int(_g(state, "fuel_system_b", 0x00)) & 0xFF,
            ]
        )

    if pid == 0x04:
        return F.pct_255(float(_g(state, "calculated_load", 20.0)))
    if pid == 0x05:
        return F.temp_c_offset40(float(state.coolant_c))
    if pid == 0x06:
        return F.fuel_trim_pct(float(_g(state, "stft_b1", 0.0)))
    if pid == 0x07:
        return F.fuel_trim_pct(float(_g(state, "ltft_b1", 0.0)))
    if pid == 0x08:
        return F.fuel_trim_pct(float(_g(state, "stft_b2", 0.0)))
    if pid == 0x09:
        return F.fuel_trim_pct(float(_g(state, "ltft_b2", 0.0)))
    if pid == 0x0A:
        return F.fuel_pressure_gauge_kpa(float(_g(state, "fuel_pressure_kpa", 300.0)))
    if pid == 0x0B:
        return F.u8(int(round(float(_g(state, "map_kpa", 100.0)))))
    if pid == 0x0C:
        return F.rpm(float(state.engine_rpm))
    if pid == 0x0D:
        return F.u8(int(round(float(state.vehicle_speed_kph))))
    if pid == 0x0E:
        return F.timing_advance_deg(float(_g(state, "timing_advance", 10.0)))
    if pid == 0x0F:
        return F.temp_c_offset40(float(_g(state, "intake_air_c", 25.0)))
    if pid == 0x10:
        return F.maf_gps(float(_g(state, "maf_gps", 5.0)))
    if pid == 0x11:
        return F.pct_255(float(state.throttle_pct))
    if pid == 0x12:
        return F.u8(int(_g(state, "secondary_air", 0x01)))
    if pid == 0x13:
        return F.u8(int(_g(state, "o2_loc_13", 0x03)))  # B1S1+B1S2
    if 0x14 <= pid <= 0x1B:
        idx = pid - 0x14
        return _o2_pair(state, f"o2_{idx}_v", f"o2_{idx}_trim")
    if pid == 0x1C:
        return F.u8(int(_g(state, "obd_standard", 0x06)))  # EOBD+OBD-II
    if pid == 0x1D:
        return F.u8(int(_g(state, "o2_loc_1d", 0x03)))
    if pid == 0x1E:
        return F.u8(int(_g(state, "aux_input", 0x00)))
    if pid == 0x1F:
        return F.u16_be(int(_g(state, "runtime_s", 120)))

    if pid == 0x21:
        return F.u16_be(int(_g(state, "distance_mil_km", 0)))
    if pid == 0x22:
        return F.fuel_rail_rel_kpa(float(_g(state, "fuel_rail_rel_kpa", 0.0)))
    if pid == 0x23:
        return F.fuel_rail_kpa10(float(_g(state, "fuel_rail_kpa", 35000.0)))
    if 0x24 <= pid <= 0x2B:
        i = pid - 0x24
        return _wide_v(state, f"wide_{i}_lambda", f"wide_{i}_v")
    if pid == 0x2C:
        return F.pct_255(float(_g(state, "commanded_egr", 0.0)))
    if pid == 0x2D:
        return F.fuel_trim_pct(float(_g(state, "egr_error_pct", 0.0)))
    if pid == 0x2E:
        return F.pct_255(float(_g(state, "evaporative_purge", 0.0)))
    if pid == 0x2F:
        return F.pct_255(float(_g(state, "fuel_level_pct", 50.0)))
    if pid == 0x30:
        return F.u8(int(_g(state, "warmups_since_clear", 5)))
    if pid == 0x31:
        return F.u16_be(int(_g(state, "distance_clear_km", 100)))
    if pid == 0x32:
        return F.evap_pa_025(float(_g(state, "evap_pressure_pa", 0.0)))
    if pid == 0x33:
        return F.u8(int(round(float(_g(state, "barometric_kpa", 101.0)))))
    if 0x34 <= pid <= 0x3B:
        i = pid - 0x34
        return _wide_i(state, f"widei_{i}_lambda", f"widei_{i}_ma")
    if 0x3C <= pid <= 0x3F:
        keys = (
            "catalyst_b1s1_c",
            "catalyst_b2s1_c",
            "catalyst_b1s2_c",
            "catalyst_b2s2_c",
        )
        return F.catalyst_temp_c(float(_g(state, keys[pid - 0x3C], 450.0)))

    if pid == 0x41:
        # Byte A reserved 0; B/C/D similar layout to $01 monitors this cycle
        return bytes(
            [
                0x00,
                int(_g(state, "monitor_cycle_b", 0x07)) & 0xFF,
                int(_g(state, "monitor_cycle_c", 0x00)) & 0xFF,
                int(_g(state, "monitor_cycle_d", 0x00)) & 0xFF,
            ]
        )
    if pid == 0x42:
        return F.module_voltage(float(_g(state, "module_voltage", 14.2)))
    if pid == 0x43:
        return F.pct_255_u16(float(_g(state, "absolute_load", 20.0)))
    if pid == 0x44:
        return F.eq_ratio(float(_g(state, "commanded_eq_ratio", 1.0)))
    if pid == 0x45:
        return F.pct_255(float(_g(state, "relative_throttle", float(state.throttle_pct))))
    if pid == 0x46:
        return F.temp_c_offset40(float(_g(state, "ambient_c", 22.0)))
    if pid == 0x47:
        return F.pct_255(float(_g(state, "throttle_b", float(state.throttle_pct))))
    if pid == 0x48:
        return F.pct_255(float(_g(state, "throttle_c", 0.0)))
    if pid == 0x49:
        return F.pct_255(float(_g(state, "accel_d", 0.0)))
    if pid == 0x4A:
        return F.pct_255(float(_g(state, "accel_e", 0.0)))
    if pid == 0x4B:
        return F.pct_255(float(_g(state, "accel_f", 0.0)))
    if pid == 0x4C:
        return F.pct_255(float(_g(state, "commanded_throttle", float(state.throttle_pct))))
    if pid == 0x4D:
        return F.u16_be(int(_g(state, "runtime_mil_min", 0)))
    if pid == 0x4E:
        return F.u16_be(int(_g(state, "runtime_clear_min", 30)))
    if pid == 0x4F:
        # Max EQ=1, O2V=1V, O2mA=1, MAP scale 10 kPa → report 1,1,1,25 typical
        return bytes(
            [
                int(_g(state, "cfg_max_eq", 1)) & 0xFF,
                int(_g(state, "cfg_max_o2v", 1)) & 0xFF,
                int(_g(state, "cfg_max_o2ma", 1)) & 0xFF,
                int(_g(state, "cfg_max_map", 25)) & 0xFF,
            ]
        )
    if pid == 0x50:
        return bytes(
            [
                int(_g(state, "cfg_max_maf", 10)) & 0xFF,
                0x00,
                0x00,
                0x00,
            ]
        )
    if pid == 0x51:
        return F.u8(int(_g(state, "fuel_type", 0x01)))  # Gasoline
    if pid == 0x52:
        return F.pct_255(float(_g(state, "alcohol_pct", 0.0)))
    if pid == 0x53:
        return F.evap_abs_kpa(float(_g(state, "evap_abs_kpa", 101.3)))
    if pid == 0x54:
        return F.evap_pa_1(float(_g(state, "evap_pressure_pa", 0.0)))
    if pid == 0x55:
        return F.fuel_trim_pct(float(_g(state, "st_sec_o2_b1", 0.0)))
    if pid == 0x56:
        return F.fuel_trim_pct(float(_g(state, "lt_sec_o2_b1", 0.0)))
    if pid == 0x57:
        return F.fuel_trim_pct(float(_g(state, "st_sec_o2_b2", 0.0)))
    if pid == 0x58:
        return F.fuel_trim_pct(float(_g(state, "lt_sec_o2_b2", 0.0)))
    if pid == 0x59:
        return F.fuel_rail_kpa10(float(_g(state, "fuel_rail_abs_kpa", 35000.0)))
    if pid == 0x5A:
        return F.pct_255(float(_g(state, "rel_accel_pct", 0.0)))
    if pid == 0x5B:
        return F.pct_255(float(_g(state, "hybrid_battery_pct", 75.0)))
    if pid == 0x5C:
        return F.temp_c_offset40(float(_g(state, "oil_temp_c", 90.0)))
    if pid == 0x5D:
        return F.injection_timing_deg(float(_g(state, "injection_timing_deg", 0.0)))
    if pid == 0x5E:
        return F.fuel_rate_lph(float(_g(state, "fuel_rate_lph", 2.5)))
    if pid == 0x5F:
        return F.u8(int(_g(state, "emission_req", 0x0E)))

    if pid == 0x61:
        return F.torque_pct_offset125(float(_g(state, "driver_demand_torque_pct", 10.0)))
    if pid == 0x62:
        return F.torque_pct_offset125(float(_g(state, "actual_torque_pct", 10.0)))
    if pid == 0x63:
        return F.u16_be(int(_g(state, "engine_ref_torque_nm", 200)))
    if pid == 0x64:
        pts = [
            float(_g(state, f"torque_pt_{i}", 10.0 if i == 1 else 0.0))
            for i in range(1, 6)
        ]
        return b"".join(F.torque_pct_offset125(p) for p in pts)
    if pid == 0x65:
        # Support PTO etc. in A; status in B
        return bytes(
            [
                int(_g(state, "aux_io_support", 0x01)) & 0xFF,
                int(_g(state, "aux_io_status", 0x00)) & 0xFF,
            ]
        )
    if pid == 0x66:
        # Support MAF A; sensor A value
        return _support_flags_sensors(
            int(_g(state, "maf66_support", 0x01)),
            F.maf_a_gps(float(_g(state, "maf66_a_gps", 5.0))),
            F.maf_a_gps(float(_g(state, "maf66_b_gps", 0.0))),
            nbytes=5,
        )
    if pid == 0x67:
        return _support_flags_sensors(
            int(_g(state, "ect67_support", 0x01)),
            F.temp_c_offset40(float(state.coolant_c)),
            F.temp_c_offset40(float(_g(state, "coolant2_c", float(state.coolant_c)))),
            nbytes=3,
        )
    if pid == 0x68:
        # Support IAT1; up to 6 temps — fill first, zero rest
        support = int(_g(state, "iat68_support", 0x01))
        t1 = F.temp_c_offset40(float(_g(state, "intake_air_c", 25.0)))
        rest = bytes(6)
        return _pad(bytes([support]) + t1 + rest[1:], 7)
    if pid == 0x69:
        support = int(_g(state, "egr69_support", 0x03))  # commanded + error
        return _pad(
            bytes([support])
            + F.pct_255(float(_g(state, "commanded_egr", 0.0)))
            + F.fuel_trim_pct(float(_g(state, "egr_error_pct", 0.0)))
            + bytes(4),
            7,
        )
    if pid == 0x6A:
        return _pad(
            bytes([int(_g(state, "afr6a_support", 0x03))])
            + F.pct_255(float(_g(state, "cmd_intake_flow_pct", 0.0)))
            + F.pct_255(float(_g(state, "rel_intake_flow_pct", 0.0)))
            + bytes(2),
            5,
        )
    if pid == 0x6B:
        return _pad(
            bytes([int(_g(state, "egrt6b_support", 0x01))])
            + F.temp_c_offset40(float(_g(state, "egr_temp_c", 100.0)))
            + bytes(3),
            5,
        )
    if pid == 0x6C:
        return _pad(
            bytes([int(_g(state, "thr6c_support", 0x03))])
            + F.pct_255(float(_g(state, "commanded_throttle", float(state.throttle_pct))))
            + F.pct_255(float(_g(state, "relative_throttle", float(state.throttle_pct))))
            + bytes(2),
            5,
        )
    if pid == 0x6D:
        return _pad(bytes([int(_g(state, "fpc6d_support", 0x01))]) + bytes(10), 11)
    if pid == 0x6E:
        return _pad(bytes([int(_g(state, "ipc6e_support", 0x01))]) + bytes(8), 9)
    if pid == 0x6F:
        return _pad(
            bytes([int(_g(state, "tcip6f_support", 0x01))])
            + F.u8(int(round(float(_g(state, "turbo_inlet_kpa", 100.0)))))
            + bytes(1),
            3,
        )
    if pid == 0x70:
        return _pad(bytes([int(_g(state, "boost70_support", 0x01))]) + bytes(9), 10)
    if pid == 0x71:
        return _pad(bytes([int(_g(state, "vgt71_support", 0x01))]) + bytes(5), 6)
    if pid == 0x72:
        return _pad(bytes([int(_g(state, "wg72_support", 0x01))]) + bytes(4), 5)
    if pid == 0x73:
        return _pad(bytes([int(_g(state, "exhp73_support", 0x01))]) + bytes(4), 5)
    if pid == 0x74:
        return _pad(
            bytes([int(_g(state, "trpm74_support", 0x01))])
            + F.u16_be(int(_g(state, "turbo_rpm", 50000)))
            + bytes(2),
            5,
        )
    if pid == 0x75:
        return _pad(
            bytes([int(_g(state, "tta75_support", 0x01))])
            + F.catalyst_temp_c(float(_g(state, "turbo_a_temp_c", 200.0)))
            + bytes(4),
            7,
        )
    if pid == 0x76:
        return _pad(
            bytes([int(_g(state, "ttb76_support", 0x01))])
            + F.catalyst_temp_c(float(_g(state, "turbo_b_temp_c", 200.0)))
            + bytes(4),
            7,
        )
    if pid == 0x77:
        return _pad(
            bytes([int(_g(state, "cac77_support", 0x01))])
            + F.temp_c_offset40(float(_g(state, "cac_temp_c", 40.0)))
            + bytes(3),
            5,
        )
    if pid == 0x78:
        return _pad(
            bytes([int(_g(state, "egt78_support", 0x01))])
            + F.catalyst_temp_c(float(_g(state, "egt_b1_c", 400.0)))
            + bytes(6),
            9,
        )
    if pid == 0x79:
        return _pad(
            bytes([int(_g(state, "egt79_support", 0x01))])
            + F.catalyst_temp_c(float(_g(state, "egt_b2_c", 400.0)))
            + bytes(6),
            9,
        )
    if pid == 0x7A:
        return _pad(bytes([int(_g(state, "dpf7a_support", 0x01))]) + bytes(6), 7)
    if pid == 0x7B:
        return _pad(bytes([int(_g(state, "dpf7b_support", 0x01))]) + bytes(6), 7)
    if pid == 0x7C:
        return _pad(
            bytes([int(_g(state, "dpft7c_support", 0x01))])
            + F.catalyst_temp_c(float(_g(state, "dpf_temp_c", 350.0)))
            + bytes(6),
            9,
        )
    if pid == 0x7D:
        return F.u8(int(_g(state, "nox_nte_status", 0x00)))
    if pid == 0x7E:
        return F.u8(int(_g(state, "pm_nte_status", 0x00)))
    if pid == 0x7F:
        # Support total+idle; 4-byte times
        support = int(_g(state, "runtime7f_support", 0x03))
        total = F.u32_be(int(_g(state, "total_engine_runtime_s", 3600)))
        idle = F.u32_be(int(_g(state, "total_idle_runtime_s", 600)))
        pto = F.u32_be(int(_g(state, "total_pto_runtime_s", 0)))
        return _pad(bytes([support]) + total + idle + pto, 13)

    if pid in (0x81, 0x82, 0x89, 0x8A):
        return _pad(bytes([0x1F]) + bytes(15), 16)
    if pid == 0x83:
        return _pad(bytes([0x01]) + F.u16_be(int(_g(state, "nox_ppm", 50))) + bytes(6), 9)
    if pid == 0x84:
        return F.temp_c_offset40(float(_g(state, "manifold_surface_c", 80.0)))
    if pid == 0x85:
        return _pad(bytes([0x01]) + bytes(9), 10)
    if pid == 0x86:
        return _pad(bytes([0x01]) + bytes(4), 5)
    if pid == 0x87:
        return _pad(
            bytes([0x01])
            + F.u16_be(int(round(float(_g(state, "map_kpa", 100.0)) * 32)))
            + bytes(2),
            5,
        )
    if pid == 0x88:
        return _pad(bytes([0x01]) + bytes(12), 13)
    if pid == 0x8B:
        return _pad(bytes([0x01]) + bytes(6), 7)
    if pid in (0x8C, 0x9C):
        return _pad(bytes([0x01]) + F.eq_ratio(1.0) + F.wide_o2_voltage_v(0.45) + bytes(11), 16)
    if pid == 0x8D:
        return F.pct_255(float(_g(state, "throttle_g", 0.0)))
    if pid == 0x8E:
        return F.torque_pct_offset125(float(_g(state, "friction_torque_pct", 5.0)))
    if pid == 0x8F:
        return _pad(bytes([0x01]) + bytes(6), 7)
    if pid == 0x90:
        return _pad(bytes([0x01, 0x00, 0x00]), 3)
    if pid == 0x91:
        return _pad(bytes([0x01]) + bytes(4), 5)
    if pid == 0x92:
        return bytes(
            [
                int(_g(state, "fuel_ci_a", 0x01)) & 0xFF,
                int(_g(state, "fuel_ci_b", 0x00)) & 0xFF,
            ]
        )
    if pid == 0x93:
        return _pad(bytes([0x01, 0x00, 0x00]), 3)
    if pid == 0x94:
        return _pad(bytes([0x01]) + bytes(11), 12)
    if pid in (0x98, 0x99):
        key = "egt_b1_c" if pid == 0x98 else "egt_b2_c"
        return _pad(
            bytes([0x01]) + F.catalyst_temp_c(float(_g(state, key, 400.0))) + bytes(6),
            9,
        )
    if pid == 0x9A:
        return _pad(bytes([0x01]) + bytes(5), 6)
    if pid == 0x9B:
        return _pad(
            bytes([0x01])
            + F.pct_255(float(_g(state, "def_level_pct", 80.0)))
            + F.temp_c_offset40(float(_g(state, "def_temp_c", 20.0)))
            + bytes(1),
            4,
        )
    if pid == 0x9D:
        return F.fuel_rate_gps(float(_g(state, "engine_fuel_rate_gps", 1.0))) + F.fuel_rate_gps(
            float(_g(state, "vehicle_fuel_rate_gps", 1.0))
        )
    if pid == 0x9E:
        return F.exhaust_flow_kgh(float(_g(state, "exhaust_flow_kgh", 100.0)))
    if pid == 0x9F:
        return _pad(bytes([0x01]) + F.pct_255(50.0) + bytes(7), 9)

    if pid == 0xA1:
        return _pad(bytes([0x01]) + F.u16_be(int(_g(state, "nox_corr_ppm", 40))) + bytes(6), 9)
    if pid == 0xA2:
        return F.cylinder_fuel_mg(float(_g(state, "cylinder_fuel_mg", 20.0)))
    if pid == 0xA3:
        return _pad(bytes([0x01]) + F.evap_pa_025(0.0) + bytes(6), 9)
    if pid == 0xA4:
        # Support gear+ratio; gear nibble; ratio
        gear = int(_g(state, "trans_gear", 1)) & 0x0F
        return bytes([0x03, (gear << 4) & 0xFF]) + F.u16_be(
            int(round(float(_g(state, "trans_gear_ratio", 3.5)) / 0.001))
        )
    if pid == 0xA5:
        return _pad(bytes([0x01]) + F.pct_255(float(_g(state, "def_dosing_pct", 0.0))) + bytes(2), 4)
    if pid == 0xA6:
        return F.odometer_km(float(_g(state, "odometer_km", 12345.6)))
    if pid in (0xA7, 0xA8):
        return _pad(bytes([0x01]) + F.u16_be(50) + bytes(6), 9)
    if pid == 0xA9:
        return bytes(
            [
                int(_g(state, "moto_io_support", 0x01)) & 0xFF,
                int(_g(state, "moto_io_status", 0x00)) & 0xFF,
            ]
        )

    meta = PID_META.get(pid)
    if meta:
        # Fallback: zeros of correct length (still "supported")
        return bytes(meta.nbytes)
    return None


def handle_mode01(request: bytes, state: LiveSignalState) -> bytes | None:
    if not request or request[0] != 0x01:
        return None
    if len(request) < 2:
        return None
    out = bytearray([0x41])
    for pid in request[1:]:
        data = encode_pid(int(pid), state)
        if data is None:
            continue
        out.append(int(pid) & 0xFF)
        out.extend(data)
    if len(out) == 1:
        return None
    return bytes(out)


# Back-compat name used by older tests
STARTER_PIDS = frozenset({0x01, 0x05, 0x0C, 0x0D, 0x11})


def supported_pid_bitmask_01_20(supported: frozenset[int] | set[int]) -> bytes:
    return supported_bitmask(0x00, frozenset(supported))
