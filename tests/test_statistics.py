import unittest

import pandas as pd

from table_cleaner.statistics import (
    column_profile,
    correlation_matrix,
    dataset_overview,
    group_summary,
    numeric_summary,
)


class StatisticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataframe = pd.DataFrame(
            {
                "region": ["east", "east", "west"],
                "sales": [100.0, 200.0, 150.0],
                "quantity": [1, 2, 3],
            }
        )

    def test_dataset_overview(self) -> None:
        overview = dataset_overview(self.dataframe)
        self.assertEqual(overview["rows"], 3)
        self.assertEqual(overview["columns"], 3)
        self.assertEqual(overview["missing_cells"], 0)

    def test_profile_and_numeric_summary(self) -> None:
        profile = column_profile(self.dataframe)
        summary = numeric_summary(self.dataframe)
        self.assertEqual(set(profile["column"]), {"region", "sales", "quantity"})
        self.assertEqual(set(summary["column"]), {"sales", "quantity"})

    def test_correlation_and_group_summary(self) -> None:
        correlation = correlation_matrix(self.dataframe)
        grouped = group_summary(self.dataframe, "region", "sales", "sum")
        self.assertEqual(correlation.shape, (2, 2))
        self.assertEqual(int(grouped.iloc[0]["sales"]), 300)


if __name__ == "__main__":
    unittest.main()
