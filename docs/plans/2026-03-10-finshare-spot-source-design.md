# Finshare Spot Source Design

**Date:** 2026-03-10

**Goal:** Add `finshare` as a new optional spot-market data source for ETF/LOF quotes, and reorder the fallback chain to `akshare -> finshare -> tushare -> baostock`.

## Current Context

The project computes ETF/LOF premium rates by combining:

- spot-market price from `get_etf_realtime_data()` / `get_lof_realtime_data()`
- off-market NAV from existing akshare-based NAV functions

Today, spot data falls back in this order:

1. Tushare
2. akshare
3. Baostock

The spot layer already accepts any DataFrame that can be normalized into these columns:

- `代码`
- `名称`
- `最新价`
- `成交量`
- optional `基金类型`

That makes `finshare` a good fit as a thin adapter instead of a wider refactor.

## Chosen Approach

Use a thin `finshare` adapter in the existing spot-data layer.

### Why this approach

- Small change surface: only the spot fetch path changes.
- Keeps current NAV logic untouched.
- Respects the existing fallback design and retry behavior.
- Avoids a broad provider abstraction refactor that is not needed for this request.

## Target Data Flow

### ETF flow

1. Try `ak.fund_etf_spot_em()`.
2. If akshare fails or returns a non-spot-shaped DataFrame, try `finshare`.
3. If `finshare` fails or returns no valid rows, try `Tushare`.
4. If `Tushare` fails, try `Baostock`.

### LOF flow

1. Try `ak.fund_lof_spot_em()`.
2. If akshare fails or returns a non-spot-shaped DataFrame, try `finshare`.
3. If `finshare` fails or returns no valid rows, try `Tushare`.
4. If `Tushare` fails, try `Baostock`.

## Finshare Adapter Design

Add a new internal helper:

- `_get_spot_finshare(fund_type='ETF')`

Responsibilities:

1. Check whether `finshare` is installed.
2. Build a `code -> name` mapping from the `finshare` fund list API.
3. Filter the fund list into ETF or LOF candidates.
4. Batch-fetch snapshots through `finshare` data manager.
5. Normalize results into the existing DataFrame contract.

### Expected normalized output

The helper returns a DataFrame with:

- `代码`: 6-digit fund code
- `名称`: fund name from the fund list
- `最新价`: snapshot `last_price`
- `成交量`: snapshot `volume`
- `基金类型`: `ETF` or `LOF`

If no valid rows are produced, it returns `None`.

## Finshare Fund Filtering

`finshare` snapshot models do not include the display name, so the adapter must keep the name from the fund list.

Filtering rules should stay pragmatic:

- ETF:
  - prefer name contains `ETF`
  - allow common ETF code ranges already present in market data
- LOF:
  - prefer name contains `LOF`
  - also allow Shenzhen-style `16` prefix as a fallback, matching current Baostock heuristics

The filter should be defensive because `finshare` fund-list schema may vary by upstream response.

## Error Handling

The adapter must never break the existing chain.

Failure cases that should degrade to the next source:

- `finshare` package not installed
- manager initialization failure
- fund list API failure
- fund list schema mismatch
- snapshot batch call failure
- snapshot objects missing usable `last_price`
- all rows filtered out during normalization

In all of these cases, `_get_spot_finshare()` returns `None` after logging a short error.

## Dependency Strategy

`finshare` should be an installable dependency in `requirements.txt`.

Runtime behavior remains optional:

- if installed, it participates in the fallback chain
- if missing, code logs and skips it

No new configuration keys are required for this change.

## Testing Strategy

Use TDD around the fallback chain rather than testing `finshare` internals.

Required regression coverage:

1. ETF path falls back from malformed akshare result to valid `finshare` result.
2. ETF path falls back from failed `finshare` to valid `Tushare` result.
3. LOF path falls back from failed `finshare` to valid `Baostock` result when `Tushare` also fails.

Tests should mock:

- akshare response
- `_get_spot_finshare`
- `_get_spot_tushare`
- `_get_spot_baostock`

This keeps the tests deterministic and focused on project behavior.

## Files Affected

- `src/etf_premium_rate.py`
- `tests/test_etf_premium_rate.py`
- `requirements.txt`
- `README.md`
- `config.example.yaml`

## Non-Goals

- Rewriting the whole source system into a provider framework
- Changing NAV source logic
- Adding new runtime config for source ordering
- Depending on `finshare` for report rendering or premium-rate calculation
