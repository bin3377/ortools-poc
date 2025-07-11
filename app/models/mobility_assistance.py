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

    def compatible(self, bookingType: "MobilityAssistanceType") -> bool:
        """Check if mobility assistance of vehicle is compatible with booking type"""
        if self.value == bookingType.value:
            return True
        if bookingType == self.AMBULATORY:
            return True
        return False

    @classmethod
    def from_string(cls, s: str) -> "MobilityAssistanceType":
        """Parse mobility assistance from a string"""
        s_upper = s.upper()
        if s_upper == "STRETCHER" or s_upper == "GUR":
            return cls.STRETCHER
        elif s_upper == "WHEELCHAIR" or s_upper == "WC":
            return cls.WHEELCHAIR
        else:
            return cls.AMBULATORY

    @classmethod
    def from_strings(cls, *args: str) -> "MobilityAssistanceType":
        """Parse mobility assistance from strings"""
        for arg in args:
            one = cls.from_string(arg)
            if one != cls.AMBULATORY:
                return one
        return cls.AMBULATORY

    @classmethod
    def from_multiple(cls, *args: "MobilityAssistanceType") -> "MobilityAssistanceType":
        """Parse mobility assistance from multiple types"""
        for arg in args:
            if arg != cls.AMBULATORY:
                return arg
        return cls.AMBULATORY
