# Finshare Spot Source Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `finshare` as an optional ETF/LOF spot quote source and reorder the fallback chain to `akshare -> finshare -> tushare -> baostock`.

**Architecture:** Keep the current procedural structure in `src/etf_premium_rate.py` and insert a thin `finshare` adapter that normalizes fund snapshots into the same DataFrame shape already consumed by the premium-rate pipeline. Do not refactor NAV fetching or downstream report logic.

**Tech Stack:** Python, pandas, akshare, tushare, baostock, finshare, unittest.mock

---

### Task 1: Add regression tests for the new fallback order

**Files:**
- Modify: `tests/test_etf_premium_rate.py`
- Modify: `src/etf_premium_rate.py`

**Step 1: Write the failing test**

```python
def test_falls_back_to_finshare_when_akshare_returns_non_spot_shape(self):
    malformed_df = pd.DataFrame({"date": ["2026-03-10"], "close": [1.0]})
    finshare_df = pd.DataFrame(
        {
            "代码": ["510300"],
            "名称": ["沪深300ETF"],
            "最新价": [1.001],
            "成交量": [12345.0],
            "基金类型": ["ETF"],
        }
    )

    with patch.object(mod, "_get_spot_finshare", return_value=finshare_df):
        ...
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_etf_premium_rate.GetEtfRealtimeDataTests.test_falls_back_to_finshare_when_akshare_returns_non_spot_shape -v`

Expected: FAIL because `_get_spot_finshare` does not exist or is never called.

**Step 3: Write minimal implementation**

Create `_get_spot_finshare()` and insert it into the ETF fallback chain after akshare and before Tushare.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_etf_premium_rate.GetEtfRealtimeDataTests.test_falls_back_to_finshare_when_akshare_returns_non_spot_shape -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_etf_premium_rate.py src/etf_premium_rate.py
git commit -m "test: cover finshare fallback after akshare"
```

### Task 2: Add regression tests for fallback past finshare

**Files:**
- Modify: `tests/test_etf_premium_rate.py`

**Step 1: Write the failing test**

```python
def test_falls_back_to_tushare_when_finshare_returns_none(self):
    tushare_df = pd.DataFrame(
        {
            "代码": ["510050"],
            "名称": ["上证50ETF"],
            "最新价": [1.235],
            "成交量": [2000.0],
            "基金类型": ["ETF"],
        }
    )

    with patch.object(mod, "_get_spot_finshare", return_value=None):
        ...
```

Add a second LOF test that verifies `akshare -> finshare -> tushare` all fail and the code falls back to `_get_spot_baostock`.

**Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_etf_premium_rate -v`

Expected: FAIL because the fallback order still uses the old chain.

**Step 3: Write minimal implementation**

Update both `get_etf_realtime_data()` and `get_lof_realtime_data()` to use the new order.

**Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_etf_premium_rate -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_etf_premium_rate.py src/etf_premium_rate.py
git commit -m "test: cover fallback past finshare"
```

### Task 3: Add the finshare optional import and adapter

**Files:**
- Modify: `src/etf_premium_rate.py`

**Step 1: Write the failing test**

Use the Task 1 and Task 2 tests as the active failing proof. Do not add a network-dependent test for real `finshare`.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_etf_premium_rate -v`

Expected: FAIL until `_get_spot_finshare()` exists and returns normalized output.

**Step 3: Write minimal implementation**

Add:

- optional `finshare` import guard
- helper to extract candidate code/name fields from `finshare` fund list rows
- helper to classify ETF vs LOF rows
- `_get_spot_finshare(fund_type='ETF')`

Implementation notes:

- use `get_data_manager()` for snapshots
- use `FundDataSource().get_fund_list()` for fund metadata
- batch codes to avoid oversized single requests
- normalize snapshot rows into a DataFrame with `代码 / 名称 / 最新价 / 成交量 / 基金类型`
- skip rows missing `last_price` or fund name

Example normalization skeleton:

```python
rows.append(
    {
        "代码": code,
        "名称": name,
        "最新价": float(snapshot.last_price),
        "成交量": float(getattr(snapshot, "volume", 0) or 0),
        "基金类型": fund_type,
    }
)
```

**Step 4: Run tests to verify it passes**

Run: `python3 -m unittest tests.test_etf_premium_rate -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/etf_premium_rate.py tests/test_etf_premium_rate.py
git commit -m "feat: add finshare spot data adapter"
```

### Task 4: Update dependency and documentation

**Files:**
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `config.example.yaml`

**Step 1: Write the failing test**

No automated test is needed here. Use documentation review as the verification target.

**Step 2: Run verification to show current docs are stale**

Run: `rg -n "Tushare|akshare|Baostock|数据源优先级" README.md config.example.yaml src/etf_premium_rate.py`

Expected: output still shows the old order and lacks `finshare`.

**Step 3: Write minimal implementation**

Update:

- `requirements.txt` to include `finshare`
- module docstring in `src/etf_premium_rate.py`
- README data-source section and setup instructions
- config comments to mention the new order and that `finshare` is optional

**Step 4: Run verification to confirm docs are current**

Run: `rg -n "finshare|akshare -> finshare|akshare > finshare|Baostock" README.md config.example.yaml src/etf_premium_rate.py requirements.txt`

Expected: output shows `finshare` and the new source order everywhere relevant.

**Step 5: Commit**

```bash
git add requirements.txt README.md config.example.yaml src/etf_premium_rate.py
git commit -m "docs: document finshare source order"
```

### Task 5: Run full verification

**Files:**
- Modify: none
- Test: `tests/test_etf_premium_rate.py`

**Step 1: Run the focused automated tests**

Run: `python3 -m unittest tests.test_etf_premium_rate -v`

Expected: PASS

**Step 2: Run a syntax check**

Run: `python3 -m py_compile src/etf_premium_rate.py tests/test_etf_premium_rate.py`

Expected: PASS with no output.

**Step 3: Review the diff**

Run: `git diff -- src/etf_premium_rate.py tests/test_etf_premium_rate.py requirements.txt README.md config.example.yaml`

Expected: diff only shows the intended finshare source additions and source-order doc updates.

**Step 4: Commit**

```bash
git add src/etf_premium_rate.py tests/test_etf_premium_rate.py requirements.txt README.md config.example.yaml
git commit -m "feat: add finshare ETF and LOF fallback source"
```
