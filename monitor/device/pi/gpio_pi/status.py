from enum import Enum


class Result(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    APPROVAL = "APPROVAL"
    UNKNOWN = "UNKNOWN"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    NONE = "NONE"
