# Control Validator Hebrew Encoding Fix

## Summary
- Validated control CSVs were exporting Greek characters (e.g., `??? ?`) in the `DayInWeek` field instead of Hebrew (e.g., `éåí â`).
- `chardet` detected `ISO-8859-7` (Greek) for Hebrew source files and the pipeline trusted that result, so downstream processing worked with the wrong encoding.
- Added a Hebrew-aware override that reclassifies Greek detections as `cp1255` when the byte sample clearly contains Hebrew code points, and wired the control validator UI to surface the override.

## Root Cause
- Control CSVs are encoded in Windows Hebrew (`cp1255`).
- The byte patterns for Hebrew letters overlap with Greek in single-byte encodings; `chardet` often returns `ISO-8859-7` with high confidence.
- When the validator loaded the file using the misdetected encoding, Pandas produced Greek text, which was then written verbatim to `validated_data.csv`.

## Fix Details
- Introduced `resolve_hebrew_encoding` in `components/processing/pipeline.py` to post-process `chardet` results. The helper decodes the sample as both the detected encoding and `cp1255`, counts Unicode characters in the Hebrew block (`0x0590-0x05FF`) versus the Greek block, and overrides to `cp1255` when Hebrew dominates.
- Updated `detect_file_encoding` to use the helper and log when an override occurs.
- Updated `app.run_control_validation` to reuse the helper so the Streamlit workflow reports the corrected encoding and avoids corrupt output.

## Validation
1. `pytest test_encoding_detection.py::test_control_file_detects_cp1255 -q`
2. Manually load `test_data/control/original_…csv` through the validator and confirm `validated_data.csv` now retains Hebrew in `DayInWeek`.

## Follow-up
- Consider applying the same override in any other ingestion paths that accept external CSV uploads.
- If additional locales are introduced, extend the helper with language-specific heuristics instead of relying solely on `cp1255` fallback.
