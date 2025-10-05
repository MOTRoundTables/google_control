# Control Validation Performance Improvement Plan

This note captures the immediate ideas for reducing the time spent in the "Running batch validation with route alternative grouping" phase when working with large datasets such as `test_data/control/data.csv` (~714k rows).

## 1. Parallelise `validate_dataframe_batch`
- **Idea**: Partition the input DataFrame by `link_id` (or `Name`) and process chunks in parallel using `concurrent.futures.ProcessPoolExecutor`.
- **Why**: Each link is independent after shapefile lookup creation, so CPU cores can work in parallel without synchronisation beyond reading the shapefile lookup.
- **Key tasks**:
  - Extract a lightweight payload for each chunk (avoid copying columns that arent required by `_validate_single_row_core`).
  - Share the precomputed shapefile lookup via an initialiser or use `multiprocessing.shared_memory` if necessary.
  - Concatenate results and re-run downstream tests to ensure deterministic ordering.
- **Risks**: Higher RAM usage; need to guard against GDAL/shapely objects that cannot be pickled (ensure we serialise plain data going into worker processes).

## 2. Optimise per-row geometry work
- **Idea**: Cache polyline decodes and Hausdorff-ready geometries.
- **Why**: Many rows share the same `Polyline` or route alternative across timestamps.
- **Key tasks**:
  - Introduce an `lru_cache` (or explicit dict) keyed by `Polyline` string for the decoded coordinates.
  - Cache transformed shapefile geometries in `EPSG:2039` so the metric conversion is only done once per link.
  - Measure impact with representative slices (e.g., first 100k rows) to confirm reduced per-row latency.

## 3. Chunked validation pipeline (single process)
- **Idea**: Process the CSV in streaming chunks (e.g., 50k rows) while writing intermediate results to Parquet/Feather before concatenating.
- **Why**: Keeps memory steady and allows us to surface progress earlier; also positions us to parallelise chunk processing later.
- **Key tasks**:
  - Refactor `validate_dataframe_batch` to accept an iterator of DataFrame chunks.
  - Ensure consistent ordering when concatenating chunk outputs so downstream sorting remains stable.

## 4. Progress telemetry & tooling
- **Idea**: Instrument validation with periodic `st.info`/logging updates (rows per minute, estimated time remaining).
- **Why**: Even if runtime stays similar, giving users visibility that work is progressing helps distinguish "stuck" vs "working" states.
- **Key tasks**:
  - Emit progress updates every N rows within the loop.
  - Optionally surface a CLI utility (`python utils/perf/benchmark_control_validation.py`) for profiling datasets before running the full Streamlit flow.

## 5. Long-term: Vectorised distance calculations
- **Idea**: Replace per-row Hausdorff calculations with vectorised operations using `pygeos`/`shapely` newer APIs or approximate metrics where acceptable.
- **Why**: Hausdorff is mathematically expensive; approximate thresholds or pre-filtering by bounding boxes could remove obvious passes/fails faster.
- **Key tasks**:
  - Investigate shapely 2.x vectorised operations (requires confirming compatibility with the rest of the stack).
  - Prototype a fast-path that short-circuits calculations for identical polylines (exact matches) before calling Hausdorff.

---

**Suggested next step**: start with option 1 (parallelisation), as it keeps logic intact while unlocking multi-core machines. Combine with option 2 for additional per-core speedups.
## Additional Optimisations (from field notes)

- **Hausdorff fail-fast guard**: Before the expensive Hausdorff calculation, compare metric envelopes and return early when they are well separated; otherwise simplify both geometries (e.g., 0.5 m tolerance) before final distance, only falling back to the exact calculation when the simplified distance sits near the decision threshold. This keeps correctness while trimming per-row cost.
- **Efficient best-alternative selection**: When generating `best_valid_observations.csv`, use `groupby(...).idxmin()` to grab the lowest Hausdorff distance per `(link_id, Timestamp)` instead of manual loops.
- **Categorical keys for large joins**: Cast `link_id`/`Name` to `category` once prior to heavy groupby/sort steps so pandas can process large link sets more efficiently.
