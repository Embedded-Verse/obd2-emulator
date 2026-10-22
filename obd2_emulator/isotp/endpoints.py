"""ISO 15765-2/4 endpoints for OBD ECU (11-bit + 29-bit, physical + functional).

Functional requests (0x7DF / 0x18DB33F1) are received on dedicated stacks, but
multi-frame *responses* are always transmitted via the matching physical stack
so Flow Control arrives on 0x7E0 / 0x18DA10F1 (ISO 15765-4 / ELM327 behavior).
"""

from __future__ import annotations

from dataclasses import dataclass

import can
import isotp

# ISO 15765-4 defaults (ELM327 / light-vehicle OBD)
ID_11_FUNC = 0x7DF
ID_11_PHYS_REQ = 0x7E0
ID_11_PHYS_RESP = 0x7E8
ID_29_FUNC = 0x18DB33F1
ID_29_PHYS_REQ = 0x18DA10F1
ID_29_PHYS_RESP = 0x18DAF110


@dataclass(frozen=True)
class IsotpIds:
    """Legacy physical 11-bit pair (kept for config/CLI)."""

    request_id: int = ID_11_PHYS_REQ
    response_id: int = ID_11_PHYS_RESP
    functional_id: int = ID_11_FUNC
    listen_functional: bool = True
    listen_extended: bool = True
    ext_request_id: int = ID_29_PHYS_REQ
    ext_response_id: int = ID_29_PHYS_RESP
    ext_functional_id: int = ID_29_FUNC


@dataclass(frozen=True)
class EndpointSpec:
    name: str
    address: isotp.Address
    # Send responses on this endpoint (physical) so FC uses phys request ID
    reply_name: str


def make_ecu_address(ids: IsotpIds | None = None) -> isotp.Address:
    """ECU physical 11-bit address: RX request, TX response."""
    ids = ids or IsotpIds()
    return isotp.Address(
        addressing_mode=isotp.AddressingMode.Normal_11bits,
        txid=int(ids.response_id) & 0x7FF,
        rxid=int(ids.request_id) & 0x7FF,
    )


def make_tester_address(ids: IsotpIds | None = None) -> isotp.Address:
    """Tester address (inverse of ECU physical) — for bench scripts."""
    ids = ids or IsotpIds()
    return isotp.Address(
        addressing_mode=isotp.AddressingMode.Normal_11bits,
        txid=int(ids.request_id) & 0x7FF,
        rxid=int(ids.response_id) & 0x7FF,
    )


def make_ecu_endpoint_specs(ids: IsotpIds | None = None) -> list[EndpointSpec]:
    """All ECU RX/TX pairs ELM327 / ISO 15765-4 needs on one bus bitrate."""
    ids = ids or IsotpIds()
    phys_11 = "phys_11"
    phys_29 = "phys_29"
    specs: list[EndpointSpec] = [
        EndpointSpec(
            phys_11,
            isotp.Address(
                addressing_mode=isotp.AddressingMode.Normal_11bits,
                txid=int(ids.response_id) & 0x7FF,
                rxid=int(ids.request_id) & 0x7FF,
            ),
            reply_name=phys_11,
        )
    ]
    if ids.listen_functional:
        specs.append(
            EndpointSpec(
                "func_11",
                isotp.Address(
                    addressing_mode=isotp.AddressingMode.Normal_11bits,
                    txid=int(ids.response_id) & 0x7FF,
                    rxid=int(ids.functional_id) & 0x7FF,
                ),
                reply_name=phys_11,
            )
        )
    if ids.listen_extended:
        specs.append(
            EndpointSpec(
                phys_29,
                isotp.Address(
                    addressing_mode=isotp.AddressingMode.Normal_29bits,
                    txid=int(ids.ext_response_id) & 0x1FFFFFFF,
                    rxid=int(ids.ext_request_id) & 0x1FFFFFFF,
                ),
                reply_name=phys_29,
            )
        )
        if ids.listen_functional:
            specs.append(
                EndpointSpec(
                    "func_29",
                    isotp.Address(
                        addressing_mode=isotp.AddressingMode.Normal_29bits,
                        txid=int(ids.ext_response_id) & 0x1FFFFFFF,
                        rxid=int(ids.ext_functional_id) & 0x1FFFFFFF,
                    ),
                    reply_name=phys_29,
                )
            )
    return specs


def make_stack(
    bus: can.BusABC,
    address: isotp.Address,
    notifier: can.Notifier | None = None,
) -> isotp.CanStack | isotp.NotifierBasedCanStack:
    """Prefer NotifierBased stack when a shared Notifier is provided."""
    if notifier is not None:
        return isotp.NotifierBasedCanStack(bus=bus, notifier=notifier, address=address)
    return isotp.CanStack(bus=bus, address=address)
