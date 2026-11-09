"""Support tickets (sample under review)."""
from enum import Enum


class State(Enum):
    OPEN = "open"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


TRANSITIONS = {
    State.OPEN: {State.WAITING, State.RESOLVED},
    State.WAITING: {State.OPEN, State.RESOLVED},
    State.RESOLVED: {State.OPEN, State.CLOSED},
    State.CLOSED: set(),
}


def move(ticket, target):
    """The only writer of ticket["state"]."""
    if target not in TRANSITIONS[ticket["state"]]:
        raise ValueError(f"cannot move {ticket['state'].value} to {target.value}")
    ticket["state"] = target
    return ticket


def label(ticket):
    return ticket["state"].value
