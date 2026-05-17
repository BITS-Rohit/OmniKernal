
from enum import StrEnum


class PacketState(StrEnum):
    """
    State of the packet in the OmniKernal pipeline.
    """
    RECEIVED = "RECEIVED"  # Raw message arrived
    MAPPED = "MAPPED" # Cache check & Execution Handler Mapping.
    SANITIZED = "SANITIZED"  # Text cleaned, prefix confirmed
    ROUTED = "ROUTED"  # Route found, args parsed
    EXECUTING = "EXECUTING"  # Handler is running
    DONE = "DONE"  # Handler resolved successfully
    FAILED = "FAILED"  # Handler or Core reported failure
    DROPPED = "DROPPED"  # No route found — silently discarded + logged
