import unittest
from unittest.mock import patch

import pandas as pd

from src import etf_premium_rate as mod


class GetEtfRealtimeDataTests(unittest.TestCase):
    def test_falls_back_to_baostock_when_primary_source_returns_non_spot_shape(self):
        malformed_history_df = pd.DataFrame(
            {
                "date": ["2026-03-06"],
                "close": [1.234],
                "volume": [1000],
            }
        )
        baostock_df = pd.DataFrame(
            {
                "代码": ["510050"],
                "名称": ["上证50ETF"],
                "最新价": [1.235],
                "成交量": [2000.0],
                "基金类型": ["ETF"],
            }
        )

        with patch.object(mod, "_get_spot_tushare", return_value=None), patch.object(
            mod.ak, "fund_etf_spot_em", return_value=malformed_history_df
        ), patch.object(
            mod, "_get_spot_baostock", return_value=baostock_df
        ):
            result = mod.get_etf_realtime_data()

        pd.testing.assert_frame_equal(result, baostock_df)


if __name__ == "__main__":
    unittest.main()
