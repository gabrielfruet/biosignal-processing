"""Pipeline stages."""

from biosignal.stages import acquisition, sqi, statistics, cleaning, segmentation, features, engineering, dimreduction

__all__ = [
    "acquisition",
    "sqi",
    "statistics",
    "cleaning",
    "segmentation",
    "features",
    "engineering",
    "dimreduction",
]
