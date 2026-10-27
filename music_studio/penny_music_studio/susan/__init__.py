"""SUSAN: trainable symbolic composition for Penny Music Studio.

No ML framework is imported until train/inference is explicitly requested.
"""
from .composer import SusanComposerBackend, train_susan, check_susan, OptionalNeuralDependency

__all__ = ['SusanComposerBackend', 'train_susan', 'check_susan', 'OptionalNeuralDependency']
