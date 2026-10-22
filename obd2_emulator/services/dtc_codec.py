"""SAE J2012 / J1979 2-byte DTC packing (Mode $03)."""

from __future__ import annotations

_SYSTEM = {"P": 0, "C": 1, "B": 2, "U": 3}
_SYSTEM_REV = {v: k for k, v in _SYSTEM.items()}


def encode_dtc(code: str) -> bytes:
    """Encode e.g. P0301 → two bytes (high, low)."""
    c = code.strip().upper()
    if len(c) != 5 or c[0] not in _SYSTEM:
        raise ValueError(f"invalid DTC code: {code!r}")
    try:
        d1 = int(c[1])
        d2 = int(c[2], 16)
        d3 = int(c[3], 16)
        d4 = int(c[4], 16)
    except ValueError as exc:
        raise ValueError(f"invalid DTC code: {code!r}") from exc
    if d1 > 3:
        raise ValueError(f"invalid DTC first digit: {code!r}")
    hi = (_SYSTEM[c[0]] << 6) | (d1 << 4) | d2
    lo = (d3 << 4) | d4
    return bytes([hi & 0xFF, lo & 0xFF])


def decode_dtc(hi: int, lo: int) -> str:
    """Decode two DTC bytes → e.g. P0301."""
    sys = (hi >> 6) & 0x03
    d1 = (hi >> 4) & 0x03
    d2 = hi & 0x0F
    d3 = (lo >> 4) & 0x0F
    d4 = lo & 0x0F
    return f"{_SYSTEM_REV[sys]}{d1}{d2:X}{d3:X}{d4:X}"
