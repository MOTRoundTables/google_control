# Tasks: Dataset Control and Reporting

**Input**: Design documents from `/specs/control/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Tech stack: Python 3.11, pandas, geopandas, shapely, polyline
   → Structure: Single project extension to existing codebase
2. Load optional design documents:
   → data-model.md: ValidationParameters, ValidationRow, ValidCode, LinkReport, ResultCode
   → contracts/: validation_api.yaml, internal_functions.md
   → research.md: polyline library, Hausdorff implementation
3. Generate tasks by category:
   → Setup: Install polyline dependency
   → Tests: Validation functions, report generation, UI integration
   → Core: control_validator.py, control_report.py implementations
   → Integration: Streamlit UI page
   → Polish: Performance tests, documentation
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- Single project structure at repository root
- New files: `control_validator.py`, `control_report.py`
- Test files: `tests/test_control_validator.py`, `tests/test_control_report.py`
- Modified file: `app.py` (add control page)

## Phase 3.1: Setup
- [x] T001 Install polyline package dependency: `pip install polyline`
- [x] T002 Create test data directory if not exists: `E:\google_agg\test_data\control\`
- [x] T003 [P] Create empty module files: `control_validator.py` and `control_report.py`

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Validation Function Tests
- [x] T004 [P] Test parse_link_name function in `tests/test_control_validator.py` - test s_from-to, s_from_to, mixed case
- [x] T005 [P] Test decode_polyline function in `tests/test_control_validator.py` - test valid/invalid polylines
- [x] T006 [P] Test calculate_hausdorff function in `tests/test_control_validator.py` - test distance calculations
- [x] T007 [P] Test check_length_similarity function in `tests/test_control_validator.py` - test ratio/exact modes
- [x] T008 [P] Test calculate_coverage function in `tests/test_control_validator.py` - test overlap calculation
- [x] T009 Test validate_row with valid_code 90 (missing fields) in `tests/test_control_validator.py`
- [x] T010 Test validate_row with valid_code 91 (name parse failure) in `tests/test_control_validator.py`
- [x] T011 Test validate_row with valid_code 92 (link not in shapefile) in `tests/test_control_validator.py`
- [x] T012 Test validate_row with valid_code 93 (polyline decode failure) in `tests/test_control_validator.py`
- [x] T013 Test validate_row with codes 20-24 (RouteAlternative scenarios) in `tests/test_control_validator.py`
- [x] T014 Test validate_row with codes 0-4 (geometry match scenarios) in `tests/test_control_validator.py`

### Report Generation Tests
- [x] T015 [P] Test deduplicate_observations function in `tests/test_control_report.py`
- [x] T016 [P] Test aggregate_link_statistics function in `tests/test_control_report.py`
- [x] T017 [P] Test determine_result_code function in `tests/test_control_report.py` - all result codes 0,1,2,30,31,32,41,42
- [x] T018 [P] Test generate_link_report function in `tests/test_control_report.py` - full pipeline
- [x] T019 [P] Test write_shapefile_with_results function in `tests/test_control_report.py`

### Integration Tests
- [x] T020 [P] Integration test: Process sample CSV with default parameters in `tests/test_integration_control.py`
- [x] T021 [P] Integration test: Date filtering in `tests/test_integration_control.py`
- [x] T022 [P] Integration test: Parameter sensitivity in `tests/test_integration_control.py`

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models
- [x] T023 [P] Implement ValidationParameters dataclass in `control_validator.py`
- [x] T024 [P] Implement ValidCode enum in `control_validator.py`
- [x] T025 [P] Implement ResultCode enum in `control_report.py`

### Validation Functions
- [x] T026 Implement parse_link_name function in `control_validator.py`
- [x] T027 Implement decode_polyline function in `control_validator.py` using polyline library
- [x] T028 Implement calculate_hausdorff function in `control_validator.py` using shapely
- [x] T029 Implement check_length_similarity function in `control_validator.py`
- [x] T030 Implement calculate_coverage function in `control_validator.py` with densification
- [x] T031 Implement validate_row main function in `control_validator.py` with hierarchical logic

### Report Functions
- [x] T032 [P] Implement deduplicate_observations function in `control_report.py`
- [x] T033 [P] Implement aggregate_link_statistics function in `control_report.py`
- [x] T034 [P] Implement determine_result_code function in `control_report.py`
- [x] T035 Implement generate_link_report main function in `control_report.py`
- [x] T036 Implement write_shapefile_with_results function in `control_report.py`

## Phase 3.4: Integration

### Streamlit UI Integration
- [x] T037 Add "Dataset Control" page to app.py navigation
- [x] T038 Implement render_control_page function in app.py with file uploaders
- [x] T039 Add parameter controls (sliders, selectboxes) for all validation parameters
- [x] T040 Implement process_validation function to handle CSV processing
- [x] T041 Add session state management for parameter persistence
- [x] T042 Add download buttons for validated CSV and report shapefile

### Data Pipeline Integration
- [x] T043 Integrate with existing spatial_data.py for shapefile loading and CRS handling
- [x] T044 Integrate with existing map_data.py for join logic reuse
- [x] T045 Add chunked processing support for large CSV files

## Phase 3.5: Polish

### Performance & Optimization
- [ ] T046 [P] Add spatial indexing for shapefile joins
- [ ] T047 [P] Implement polyline caching to avoid re-decoding
- [x] T048 [P] Add progress bars for long-running operations
- [ ] T049 Performance test with 1M+ rows dataset

### Documentation & Validation
- [x] T050 [P] Update CLAUDE.md with complete valid_code reference
- [x] T051 [P] Add docstrings to all public functions
- [x] T052 Run quickstart.md scenarios to validate implementation
- [x] T053 Test with actual control dataset: `E:\google_agg\test_data\control\data_test_control.csv`

## Dependencies
- Setup (T001-T003) before all tests
- Tests (T004-T022) before implementation (T023-T036)
- Data models (T023-T025) before validation functions (T026-T031)
- Core implementation before UI integration (T037-T045)
- Everything before polish (T046-T053)

## Parallel Example
```
# Launch validation function tests together:
Task: "Test parse_link_name function in tests/test_control_validator.py"
Task: "Test decode_polyline function in tests/test_control_validator.py"
Task: "Test calculate_hausdorff function in tests/test_control_validator.py"
Task: "Test check_length_similarity function in tests/test_control_validator.py"
Task: "Test calculate_coverage function in tests/test_control_validator.py"

# Launch report tests together:
Task: "Test deduplicate_observations in tests/test_control_report.py"
Task: "Test aggregate_link_statistics in tests/test_control_report.py"
Task: "Test determine_result_code in tests/test_control_report.py"
```

## Notes
- [P] tasks = different files, no shared dependencies
- Verify all tests fail before implementing
- Commit after each task group
- Use existing codebase patterns for consistency
- Test with real shapefiles from `test_data/google_results_to_golan_17_8_25/`

## Validation Checklist
*GATE: All items must pass*

- [x] All contracts have corresponding tests (T004-T019 cover internal_functions.md)
- [x] All entities have implementation tasks (ValidationParameters, ValidCode, ResultCode)
- [x] All tests come before implementation (Phase 3.2 before 3.3)
- [x] Parallel tasks truly independent (marked [P] only for different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task in same phase