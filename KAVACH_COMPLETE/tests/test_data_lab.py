import unittest
import pandas as pd
from kavach.data_lab import find_column, valid_coordinate_frame

class TestSatelliteDataLab(unittest.TestCase):
    def test_find_column_ignores_case_and_spaces(self):
        self.assertEqual(find_column(["Acq Date", "LATITUDE"], ["acq_date"]), "Acq Date")

    def test_valid_coordinate_frame_drops_invalid_rows(self):
        df = pd.DataFrame({"lat": [23.2, 999, None], "lon": [77.4, 77.5, 77.6]})
        result = valid_coordinate_frame(df, "lat", "lon")
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result.iloc[0]["_latitude"], 23.2)

if __name__ == "__main__":
    unittest.main()
