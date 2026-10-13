"""Tests for the comparison metric, independent of the game capture."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from compare_mft_menu import dice


class MetricTests(unittest.TestCase):
    def test_identical(self):
        mask = np.array([[True, False], [False, True]])
        self.assertEqual(dice(mask, mask), 1.0)

    def test_disjoint(self):
        mask = np.array([[True, False]])
        self.assertEqual(dice(mask, ~mask), 0.0)

    def test_partial(self):
        self.assertAlmostEqual(dice(np.array([True, True, False]), np.array([False, True, True])), 0.5)

    def test_empty(self):
        self.assertEqual(dice(np.zeros(4, dtype=bool), np.zeros(4, dtype=bool)), 0.0)


if __name__ == '__main__':
    unittest.main()
