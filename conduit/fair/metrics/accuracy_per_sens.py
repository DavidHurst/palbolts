"""Accuracy per sensitive group."""
from typing import Any

import torch
from torchmetrics import Accuracy

__all__ = ["AccuracyPerSens"]


class AccuracyPerSens(Accuracy):
    """Accuracy Metric."""

    def __init__(self, sens: int, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sens = sens

    @property
    def __name__(self) -> str:
        return f"Accuracy_s{self.sens}"

    def update(self, preds: torch.Tensor, sens: torch.Tensor, target: torch.Tensor) -> None:
        """Update state with predictions and targets.

        :param preds: Predictions from model
        :param sens: Ground truth sensitive labels
        :param target: Ground truth values
        """
        mask = sens == self.sens
        if mask.sum() > 0:
            super().update(preds[mask], target[mask])
