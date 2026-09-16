"""Two-parameter logistic IRT helpers for adaptive exam selection."""

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


@dataclass(frozen=True)
class IRTItem:
    question_id: str
    discrimination: float
    difficulty: float


@dataclass(frozen=True)
class AbilityEstimate:
    theta: float
    standard_error: float
    lower_bound: float
    upper_bound: float


class IRTService:
    def probability(self, theta: float, item: IRTItem) -> float:
        exponent = max(-35.0, min(35.0, item.discrimination * (theta - item.difficulty)))
        return 1.0 / (1.0 + math.exp(-exponent))

    def information(self, theta: float, item: IRTItem) -> float:
        probability = self.probability(theta, item)
        return item.discrimination**2 * probability * (1.0 - probability)

    def update(self, theta: float, item: IRTItem, correct: bool, learning_rate: float = 0.5) -> float:
        delta = (1.0 if correct else 0.0) - self.probability(theta, item)
        return max(-4.0, min(4.0, theta + learning_rate * delta * max(0.1, item.discrimination)))

    def estimate(self, responses: Iterable[tuple[IRTItem, bool]], starting_theta: float = 0.0) -> AbilityEstimate:
        theta = starting_theta
        total_information = 0.0
        for item, correct in responses:
            theta = self.update(theta, item, correct)
            total_information += self.information(theta, item)
        standard_error = 1.0 / math.sqrt(max(total_information, 1e-6))
        margin = 1.96 * standard_error
        return AbilityEstimate(theta, standard_error, theta - margin, theta + margin)

    def select_next(self, theta: float, items: Sequence[IRTItem], answered_ids: set[str]) -> IRTItem | None:
        available = [item for item in items if item.question_id not in answered_ids]
        if not available:
            return None
        return max(available, key=lambda item: self.information(theta, item))


irt_service = IRTService()
