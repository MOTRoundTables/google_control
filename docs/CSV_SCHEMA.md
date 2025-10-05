# CSV Input Schema Documentation

## Required Columns

The following columns are **required** in your CSV file:

| Column Name | Alternative Names | Data Type | Description | Example |
|-------------|-------------------|-----------|-------------|---------|
| `DataID` | - | Integer/String | Unique identifier for each record | `287208545` |
| `Name` | - | String | Link identifier (used as link_id) | `s_653-655` |
| `SegmentID` | - | Integer | Segment identifier | `1185048` |
| `RouteAlternative` | - | Integer | Route alternative number | `1` |
| `RequestedTime` | - | Time | Requested time for the measurement | `13:45:00` |
| `Timestamp` | - | DateTime | Actual timestamp of measurement | `2025-07-01 13:45:42` |
| `DayInWeek` | - | String | Day name (Hebrew/English) | `יום ג` or `Tuesday` |
| `DayType` | - | String | Type of day | `יום חול` (weekday) |
| `Duration` | `Duration (seconds)` | Float | Travel duration in seconds | `2446.0` |
| `Distance` | `Distance (meters)` | Float | Travel distance in meters | `59428.0` |
| `Speed` | `Speed (km/h)` | Float | Average speed in km/h | `87.465576` |
| `Url` | - | String | Recording URL | `https://...` |
| `Polyline` | - | String | Route polyline data | `_oxwD{_wtE...` |

## Optional Columns

| Column Name | Data Type | Description | Example |
|-------------|-----------|-------------|---------|
| `is_valid` | Boolean | Validity flag for the record | `TRUE`/`FALSE` |
| `valid_code` | String | Validation code/reason | `VALID` |

## Column Name Flexibility

The system supports flexible column naming. These variations are automatically recognized:

- **Duration**: `Duration`, `Duration (seconds)`
- **Distance**: `Distance`, `Distance (meters)`  
- **Speed**: `Speed`, `Speed (km/h)`

## Data Types and Formats

### DateTime Format
- **Timestamp**: `YYYY-MM-DD HH:MM:SS` (e.g., `2025-07-01 13:45:42`)
- **RequestedTime**: `HH:MM:SS` (e.g., `13:45:00`)

### Numeric Fields
- **Duration**: Positive float (seconds)
- **Distance**: Positive float (meters)
- **Speed**: Positive float (km/h)

### Text Fields
- **DayInWeek**: Hebrew or English day names
- **DayType**: Hebrew or English day type descriptions

## Validation Rules

1. **Required columns must be present** (with flexible naming)
2. **Timestamps must be parseable** in the specified format
3. **Numeric fields should be positive** for meaningful analysis
4. **Duplicate records** are automatically removed by DataID and link+timestamp
5. **Invalid records** are filtered based on the `is_valid` column if present

## Example CSV Structure

```csv
DataID,Name,SegmentID,RouteAlternative,RequestedTime,Timestamp,DayInWeek,DayType,Duration (seconds),Distance (meters),Speed (km/h),Url,Polyline,is_valid
287208545,s_653-655,1185048,1,13:45:00,2025-07-01 13:45:42,יום ג,יום חול,2446.0,59428.0,87.465576,https://...,_oxwD{_wtE...,TRUE
287214814,s_653-655,1185048,1,14:15:00,2025-07-01 14:15:41,יום ג,יום חול,2463.0,59428.0,86.86188,https://...,_oxwD{_wtE...,FALSE
```

## Common Issues and Solutions

### ❌ "Missing required columns"
- **Cause**: Column names don't match expected format
- **Solution**: Use the alternative names listed above or rename columns

### ❌ "Timestamps failed to parse"
- **Cause**: Timestamp format doesn't match `YYYY-MM-DD HH:MM:SS`
- **Solution**: Ensure timestamps are in the correct format

### ❌ "No valid data found"
- **Cause**: All records marked as invalid or filtered out
- **Solution**: Check the `is_valid` column values and data quality

## File Requirements

- **Format**: CSV (Comma-separated values)
- **Encoding**: UTF-8 (preferred) or other common encodings
- **Size**: No strict limit, but large files are processed in chunks
- **Headers**: First row must contain column names