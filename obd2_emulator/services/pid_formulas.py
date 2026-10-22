"""J1979DA Annex B / Annex E scaling helpers for Mode $01 encoders.

Formulas follow SAE J1979 Digital Annex (201702) Scaling/bit columns.
"""

from __future__ import annotations

from decimal import Decimal


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def u8(v: int) -> bytes:
    return bytes([max(0, min(255, int(v))) & 0xFF])


def u16_be(v: int) -> bytes:
    v = max(0, min(0xFFFF, int(v)))
    return bytes([(v >> 8) & 0xFF, v & 0xFF])


def s16_be(v: int) -> bytes:
    v = max(-32768, min(32767, int(v)))
    if v < 0:
        v = (1 << 16) + v
    return bytes([(v >> 8) & 0xFF, v & 0xFF])


def u32_be(v: int) -> bytes:
    v = max(0, min(0xFFFFFFFF, int(v)))
    return bytes(
        [(v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF]
    )


def pct_255(pct: float) -> bytes:
    """100/255 % per bit (0–100%)."""
    raw = int(round(clamp(pct, 0.0, 100.0) * 255.0 / 100.0))
    return u8(raw)


def pct_255_u16(pct: float) -> bytes:
    """Absolute load etc.: A,B with 100/255 % per bit."""
    raw = int(round(clamp(pct, 0.0, 25700.0) * 255.0 / 100.0))
    return u16_be(raw)


def temp_c_offset40(temp_c: float) -> bytes:
    """1 °C/bit with −40 °C offset."""
    return u8(int(round(clamp(temp_c, -40.0, 215.0) + 40.0)))


def fuel_trim_pct(pct: float) -> bytes:
    """100/128 % per bit, 0% at 128 → A = 128 + pct*128/100."""
    raw = int(round(128.0 + clamp(pct, -100.0, 99.2) * 128.0 / 100.0))
    return u8(raw)


def timing_advance_deg(deg: float) -> bytes:
    """½ °/bit with 0° at 128 → A = 2*deg + 128."""
    raw = int(round(clamp(deg, -64.0, 63.5) * 2.0 + 128.0))
    return u8(raw)


def rpm(rpm_val: float) -> bytes:
    """¼ rpm per bit."""
    return u16_be(int(round(clamp(rpm_val, 0.0, 16383.75) * 4.0)))


def maf_gps(gps: float) -> bytes:
    """0.01 g/s per bit."""
    return u16_be(int(round(clamp(gps, 0.0, 655.35) * 100.0)))


def o2_voltage_v(volts: float) -> bytes:
    """0.005 V per bit (byte A of PID $14–$1B)."""
    return u8(int(round(clamp(volts, 0.0, 1.275) / 0.005)))


def eq_ratio(ratio: float) -> bytes:
    """Equivalence ratio: 2/65536 per bit (DA ≈ 3.05e-05)."""
    raw = int(round(clamp(ratio, 0.0, 1.999) / (2.0 / 65536.0)))
    return u16_be(raw)


def wide_o2_voltage_v(volts: float) -> bytes:
    """0.000122 V per bit (≈ 8/65536)."""
    raw = int(round(clamp(volts, 0.0, 7.999) / (8.0 / 65536.0)))
    return u16_be(raw)


def wide_o2_current_ma(ma: float) -> bytes:
    """0.00390625 mA/bit with 0 mA at 32768 (signed around mid-scale)."""
    raw = int(round(ma / 0.00390625 + 32768.0))
    return u16_be(raw)


def catalyst_temp_c(temp_c: float) -> bytes:
    """0.1 °C/bit with −40 °C offset."""
    raw = int(round((clamp(temp_c, -40.0, 6513.5) + 40.0) * 10.0))
    return u16_be(raw)


def torque_pct_offset125(pct: float) -> bytes:
    """1 %/bit with −125 offset."""
    return u8(int(round(clamp(pct, -125.0, 130.0) + 125.0)))


def injection_timing_deg(deg: float) -> bytes:
    """1/128 °/bit with 0° at 26880."""
    raw = int(round(deg * 128.0 + 26880.0))
    return u16_be(raw)


def fuel_rate_lph(lph: float) -> bytes:
    """0.05 L/h per bit."""
    return u16_be(int(round(clamp(lph, 0.0, 3276.75) / 0.05)))


def fuel_pressure_gauge_kpa(kpa: float) -> bytes:
    """3 kPa/bit gauge."""
    return u8(int(round(clamp(kpa, 0.0, 765.0) / 3.0)))


def fuel_rail_rel_kpa(kpa: float) -> bytes:
    """0.079 kPa/bit."""
    return u16_be(int(round(clamp(kpa, 0.0, 5177.0) / 0.079)))


def fuel_rail_kpa10(kpa: float) -> bytes:
    """10 kPa/bit."""
    return u16_be(int(round(clamp(kpa, 0.0, 655350.0) / 10.0)))


def evap_pa_025(pa: float) -> bytes:
    """0.25 Pa/bit signed."""
    return s16_be(int(round(pa / 0.25)))


def evap_abs_kpa(kpa: float) -> bytes:
    """0.005 kPa/bit unsigned."""
    return u16_be(int(round(clamp(kpa, 0.0, 327.675) / 0.005)))


def evap_pa_1(pa: float) -> bytes:
    """1 Pa/bit signed."""
    return s16_be(int(round(pa)))


def module_voltage(v: float) -> bytes:
    """0.001 V/bit."""
    # Decimal avoids binary float artifacts (14.2 * 1000 → 14199.999…)
    q = Decimal(str(clamp(v, 0.0, 65.535))) * Decimal(1000)
    return u16_be(int(q.to_integral_value(rounding="ROUND_HALF_UP")))


def odometer_km(km: float) -> bytes:
    """0.1 km/bit."""
    return u32_be(int(round(clamp(km, 0.0, 429496729.5) * 10.0)))


def fuel_rate_gps(gps: float) -> bytes:
    """0.02 g/s per bit."""
    return u16_be(int(round(clamp(gps, 0.0, 1310.7) / 0.02)))


def exhaust_flow_kgh(kgh: float) -> bytes:
    """0.2 kg/h per bit."""
    return u16_be(int(round(clamp(kgh, 0.0, 13107.0) / 0.2)))


def cylinder_fuel_mg(mg: float) -> bytes:
    """0.03125 mg/stroke per bit."""
    return u16_be(int(round(clamp(mg, 0.0, 2047.96875) / 0.03125)))


def maf_a_gps(gps: float) -> bytes:
    """PID $66 sensor: 0.03125 g/s per bit."""
    return u16_be(int(round(clamp(gps, 0.0, 2047.96875) / 0.03125)))
