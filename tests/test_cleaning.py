import unittest

import pandas as pd

from table_cleaner.cleaning import CleaningOptions, clean_table


class CleaningTests(unittest.TestCase):
    def test_removes_duplicates_after_trimming(self) -> None:
        dataframe = pd.DataFrame(
            {
                " 姓名 ": [" 张三 ", "张三", "李四"],
                "金额": [10, 10, 20],
            }
        )

        cleaned, report = clean_table(dataframe)

        self.assertEqual(len(cleaned), 2)
        self.assertEqual(report.removed_duplicates, 1)
        self.assertEqual(cleaned.iloc[0]["姓名"], "张三")
        self.assertNotIn(" 姓名 ", cleaned.columns)

    def test_fills_numeric_and_text_missing_values(self) -> None:
        dataframe = pd.DataFrame(
            {
                "number": [1.0, None, 3.0],
                "text": ["a", None, "a"],
            }
        )
        options = CleaningOptions(
            normalize_columns=False,
            drop_empty_rows=False,
            missing_strategy="fill",
            fill_method="auto",
        )

        cleaned, report = clean_table(dataframe, options)

        self.assertEqual(cleaned.loc[1, "number"], 2.0)
        self.assertEqual(cleaned.loc[1, "text"], "a")
        self.assertEqual(report.filled_cells, 2)

    def test_drops_rows_with_any_missing_value(self) -> None:
        dataframe = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", None]})
        options = CleaningOptions(
            normalize_columns=False,
            missing_strategy="drop_rows",
        )

        cleaned, report = clean_table(dataframe, options)

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(report.removed_missing_rows, 2)


if __name__ == "__main__":
    unittest.main()
