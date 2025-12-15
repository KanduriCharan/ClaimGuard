from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ExposureConfig:
    name: str
    outcomes: List[str]
    confounders: List[str]


@dataclass
class DomainConfig:
    exposures: List[ExposureConfig]


DOMAIN_DICTIONARY: Dict[str, DomainConfig] = {
    "health": DomainConfig(
        exposures=[
            ExposureConfig(
                name="coffee",
                outcomes=["sleep quality", "focus", "anxiety"],
                confounders=["sleep", "age", "stress", "workload"],
            ),
            ExposureConfig(
                name="caffeine",
                outcomes=["sleep quality", "alertness", "anxiety"],
                confounders=["sleep", "age", "stress"],
            ),
            ExposureConfig(
                name="exercise",
                outcomes=["anxiety", "weight", "mood"],
                confounders=["diet", "age", "baseline health"],
            ),
            ExposureConfig(
                name="sugar",
                outcomes=["weight gain", "energy", "metabolism"],
                confounders=["metabolism", "activity level", "age"],
            ),
            ExposureConfig(
                name="screen time",
                outcomes=["sleep quality", "focus"],
                confounders=["age", "stress", "time of day"],
            ),
        ]
    ),
    "finance": DomainConfig(
        exposures=[
            ExposureConfig(
                name="positive news",
                outcomes=["stock return", "volume"],
                confounders=["market trend", "sector shock", "macro conditions"],
            ),
            ExposureConfig(
                name="tweet sentiment",
                outcomes=["stock return", "volume", "volatility"],
                confounders=["market trend", "bot activity", "fake accounts", "macro data"],
            ),
            ExposureConfig(
                name="earnings surprise",
                outcomes=["stock return", "volatility"],
                confounders=["guidance revisions", "macroeconomic conditions", "sector performance"],
            ),
            ExposureConfig(
                name="rate cut",
                outcomes=["stock return", "volatility", "market stability"],
                confounders=["inflation", "economic growth", "global market signals"],
            ),
        ]
    ),
}
