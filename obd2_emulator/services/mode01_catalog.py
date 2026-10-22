"""Mode $01 PID catalog — names & sizes from SAE J1979DA Annex B (201702).

Scaling formulas live in pid_formulas / mode01 encoders. Reserved empty PIDs
$95–$97 omitted. Support PIDs $00/$20/$40/$60/$80/$A0 are bitmask responses.
"""

from __future__ import annotations

from dataclasses import dataclass

# ECU GUI segregation (UX only — wire format stays J1979-native)
ECU_GROUPS: dict[str, str] = {
    "Powertrain": "engine_rpm calculated_load coolant_c intake_air_c maf_gps "
    "throttle_pct timing_advance vehicle_speed_kph absolute_load "
    "relative_throttle throttle_b throttle_c accel_d accel_e accel_f "
    "commanded_throttle oil_temp_c injection_timing_deg fuel_rate_lph "
    "driver_demand_torque_pct actual_torque_pct engine_ref_torque_nm "
    "friction_torque_pct throttle_g runtime_s",
    "Fuel & Trim": "fuel_system_a fuel_system_b stft_b1 ltft_b1 stft_b2 ltft_b2 "
    "fuel_pressure_kpa map_kpa fuel_rail_rel_kpa fuel_rail_kpa "
    "fuel_level_pct alcohol_pct fuel_type commanded_eq_ratio "
    "fuel_rail_abs_kpa engine_fuel_rate_gps vehicle_fuel_rate_gps",
    "Emissions / O2": "o2_loc_13 secondary_air o2_b1s1_v o2_b1s1_trim "
    "wide_b1s1_lambda wide_b1s1_v wide_b1s1_lambda_i wide_b1s1_ma "
    "commanded_egr egr_error_pct evaporative_purge catalyst_b1s1_c "
    "barometric_kpa ambient_c evap_pressure_pa evap_abs_kpa",
    "Hybrid / EV": "hybrid_battery_pct odometer_km",
    "Diesel / Aftertreatment": "nox_nte_status pm_nte_status manifold_surface_c "
    "exhaust_flow_kgh cylinder_fuel_mg",
    "Diagnostics / Status": "mil_on dtc_count monitor_status_b monitor_status_c "
    "monitor_status_d distance_mil_km warmups_since_clear "
    "distance_clear_km runtime_mil_min runtime_clear_min "
    "obd_standard freeze_dtc_hi freeze_dtc_lo",
}


@dataclass(frozen=True)
class PidMeta:
    pid: int
    name: str
    nbytes: int
    group: str = "Other"


# Built from Annex B extraction (scratch/mode01_pid_meta.json) — nbytes verified
PID_META: dict[int, PidMeta] = {}

