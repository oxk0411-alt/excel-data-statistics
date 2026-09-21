import tempfile
import unittest
from pathlib import Path

import pandas as pd

from table_cleaner.export import (
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    sanitize_dataframe_for_export,
    suggest_output_name,
)
from table_cleaner.io_utils import read_table


class InputExportTests(unittest.TestCase):
    def test_reads_utf8_bom_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_text("名称,金额\n甲,10\n乙,\n", encoding="utf-8-sig")
            dataframe = read_table(path)
        self.assertEqual(dataframe.shape, (2, 2))
        self.assertEqual(dataframe.iloc[0]["名称"], "甲")

    def test_sanitizes_formula_cells(self) -> None:
        dataframe = pd.DataFrame({"value": ["=1+1", "+cmd", "normal", 3]})
        sanitized = sanitize_dataframe_for_export(dataframe)
        self.assertEqual(sanitized.iloc[0]["value"], "'=1+1")
        self.assertEqual(sanitized.iloc[1]["value"], "'+cmd")
        self.assertEqual(sanitized.iloc[2]["value"], "normal")

    def test_exports_csv_and_excel(self) -> None:
        dataframe = pd.DataFrame({"name": ["A"], "value": [1]})
        self.assertTrue(dataframe_to_csv_bytes(dataframe).startswith(b"\xef\xbb\xbf"))
        self.assertGreater(len(dataframe_to_excel_bytes(dataframe)), 1000)
        self.assertEqual(suggest_output_name("sales.xlsx", ".csv"), "sales_cleaned.csv")


if __name__ == "__main__":
    unittest.main()
