# Feature Specification: Dataset Control and Reporting

**Feature Branch**: `control`
**Created**: 2025-09-21
**Status**: Draft
**Input**: User description: "Specification for dataset control and reporting"

## Execution Flow (main)
```
1. Parse user description from Input
   → Extract validation requirements for Google Maps polyline data
2. Load dataset CSV and reference shapefile
   → Parse link identifiers from Name field (s_from-to format)
   → Decode polyline geometry from Polyline field
3. For each row:
   → Check data availability (required fields)
   → Join to shapefile by from_id and to_id
   → Decode polyline and validate geometry, then evaluate RouteAlternative, then run geometry tests in this exact order Hausdorff, length, coverage
   → Assign is_valid and valid_code
4. Generate per-link report:
   → Calculate share of valid observations per link
   → Assign result_code and result_label
   → Write output shapefile with results
5. Return: SUCCESS (validation and reporting complete)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a traffic monitoring analyst, I need to validate that Google Maps route data matches our reference road network shapefile, so I can ensure data quality and identify discrepancies between observed routes and expected network geometry.

### Acceptance Scenarios
1. **Given** a dataset CSV with encoded polylines and a reference shapefile, **When** I run validation with default parameters, **Then** each row is marked with is_valid (True/False) and a specific valid_code explaining the validation result
2. **Given** RouteAlternative values greater than 1, **When** at least one alternative matches the reference geometry, **Then** the observation is marked as valid
3. **Given** a validated dataset, **When** I generate the per-link report, **Then** I receive a shapefile with result_code, result_label, and percentage of valid observations per link
4. **Given** geometry comparison parameters (Hausdorff threshold, length tolerance), **When** I adjust these values, **Then** the validation sensitivity changes accordingly
5. **Given** a link with no observations in the dataset, **When** generating the report, **Then** the link is marked with result_code 41 (did not record)

### Edge Cases
- What happens when polyline decode fails? → is_valid=False, valid_code=93
- How does system handle reversed direction polylines? → Hausdorff distance remains valid (direction-agnostic)
- What happens with very short links (<20m)? → min_link_length_m parameter stabilizes length ratios
- How are duplicate polylines per timestamp handled? → Deduplicated before calculating percentages in report
- What if shapefile CRS differs from metric CRS? → Automatic reprojection to EPSG 2039 before calculations

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST validate each CSV row against reference shapefile geometry
- **FR-002**: System MUST parse link identifiers from Name field using format "s_{from_id}-{to_id}"
- **FR-003**: System MUST decode encoded polylines from the Polyline field
- **FR-004**: System MUST calculate Hausdorff distance between decoded polyline and reference geometry
- **FR-005**: System MUST evaluate length similarity between polyline and reference based on configurable mode (off/ratio/exact)
- **FR-006**: System MUST handle multiple RouteAlternative values, validating if any alternative matches
- **FR-007**: System MUST assign is_valid (True/False) and valid_code (integer) to each row
- **FR-008**: System MUST generate per-link report with share of valid observations
- **FR-009**: System MUST write output shapefile with result_code, result_label, and num fields
- **FR-010**: System MUST reproject both datasets to metric CRS (default EPSG 2039) before distance/length calculations
- **FR-011**: System MUST allow configuration of validation thresholds (hausdorff_threshold_m, coverage_min, etc.)
- **FR-012**: System MUST provide UI controls for all validation parameters
- **FR-013**: System MUST handle missing data gracefully (missing fields, unparseable names, decode failures)
- **FR-014**: System MUST support running validation on the entire dataset or filtered by day or by date range
- **FR-016**: System MUST allow loading any reference shapefile and must reuse the current map matching logic for CRS handling and feature join
- **FR-017**: System MUST treat Name parsing as canonical s_from_to while also accepting a dash separator and mixed case, and must fail with valid_code 91 if parsing fails
- **FR-015**: System MUST provide download links for validated CSV and output shapefile

### Key Entities *(include if feature involves data)*
- **Observation Row**: Single GPS observation with encoded polyline, link identifier, timestamp, and RouteAlternative
- **Reference Link**: Shapefile feature with From/To node IDs and LineString geometry
- **Validation Result**: Per-row result with is_valid boolean and valid_code integer
- **Link Report**: Aggregated validation statistics per reference link with result_code and percentage

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---

## Additional Context

### UI Notes
- Expose all parameters above on the control page and persist the last used values per user session

### File Placement
This feature adds a new page in app.py. All calculations are implemented in two files: control_validator.py for is_valid and valid_code, and control_report.py for the per link report and shapefile write back.

### Valid Code Definitions
The system uses a hierarchical validation code system. When multiple failure reasons exist for a row, return the first hit by the evaluation order: Data availability, Join, Decode, RouteAlternative, Hausdorff, Length, Coverage.

#### Data Availability Codes (90-93)
- 90: Required fields missing
- 91: Cannot parse from_id/to_id from Name field
- 92: Link not found in reference shapefile
- 93: Polyline decode failed or empty geometry

#### Route Alternative Codes (20-24)
- 20: Zero alternatives, geometry comparison fails
- 21: One alternative, matches reference
- 22: One alternative, does not match reference
- 23: Multiple alternatives, at least one matches
- 24: Multiple alternatives, none match

#### Geometry Match Codes (0-4)
- 0: Exact match (Hausdorff=0, length check passes)
- 1: Within tolerance (Hausdorff≤threshold, length check passes)
- 2: Distance failure (Hausdorff>threshold)
- 3: Length failure (based on configured mode)
- 4: Coverage failure (overlap<coverage_min)

Coverage is computed along the reference link as overlapped length divided by reference length after both geometries are densified to the same vertex spacing. A row is True if any alternative satisfies Hausdorff less than or equal to threshold and the configured length check and coverage greater than or equal to coverage_min.

### Report Result Codes
- 0: All observations valid (100%)
- 1: Single alternative route, some invalid (num equals percent of valid observations for that link over the chosen period after deduplication by link id plus timestamp plus polyline)
- 2: Single alternative route, all invalid (0%)
- 30: Multiple alternatives, all valid (100%)
- 31: Multiple alternatives, mixed validity (num equals percent of valid observations for that link over the chosen period after deduplication by link id plus timestamp plus polyline)
- 32: Multiple alternatives, all invalid (0%)
- 41: Link not recorded in dataset (do not emit any row level records for that link in the period, and write num as null on the shapefile copy)
- 42: Link partially recorded

### Configurable Parameters
- hausdorff_threshold_m: default 5
- length_check_mode: values off, ratio, exact
- length_ratio_min: default 0.90
- length_ratio_max: default 1.10
- epsilon_length_m: default 0.5 applies only when mode is exact to allow near 100 percent length match
- coverage_min: default 0.85 fraction of reference link length overlapped by the best alternative
- coverage_spacing_m: default 1.0 densification spacing for coverage calculation affects precision vs performance
- min_link_length_m: default 20 used to suppress noisy ratios on very short links
- crs_metric: default EPSG 2039 both datasets are reprojected before any metric calculation
- polyline_precision: default 5