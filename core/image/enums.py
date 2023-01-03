from enum import Enum


class Size(Enum):
    """Enum for image size."""

    SMALL = 256
    MEDIUM = 512
    LARGE = 1024

    def get_size(self):
        return f"{self.value}x{self.value}"
