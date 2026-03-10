import unittest
from unittest.mock import patch
from types import SimpleNamespace

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
            mod, "_get_spot_finshare", return_value=None
        ), patch.object(
            mod, "_get_spot_baostock", return_value=baostock_df
        ):
            result = mod.get_etf_realtime_data()

        pd.testing.assert_frame_equal(result, baostock_df)

    def test_falls_back_to_finshare_when_akshare_returns_non_spot_shape(self):
        malformed_history_df = pd.DataFrame(
            {
                "date": ["2026-03-10"],
                "close": [1.0],
                "volume": [1000],
            }
        )
        finshare_df = pd.DataFrame(
            {
                "代码": ["510300"],
                "名称": ["沪深300ETF"],
                "最新价": [1.001],
                "成交量": [12345.0],
                "基金类型": ["ETF"],
            }
        )

        with patch.object(mod, "_get_spot_tushare", return_value=None), patch.object(
            mod.ak, "fund_etf_spot_em", return_value=malformed_history_df
        ), patch.object(
            mod, "_get_spot_finshare", return_value=finshare_df, create=True
        ), patch.object(
            mod, "_get_spot_baostock", return_value=None
        ):
            result = mod.get_etf_realtime_data()

        pd.testing.assert_frame_equal(result, finshare_df)

    def test_falls_back_to_tushare_when_finshare_returns_none(self):
        call_sequence = []
        tushare_df = pd.DataFrame(
            {
                "代码": ["510050"],
                "名称": ["上证50ETF"],
                "最新价": [1.235],
                "成交量": [2000.0],
                "基金类型": ["ETF"],
            }
        )

        def fake_akshare():
            call_sequence.append("akshare")
            raise Exception("akshare unavailable")

        def fake_finshare(fund_type="ETF"):
            call_sequence.append("finshare")
            return None

        def fake_tushare(fund_type="ETF"):
            call_sequence.append("tushare")
            return tushare_df

        with patch.object(mod, "_get_spot_tushare", side_effect=fake_tushare), patch.object(
            mod.ak, "fund_etf_spot_em", side_effect=fake_akshare
        ), patch.object(
            mod, "_get_spot_finshare", side_effect=fake_finshare, create=True
        ), patch.object(
            mod, "_get_spot_baostock", return_value=None
        ):
            result = mod.get_etf_realtime_data()

        pd.testing.assert_frame_equal(result, tushare_df)
        self.assertEqual(call_sequence, ["akshare", "finshare", "tushare"])


class GetLofRealtimeDataTests(unittest.TestCase):
    def test_falls_back_to_baostock_when_finshare_and_tushare_fail(self):
        call_sequence = []
        baostock_df = pd.DataFrame(
            {
                "代码": ["163402"],
                "名称": ["兴全趋势LOF"],
                "最新价": [1.888],
                "成交量": [6789.0],
                "基金类型": ["LOF"],
            }
        )

        def fake_akshare():
            call_sequence.append("akshare")
            raise Exception("akshare unavailable")

        def fake_finshare(fund_type="LOF"):
            call_sequence.append("finshare")
            return None

        def fake_tushare(fund_type="LOF"):
            call_sequence.append("tushare")
            return None

        def fake_baostock(fund_type="LOF"):
            call_sequence.append("baostock")
            return baostock_df

        with patch.object(mod, "_get_spot_tushare", side_effect=fake_tushare), patch.object(
            mod.ak, "fund_lof_spot_em", side_effect=fake_akshare
        ), patch.object(
            mod, "_get_spot_finshare", side_effect=fake_finshare, create=True
        ), patch.object(
            mod, "_get_spot_baostock", side_effect=fake_baostock
        ):
            result = mod.get_lof_realtime_data()

        pd.testing.assert_frame_equal(result, baostock_df)
        self.assertEqual(call_sequence, ["akshare", "finshare", "tushare", "baostock"])


class GetSpotFinshareTests(unittest.TestCase):
    def test_normalizes_finshare_snapshots_for_etf(self):
        manager = SimpleNamespace(
            get_batch_snapshots=lambda codes: {
                "510300.SH": SimpleNamespace(last_price=4.321, volume=4567.0, code="510300.SH")
            }
        )

        with patch.object(mod, "_FINSHARE_AVAILABLE", True, create=True), patch.object(
            mod, "get_data_manager", return_value=manager, create=True
        ), patch.object(
            mod,
            "_get_finshare_candidates",
            return_value=[("510300", "沪深300ETF"), ("163402", "兴全趋势LOF")],
            create=True,
        ):
            result = mod._get_spot_finshare("ETF")

        expected = pd.DataFrame(
            {
                "代码": ["510300"],
                "名称": ["沪深300ETF"],
                "最新价": [4.321],
                "成交量": [4567.0],
                "基金类型": ["ETF"],
            }
        )
        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


if __name__ == "__main__":
    unittest.main()
