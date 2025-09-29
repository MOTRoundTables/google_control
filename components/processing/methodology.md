
## 1) Overview

The Hour Aggregation system processes Google Maps link monitoring data from CSV files to produce:
- **Hourly aggregations** with traffic metrics by link, date, and hour
- **Weekly profiles** showing typical patterns by day type and hour
- **Quality metrics** for data completeness and reliability assessment

The pipeline handles millions of rows efficiently through chunked processing, timezone-aware temporal analysis, and configurable validation rules.

---

## 2) Input data requirements

### Required CSV columns
| Column | Description | Example |
| --- | --- | --- |
| **DataID** | Unique record identifier | 123456 |
| **Name** | Link identifier (becomes link_id) | s_653-655 |
| **Timestamp** | Observation timestamp | 2024-08-17 14:30:00 |
| **Duration** | Travel time in seconds | 180 |
| **Distance** | Link distance in meters | 2500 |
| **Speed** | Average speed in km/h | 50 |
| **DayInWeek** | Hebrew day name | ראשון |
| **DayType** | Day classification | חול |

### Optional columns
- **SegmentID**, **RouteAlternative** — Routing metadata
- **Url**, **Polyline** — Google Maps metadata
- **is_valid** — Pre-validated data flag

### Data formats
- **Encoding**: UTF-8, CP1255 (Hebrew), auto-detected
- **Timestamps**: Multiple formats supported with fallback parsing
- **Timezone**: Configurable, default Asia/Jerusalem

---

## 3) Processing pipeline stages

### Stage 1: Data ingestion & validation
1. **Encoding detection**: Resolve Hebrew encoding (CP1255 vs ISO-8859-7)
2. **Column standardization**: Map variations to canonical names
3. **Type validation**: Ensure numeric fields contain valid numbers
4. **Duplicate removal**: Remove by DataID and link+timestamp

### Stage 2: Temporal enhancement
1. **Timestamp parsing**: Convert to timezone-aware datetime
2. **Feature extraction**: date, hour, weekday, week number
3. **Holiday detection**: Israeli holidays via Hebrew calendar
4. **DST handling**: Proper daylight saving transitions

### Stage 3: Data filtering
1. **Date range**: Start/end date boundaries
2. **Time selection**: Specific weekdays (0-6) and hours (0-23)
3. **Link filtering**: Include/exclude specific links
4. **Validity**: Use is_valid column when present

### Stage 4: Aggregation computation
1. **Hourly grouping**: By link_id, date, hour, daytype
2. **Weekly profiling**: By link_id, daytype, hour across all dates
3. **Metrics calculation**: See sections 4 & 5 for details

### Stage 5: Quality assessment
1. **Completeness metrics**: Coverage by link and time
2. **Statistical indicators**: Standard deviations, outliers
3. **Data flags**: Suspicious values, missing periods

---

## 4) Hourly aggregation logic

### Grouping dimensions
- **link_id**: Unique link identifier (e.g., s_653-655)
- **date**: Calendar date (YYYY-MM-DD)
- **hour_of_day**: Hour 0-23
- **daytype**: Day classification (חול/שבת/חג)

### Computed metrics
| Field | Calculation | Description |
| --- | --- | --- |
| **n_total** | COUNT(*) | Total observations in hour |
| **n_valid** | COUNT(is_valid=True) | Valid observations (when is_valid exists) |
| **avg_duration_sec** | AVG(Duration) | Mean travel time |
| **std_duration_sec** | STDEV(Duration) | Duration variability |
| **min_duration_sec** | MIN(Duration) | Fastest observation |
| **max_duration_sec** | MAX(Duration) | Slowest observation |
| **avg_distance_m** | AVG(Distance) | Mean distance |
| **avg_speed_kmh** | AVG(Speed) | Mean speed |
| **data_quality_flag** | Computed | Quality indicator (0=good, 1=warning) |

### Aggregation formula example
```sql
SELECT link_id, date, hour_of_day, daytype,
       COUNT(*) as n_total,
       AVG(Duration) as avg_duration_sec,
       STDEV(Duration) as std_duration_sec
FROM processed_data
GROUP BY link_id, date, hour_of_day, daytype
```

---

## 5) Weekly profile generation

### Grouping dimensions
- **link_id**: Unique link identifier
- **daytype**: Day classification (חול/weekday, שבת/weekend, חג/holiday)
- **hour_of_day**: Hour 0-23

