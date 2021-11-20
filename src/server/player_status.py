import enum
@enum.unique
class PlayerStatus(enum.IntEnum):
    ONLINE = 0
    DISCONNECTED = 1
    OFFLINE = 2