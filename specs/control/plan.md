# Implementation Plan: Dataset Control and Reporting

**Branch**: `control` | **Date**: 2025-09-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/control/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → Feature spec loaded successfully
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → No NEEDS CLARIFICATION found in spec
   → Set Structure Decision based on project type: single project
3. Fill the Constitution Check section based on the content of the constitution document.
   → Using generic template (no specific constitution defined)
4. Evaluate Constitution Check section below
   → No violations found - proceeding with simple approach
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → Researching polyline decoding, Hausdorff distance, and shapefile handling
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
7. Re-evaluate Constitution Check section
   → No new violations
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Validate Google Maps polyline data against reference shapefiles by computing geometric similarity metrics (Hausdorff distance, length ratio, coverage) and generate quality reports per link with validation statistics.

## Technical Context
**Language/Version**: Python 3.11 (established codebase)
**Primary Dependencies**: pandas, geopandas, shapely, pyproj, polyline (for decoding)
**Storage**: CSV files, Shapefiles (GIS format)
**Testing**: pytest (existing test framework)
**Target Platform**: Windows/Linux desktop (Streamlit web app)
**Project Type**: single - extension to existing codebase
**Performance Goals**: Process millions of rows efficiently using chunked reading
**Constraints**: Memory efficient for large datasets, maintain UI responsiveness
**Scale/Scope**: Millions of observations, thousands of links

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Since no specific constitution is defined, using general best practices:
- [x] Simple architecture: Two backend modules + UI page
- [x] Clear separation of concerns: validation logic vs reporting logic
- [x] Reuses existing code: CRS handling, shapefile loading, join logic
- [x] Test-friendly design: Pure functions for validation logic
- [x] Observable: Valid codes provide clear debugging info

## Project Structure

### Documentation (this feature)
```
specs/control/
├── plan.md              # This file (/plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Adding to existing structure
E:\google_agg\
├── control_validator.py    # New: Row-level validation logic
├── control_report.py        # New: Link-level reporting logic
├── app.py                   # Modified: Add control page
├── spatial_data.py          # Reuse: Shapefile loading, CRS
├── map_data.py              # Reuse: Join logic
└── tests/
    ├── test_control_validator.py  # New: Unit tests
    └── test_control_report.py     # New: Unit tests
```

**Structure Decision**: Single project extension (adding to existing codebase)

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - Polyline decoding library and precision handling
   - Hausdorff distance efficient computation for large datasets
   - Coverage calculation with densified geometries
   - Shapefile writing with added fields

2. **Generate and dispatch research agents**:
   ```
   Task: "Research polyline decoding library for Google Maps encoded polylines"
   Task: "Find efficient Hausdorff distance implementation in shapely"
   Task: "Research geometry densification and coverage calculation methods"
   Task: "Best practices for shapefile field addition in geopandas"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all technical decisions resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - ValidationRow: Single observation with validation result
   - LinkReport: Aggregated statistics per shapefile link
   - ValidationParameters: Configuration for thresholds
   - ValidCode: Enumeration of validation codes

2. **Generate API contracts** from functional requirements:
   - validate_row(row, shapefile, params) → (is_valid, valid_code)
   - generate_link_report(validated_data, shapefile, period) → report_gdf
   - Internal contracts for geometry operations

3. **Generate contract tests** from contracts:
   - Test each valid_code scenario (90-93, 20-24, 0-4)
   - Test report generation for each result_code
   - Test parameter variations

4. **Extract test scenarios** from user stories:
   - Default validation scenario
   - RouteAlternative handling
   - Report generation with filters
   - Parameter sensitivity testing

5. **Update CLAUDE.md incrementally**:
   - Add control validation module documentation
   - Document valid_code system
   - Add usage examples

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, CLAUDE.md update

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Create validation function tests [P]
- Create report generation tests [P]
- Implement polyline decoding
- Implement Hausdorff distance calculation
- Implement length and coverage checks
- Implement valid_code logic hierarchy
- Implement link aggregation logic
- Create UI page in app.py
- Integration testing

**Ordering Strategy**:
- Tests first (TDD approach)
- Core geometry functions before validation logic
- Validation before reporting
- Backend before UI

**Estimated Output**: 20-25 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following TDD)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No violations - design follows simple, testable architecture.

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)

---
*Based on generic best practices - No specific constitution defined*