### Computed metrics (averaged across all dates)
| Field | Calculation | Description |
| --- | --- | --- |
| **avg_n_total** | AVG(hourly.n_total) | Average observations per hour |
| **avg_n_valid** | AVG(hourly.n_valid) | Average valid observations |
| **avg_dur** | AVG(hourly.avg_duration) | Typical duration |
| **std_dur** | AVG(hourly.std_duration) | Typical variability |
| **avg_dist** | AVG(hourly.avg_distance) | Typical distance |
| **avg_speed** | AVG(hourly.avg_speed) | Typical speed |
| **n_days** | COUNT(DISTINCT date) | Days with data |
| **coverage** | n_days / total_days | Data completeness |

### Weekly pattern formula
```sql
SELECT link_id, daytype, hour_of_day,
       AVG(n_total) as avg_n_total,
       AVG(avg_duration_sec) as avg_dur,
       COUNT(DISTINCT date) as n_days
FROM hourly_aggregation
GROUP BY link_id, daytype, hour_of_day
```

---

## 6) Output file schemas

### Primary outputs

#### hourly_agg.csv
One row per link-date-hour combination with traffic metrics.

| Column | Type | Description |
| --- | --- | --- |
| link_id | string | Link identifier (e.g., s_653-655) |
| date | date | Calendar date (YYYY-MM-DD) |
| hour_of_day | int | Hour 0-23 |
| daytype | string | Day classification (חול/שבת/חג) |
| n_total | int | Total observations |
| n_valid | int | Valid observations |
| avg_duration_sec | float | Average duration in seconds |
| std_duration_sec | float | Duration standard deviation |
| min_duration_sec | float | Minimum duration |
| max_duration_sec | float | Maximum duration |
| avg_distance_m | float | Average distance in meters |
| avg_speed_kmh | float | Average speed in km/h |
| data_quality_flag | int | Quality indicator (0=good) |

#### weekly_hourly_profile.csv
One row per link-daytype-hour showing typical patterns.

| Column | Type | Description |
| --- | --- | --- |
| link_id | string | Link identifier |
| daytype | string | Day type (חול/שבת/חג) |
| hour_of_day | int | Hour 0-23 |
| avg_n_total | float | Average total observations |
| avg_n_valid | float | Average valid observations |
| avg_dur | float | Typical duration (seconds) |
| std_dur | float | Typical duration variability |
| min_dur | float | Minimum typical duration |
| max_dur | float | Maximum typical duration |
| avg_dist | float | Typical distance (meters) |
| avg_speed | float | Typical speed (km/h) |
| n_days | int | Number of days analyzed |
| coverage | float | Data completeness (0-1) |

### Supporting outputs

#### quality_by_link.csv
Per-link data quality metrics.

| Column | Type | Description |
| --- | --- | --- |
| link_id | string | Link identifier |
| total_observations | int | Total raw observations |
| valid_observations | int | Valid observations |
| invalid_observations | int | Invalid/failed observations |
| validity_rate | float | Percentage valid (0-100) |
| date_coverage | float | Days with data / total days |
| hour_coverage | float | Hours with data / total hours |
| avg_daily_observations | float | Average obs per day |
| data_quality_score | float | Overall quality (0-100) |

#### processing_log.txt
Detailed processing information including:
- Start/end timestamps
- File statistics (rows processed, rejected)
- Validation summary
- Error details
- Performance metrics

#### run_config.json
Complete configuration used:
```json
{
  "input_file": "path/to/data.csv",
  "date_range": ["2024-08-01", "2024-08-31"],
  "timezone": "Asia/Jerusalem",
  "chunk_size": 50000,
  "validation_rules": {...},
  "filter_settings": {...}
}
```

---

## 7) Data quality & validation

### Validation rules
| Check | Default Threshold | Action |
| --- | --- | --- |
| Duration range | 1-7200 seconds | Flag/exclude outliers |
| Speed range | 1-200 km/h | Flag unrealistic speeds |
| Distance range | 10-100000 meters | Flag measurement errors |
| Timestamp format | ISO 8601 variants | Parse with fallback |
| Required fields | All present | Skip row if missing |

### Quality indicators
- **Good (flag=0)**: All metrics within expected ranges
- **Warning (flag=1)**: Some metrics outside ranges but usable
- **Poor (flag=2)**: Multiple issues, use with caution

### Outlier handling
- **Statistical bounds**: Mean ± 3×SD for duration
- **Percentile capping**: 1st-99th percentile for speed
- **Minimum observations**: Require ≥3 obs/hour for aggregation

---

## 8) Performance optimization

