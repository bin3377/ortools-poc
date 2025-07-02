from enum import Enum


class MobilityAssistanceType(str, Enum):
    """Mobility assistance type enumeration"""

    AMBULATORY = "AMBI"
    WHEELCHAIR = "WC"
    STRETCHER = "GUR"

    def priority(self) -> int:
        """Get priority from mobility assistance (0=highest, 2=lowest)"""
        if self.value == self.STRETCHER:
            return 0
        if self.value == self.WHEELCHAIR:
            return 1
        return 2

    @classmethod
    def from_string(cls, s: str) -> "MobilityAssistanceType":
        """Parse mobility assistance from a string"""
        s_upper = s.upper()
        if s_upper == "STRETCHER":
            return cls.STRETCHER
        elif s_upper == "WHEELCHAIR":
            return cls.WHEELCHAIR
        else:
            return cls.AMBULATORY

    @classmethod
    def from_strings(cls, *args: str) -> "MobilityAssistanceType":
        """Parse mobility assistance from strings"""
        for arg in args:
            return cls.from_string(arg)
        return cls.AMBULATORY
