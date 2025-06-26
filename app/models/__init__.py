from enum import Enum

from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated

# Data models

# Represents an ObjectId field in the mongodb.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
type PyObjectId = Annotated[str, BeforeValidator(str)]


class MobilityAssistanceType(str, Enum):
    """Mobility assistance type enumeration"""

    AMBULATORY = "AMBULATORY"
    WHEELCHAIR = "WHEELCHAIR"
    STRETCHER = "STRETCHER"