### Memory management
- **Chunk processing**: Default 50,000 rows per chunk
- **Data type optimization**: Downcast numerics to float32/int32
- **Garbage collection**: Explicit cleanup between chunks
- **Column selection**: Load only required columns

### Processing speed
- **Typical throughput**: 10,000-100,000 rows/second
- **Bottlenecks**: Timestamp parsing, holiday detection
- **Optimization**: Caching, vectorized operations

### Scalability limits
- **Maximum file size**: Limited by disk space (streaming)
- **Maximum rows**: Tested up to 100M rows
- **Memory usage**: ~2GB for 10M row file

---

## 9) Configuration parameters

### Essential settings
```python
{
    # Input/Output
    "input_file": "path/to/data.csv",
    "output_folder": "output/",

    # Temporal
    "date_start": "2024-08-01",
    "date_end": "2024-08-31",
    "timezone": "Asia/Jerusalem",
    "include_weekdays": [0,1,2,3,4],  # Mon-Fri
    "include_hours": null,  # All hours

    # Processing
    "chunk_size": 50000,
    "encoding": "auto",  # or "utf-8", "cp1255"

    # Validation
    "min_valid_observations": 3,
    "outlier_std_threshold": 3.0,
    "speed_percentile_caps": [1, 99]
}
```

### Advanced options
- **custom_holidays**: Path to holiday CSV file
- **link_whitelist/blacklist**: Specific links to include/exclude
- **aggregation_functions**: Custom aggregation formulas
- **quality_thresholds**: Custom quality boundaries

---

## 10) Hebrew text handling

### Encoding resolution
The system detects and corrects Hebrew encoding misidentification:

1. **Detection**: chardet library initial guess
2. **Verification**: Check for Hebrew character frequency
3. **Override**: If Greek (ISO-8859-7) detected but Hebrew chars found → use CP1255
4. **Output**: Save with UTF-8 BOM for Excel compatibility

### Hebrew day names mapping
```python
{
    "ראשון": "Sunday",
    "שני": "Monday",
    "שלישי": "Tuesday",
    "רביעי": "Wednesday",
    "חמישי": "Thursday",
    "שישי": "Friday",
    "שבת": "Saturday"
}
```

### Day type classification
- **חול** (Chol): Regular weekday
- **שבת** (Shabbat): Saturday/weekend
- **חג** (Chag): Holiday

---

## 11) Error handling & recovery

### Common errors and solutions

| Error | Cause | Solution |
| --- | --- | --- |
| Encoding error | Hebrew text corruption | Auto-detect and override |
| Timestamp parse failure | Non-standard format | Multiple format fallbacks |
| Memory error | Large file | Reduce chunk_size |
| Missing columns | Schema mismatch | Flexible column mapping |
| Duplicate DataID | Data quality issue | Keep first, log duplicates |

### Processing continuation
- **Partial failure**: Continue with valid rows
- **Error logging**: Detailed error tracking
- **Recovery state**: Resume from last successful chunk

### Validation warnings
- Missing optional columns → Continue with reduced features
- Invalid numeric values → Replace with NaN, flag row
- Future timestamps → Flag but include in processing

---

## 12) Usage recommendations

### Best practices
1. **Start simple**: Process with default settings first
2. **Validate early**: Check first 1000 rows before full processing
3. **Monitor memory**: Watch RAM usage for large files
4. **Incremental processing**: Process by month for very large datasets
5. **Quality first**: Review quality metrics before using results

### Common workflows

#### Standard daily processing
1. Upload previous day's CSV data
2. Apply date filter for specific day
3. Generate hourly aggregations
4. Review quality metrics
5. Export results

#### Monthly analysis
1. Combine multiple daily CSVs
2. Process full month with weekday filtering
3. Generate weekly profiles
4. Identify patterns and anomalies
5. Create monthly report

#### Real-time monitoring
1. Process latest available data
2. Compare to historical weekly profile
3. Detect deviations from typical patterns
4. Generate alerts for anomalies
5. Update dashboards

---

## 13) Integration with other components

### Data flow
```
CSV Input → Processing Pipeline → Hourly/Weekly Aggregations
                                          ↓
                                    Maps Component
                                    Control Validation
                                    External Analytics
```

### Output compatibility
- **Maps**: Direct consumption of hourly_agg.csv
- **Control**: Link_id matching for validation
- **BI Tools**: Standard CSV/Parquet formats
- **APIs**: JSON export option available

### Coordinate systems
- Processing: No spatial operations (link_id only)
- Maps integration: Joins via link_id to shapefile geometries
- Control validation: Shared link_id naming (s_FROM-TO)