_RAW: list[tuple[int, str, int, str]] = [
    (0x00, "PIDs supported [$01-$20]", 4, "Diagnostics / Status"),
    (0x01, "Monitor status since DTCs cleared", 4, "Diagnostics / Status"),
    (0x02, "Freeze Frame DTC", 2, "Diagnostics / Status"),
    (0x03, "Fuel system status", 2, "Fuel & Trim"),
    (0x04, "Calculated LOAD Value", 1, "Powertrain"),
    (0x05, "Engine Coolant Temperature", 1, "Powertrain"),
    (0x06, "Short Term Fuel Trim - Bank 1", 1, "Fuel & Trim"),
    (0x07, "Long Term Fuel Trim - Bank 1", 1, "Fuel & Trim"),
    (0x08, "Short Term Fuel Trim - Bank 2", 1, "Fuel & Trim"),
    (0x09, "Long Term Fuel Trim - Bank 2", 1, "Fuel & Trim"),
    (0x0A, "Fuel Pressure (gauge)", 1, "Fuel & Trim"),
    (0x0B, "Intake Manifold Absolute Pressure", 1, "Fuel & Trim"),
    (0x0C, "Engine RPM", 2, "Powertrain"),
    (0x0D, "Vehicle Speed Sensor", 1, "Powertrain"),
    (0x0E, "Ignition Timing Advance", 1, "Powertrain"),
    (0x0F, "Intake Air Temperature", 1, "Powertrain"),
    (0x10, "Air Flow Rate from Mass Air Flow Sensor", 2, "Powertrain"),
    (0x11, "Absolute Throttle Position", 1, "Powertrain"),
    (0x12, "Commanded Secondary Air Status", 1, "Emissions / O2"),
    (0x13, "Location of oxygen sensors", 1, "Emissions / O2"),
    (0x14, "O2 Sensor Bank 1 Sensor 1", 2, "Emissions / O2"),
    (0x15, "O2 Sensor Bank 1 Sensor 2", 2, "Emissions / O2"),
    (0x16, "O2 Sensor Bank 1 Sensor 3", 2, "Emissions / O2"),
    (0x17, "O2 Sensor Bank 1 Sensor 4", 2, "Emissions / O2"),
    (0x18, "O2 Sensor Bank 2 Sensor 1", 2, "Emissions / O2"),
    (0x19, "O2 Sensor Bank 2 Sensor 2", 2, "Emissions / O2"),
    (0x1A, "O2 Sensor Bank 2 Sensor 3", 2, "Emissions / O2"),
    (0x1B, "O2 Sensor Bank 2 Sensor 4", 2, "Emissions / O2"),
    (0x1C, "OBD requirements for vehicle or engine", 1, "Diagnostics / Status"),
    (0x1D, "Location of oxygen sensors", 1, "Emissions / O2"),
    (0x1E, "Auxiliary Input Status", 1, "Diagnostics / Status"),
    (0x1F, "Time Since Engine Start", 2, "Powertrain"),
    (0x20, "PIDs supported [$21-$40]", 4, "Diagnostics / Status"),
    (0x21, "Distance Traveled While MIL is Activated", 2, "Diagnostics / Status"),
    (0x22, "Fuel Pressure relative to manifold vacuum", 2, "Fuel & Trim"),
    (0x23, "Fuel Rail Pressure", 2, "Fuel & Trim"),
    (0x24, "Wide O2 Lambda/Voltage B1S1", 4, "Emissions / O2"),
    (0x25, "Wide O2 Lambda/Voltage B1S2", 4, "Emissions / O2"),
    (0x26, "Wide O2 Lambda/Voltage B1S3", 4, "Emissions / O2"),
    (0x27, "Wide O2 Lambda/Voltage B1S4", 4, "Emissions / O2"),
    (0x28, "Wide O2 Lambda/Voltage B2S1", 4, "Emissions / O2"),
    (0x29, "Wide O2 Lambda/Voltage B2S2", 4, "Emissions / O2"),
    (0x2A, "Wide O2 Lambda/Voltage B2S3", 4, "Emissions / O2"),
    (0x2B, "Wide O2 Lambda/Voltage B2S4", 4, "Emissions / O2"),
    (0x2C, "Commanded EGR", 1, "Emissions / O2"),
    (0x2D, "EGR Error", 1, "Emissions / O2"),
    (0x2E, "Commanded Evaporative Purge", 1, "Emissions / O2"),
    (0x2F, "Fuel Level Input", 1, "Fuel & Trim"),
    (0x30, "Number of warm-ups since DTCs cleared", 1, "Diagnostics / Status"),
    (0x31, "Distance traveled since DTCs cleared", 2, "Diagnostics / Status"),
    (0x32, "Evap System Vapor Pressure", 2, "Emissions / O2"),
    (0x33, "Barometric Pressure", 1, "Emissions / O2"),
    (0x34, "Wide O2 Lambda/Current B1S1", 4, "Emissions / O2"),
    (0x35, "Wide O2 Lambda/Current B1S2", 4, "Emissions / O2"),
    (0x36, "Wide O2 Lambda/Current B1S3", 4, "Emissions / O2"),
    (0x37, "Wide O2 Lambda/Current B1S4", 4, "Emissions / O2"),
    (0x38, "Wide O2 Lambda/Current B2S1", 4, "Emissions / O2"),
    (0x39, "Wide O2 Lambda/Current B2S2", 4, "Emissions / O2"),
    (0x3A, "Wide O2 Lambda/Current B2S3", 4, "Emissions / O2"),
    (0x3B, "Wide O2 Lambda/Current B2S4", 4, "Emissions / O2"),
    (0x3C, "Catalyst Temperature B1S1", 2, "Emissions / O2"),
    (0x3D, "Catalyst Temperature B2S1", 2, "Emissions / O2"),
    (0x3E, "Catalyst Temperature B1S2", 2, "Emissions / O2"),
    (0x3F, "Catalyst Temperature B2S2", 2, "Emissions / O2"),
    (0x40, "PIDs supported [$41-$60]", 4, "Diagnostics / Status"),
    (0x41, "Monitor status this driving cycle", 4, "Diagnostics / Status"),
    (0x42, "Control module voltage", 2, "Powertrain"),
    (0x43, "Absolute Load Value", 2, "Powertrain"),
    (0x44, "Fuel/Air Commanded Equivalence Ratio", 2, "Fuel & Trim"),
    (0x45, "Relative Throttle Position", 1, "Powertrain"),
    (0x46, "Ambient Air Temperature", 1, "Emissions / O2"),
    (0x47, "Absolute Throttle Position B", 1, "Powertrain"),
    (0x48, "Absolute Throttle Position C", 1, "Powertrain"),
    (0x49, "Accelerator Pedal Position D", 1, "Powertrain"),
    (0x4A, "Accelerator Pedal Position E", 1, "Powertrain"),
    (0x4B, "Accelerator Pedal Position F", 1, "Powertrain"),
    (0x4C, "Commanded Throttle Actuator Control", 1, "Powertrain"),
    (0x4D, "Engine run time while MIL activated", 2, "Diagnostics / Status"),
    (0x4E, "Engine run time since DTCs cleared", 2, "Diagnostics / Status"),
    (0x4F, "External Test Equipment Configuration #1", 4, "Diagnostics / Status"),
    (0x50, "External Test Equipment Configuration #2", 4, "Diagnostics / Status"),
    (0x51, "Type of fuel currently being utilized", 1, "Fuel & Trim"),
    (0x52, "Alcohol Fuel Percentage", 1, "Fuel & Trim"),
    (0x53, "Absolute Evap System Vapor Pressure", 2, "Emissions / O2"),
    (0x54, "Evap System Vapor Pressure", 2, "Emissions / O2"),
    (0x55, "Short Term Secondary O2 Fuel Trim B1", 1, "Emissions / O2"),
    (0x56, "Long Term Secondary O2 Fuel Trim B1", 1, "Emissions / O2"),
    (0x57, "Short Term Secondary O2 Fuel Trim B2", 1, "Emissions / O2"),
    (0x58, "Long Term Secondary O2 Fuel Trim B2", 1, "Emissions / O2"),
    (0x59, "Fuel Rail Pressure (absolute)", 2, "Fuel & Trim"),
    (0x5A, "Relative Accelerator Pedal Position", 1, "Powertrain"),
    (0x5B, "Hybrid Battery Pack Remaining Charge", 1, "Hybrid / EV"),
    (0x5C, "Engine Oil Temperature", 1, "Powertrain"),
    (0x5D, "Fuel Injection Timing", 2, "Powertrain"),
    (0x5E, "Engine Fuel Rate", 2, "Powertrain"),
    (0x5F, "Emission requirements to which vehicle is designed", 1, "Diagnostics / Status"),
    (0x60, "PIDs supported [$61-$80]", 4, "Diagnostics / Status"),
    (0x61, "Driver's Demand Engine - Percent Torque", 1, "Powertrain"),
    (0x62, "Actual Engine - Percent Torque", 1, "Powertrain"),
    (0x63, "Engine Reference Torque", 2, "Powertrain"),
    (0x64, "Engine Percent Torque Data", 5, "Powertrain"),
    (0x65, "Auxiliary Inputs/Output Status", 2, "Diesel / Aftertreatment"),
    (0x66, "Mass Air Flow Sensor", 5, "Powertrain"),
    (0x67, "Engine Coolant Temperature (sensors)", 3, "Powertrain"),
    (0x68, "Intake Air Temperature (sensors)", 7, "Powertrain"),
    (0x69, "Commanded EGR and EGR Error", 7, "Diesel / Aftertreatment"),
    (0x6A, "Commanded Diesel Intake Air Flow Control", 5, "Diesel / Aftertreatment"),
    (0x6B, "Exhaust Gas Recirculation Temperature", 5, "Diesel / Aftertreatment"),
    (0x6C, "Commanded Throttle Actuator Control", 5, "Diesel / Aftertreatment"),
    (0x6D, "Fuel Pressure Control System", 11, "Diesel / Aftertreatment"),
    (0x6E, "Injection Pressure Control System", 9, "Diesel / Aftertreatment"),
    (0x6F, "Turbocharger Compressor Inlet Pressure", 3, "Diesel / Aftertreatment"),
    (0x70, "Boost Pressure Control", 10, "Diesel / Aftertreatment"),
    (0x71, "Variable Geometry Turbo Control", 6, "Diesel / Aftertreatment"),
    (0x72, "Wastegate Control", 5, "Diesel / Aftertreatment"),
    (0x73, "Exhaust Pressure", 5, "Diesel / Aftertreatment"),
    (0x74, "Turbocharger RPM", 5, "Diesel / Aftertreatment"),
    (0x75, "Turbocharger A Temperature", 7, "Diesel / Aftertreatment"),
    (0x76, "Turbocharger B Temperature", 7, "Diesel / Aftertreatment"),
    (0x77, "Charge Air Cooler Temperature", 5, "Diesel / Aftertreatment"),
    (0x78, "Exhaust Gas Temperature Bank 1", 9, "Diesel / Aftertreatment"),
    (0x79, "Exhaust Gas Temperature Bank 2", 9, "Diesel / Aftertreatment"),
    (0x7A, "Diesel Particulate Filter Bank 1", 7, "Diesel / Aftertreatment"),
    (0x7B, "Diesel Particulate Filter Bank 2", 7, "Diesel / Aftertreatment"),
    (0x7C, "Diesel Particulate Filter Temperature", 9, "Diesel / Aftertreatment"),
    (0x7D, "NOx NTE control area status", 1, "Diesel / Aftertreatment"),
    (0x7E, "PM NTE control area status", 1, "Diesel / Aftertreatment"),
    (0x7F, "Engine Run Time", 13, "Powertrain"),
    (0x80, "PIDs supported [$81-$A0]", 4, "Diagnostics / Status"),
    (0x81, "Engine Run Time for AECD #1-#5", 16, "Diesel / Aftertreatment"),
    (0x82, "Engine Run Time for AECD #6-#10", 16, "Diesel / Aftertreatment"),
    (0x83, "NOx Sensor", 9, "Diesel / Aftertreatment"),
    (0x84, "Manifold Surface Temperature", 1, "Diesel / Aftertreatment"),
    (0x85, "NOx Control System", 10, "Diesel / Aftertreatment"),
    (0x86, "Particulate Matter Sensor", 5, "Diesel / Aftertreatment"),
    (0x87, "Intake Manifold Absolute Pressure", 5, "Diesel / Aftertreatment"),
    (0x88, "SCR Inducement System", 13, "Diesel / Aftertreatment"),
    (0x89, "Engine Run Time for AECD #11-#15", 16, "Diesel / Aftertreatment"),
    (0x8A, "Engine Run Time for AECD #16-#20", 16, "Diesel / Aftertreatment"),
    (0x8B, "Diesel Aftertreatment Status", 7, "Diesel / Aftertreatment"),
    (0x8C, "O2 Sensor (Wide Range)", 16, "Emissions / O2"),
    (0x8D, "Absolute Throttle Position G", 1, "Powertrain"),
    (0x8E, "Engine Friction - Percent Torque", 1, "Powertrain"),
    (0x8F, "Particulate Matter (PM) Sensor Output", 7, "Diesel / Aftertreatment"),
    (0x90, "WWH-OBD Vehicle OBD System Information", 3, "Diagnostics / Status"),
    (0x91, "WWH-OBD ECU OBD System Information", 5, "Diagnostics / Status"),
    (0x92, "Fuel system status (Compression Ignition)", 2, "Fuel & Trim"),
    (0x93, "WWH-OBD Vehicle OBD Counters", 3, "Diagnostics / Status"),
    (0x94, "NOx control driver inducement counters", 12, "Diesel / Aftertreatment"),
    (0x98, "Exhaust Gas Temperature Bank 1", 9, "Diesel / Aftertreatment"),
    (0x99, "Exhaust Gas Temperature Bank 2", 9, "Diesel / Aftertreatment"),
    (0x9A, "Hybrid/EV Vehicle System Data", 6, "Hybrid / EV"),
    (0x9B, "Diesel Exhaust Fluid Sensor Output", 4, "Diesel / Aftertreatment"),
    (0x9C, "O2 Sensor (Wide Range)", 16, "Emissions / O2"),
    (0x9D, "Fuel Rate", 4, "Fuel & Trim"),
    (0x9E, "Engine Exhaust Flow Rate", 2, "Diesel / Aftertreatment"),
    (0x9F, "Fuel System Percentage Use", 9, "Fuel & Trim"),
    (0xA0, "PIDs supported [$A1-$C0]", 4, "Diagnostics / Status"),
    (0xA1, "NOx Sensor Corrected", 9, "Diesel / Aftertreatment"),
    (0xA2, "Cylinder Fuel Rate", 2, "Diesel / Aftertreatment"),
    (0xA3, "Evap System Vapor Pressure", 9, "Emissions / O2"),
    (0xA4, "Transmission Actual Gear", 4, "Powertrain"),
    (0xA5, "Diesel Exhaust Fluid Dosing", 4, "Diesel / Aftertreatment"),
    (0xA6, "Vehicle Odometer", 4, "Hybrid / EV"),
    (0xA7, "NOx Sensor", 9, "Diesel / Aftertreatment"),
    (0xA8, "NOx Sensor Corrected", 9, "Diesel / Aftertreatment"),
    (0xA9, "Motorcycle Input/Output Status", 2, "Other"),
]

for _pid, _name, _nb, _grp in _RAW:
    PID_META[_pid] = PidMeta(_pid, _name, _nb, _grp)

# All non-support PIDs we advertise as supported
SUPPORTED_PIDS: frozenset[int] = frozenset(
    p for p in PID_META if p % 0x20 != 0
)


def supported_bitmask(base: int, supported: frozenset[int] | set[int]) -> bytes:
    """Annex A: 4 data bytes; bit7 of A = PID base+1 … bit0 of D = base+0x20."""
    bits = 0
    for off in range(1, 0x21):
        pid = base + off
        if off == 0x20:
            # Next support-PID bit: set if any PIDs exist beyond this range
            if any(p > base + 0x20 for p in supported):
                bits |= 1
            elif base + 0x20 in PID_META and any(
                p in supported for p in range(base + 0x21, base + 0x40)
            ):
                bits |= 1
        elif pid in supported:
            bits |= 1 << (32 - off)
    return bits.to_bytes(4, "big")


def support_pids_present() -> list[int]:
    return [p for p in sorted(PID_META) if p % 0x20 == 0]
