class Flags:
    """Utility for working with integer bitflags.

    Usage:
        Flags.VERIFIED  # constant for first bit
        f = Flags.from_int(0)
        f.set(Flags.VERIFIED)
        if f.has(Flags.VERIFIED): ...
    """

    VERIFIED = 1 << 0

    def __init__(self, value: int = 0):
        self.value = int(value or 0)

    @classmethod
    def from_int(cls, value: int):
        return cls(value or 0)

    def has(self, flag: int) -> bool:
        return bool(self.value & flag)

    def set(self, flag: int):
        self.value |= flag
        return self

    def clear(self, flag: int):
        self.value &= ~flag
        return self

    def to_int(self) -> int:
        return int(self.value)

    def __int__(self):
        return self.to_int()
