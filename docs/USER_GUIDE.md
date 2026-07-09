# User Guide

## Basic Workflow

1. Prepare a clean DEM / DTM.
2. Reproject to a metric CRS.
3. Optionally prepare a design mask.
4. Optionally prepare exclusion zones.
5. Optionally prepare Design Units.
6. Run the plugin from the Processing Toolbox.
7. Review the generated outputs:
   - LDI lines
   - GNSS points
   - potential drainage
   - Design Units
   - Intelligent Mother Lines
8. Review ICL and WDI values.
9. Validate in the field before construction.

## Recommended Initial Parameters

| Parameter | Suggested Value |
|---|---:|
| Contour interval | 0.50 m |
| Base spacing | 3.5 m |
| N offsets | 20 - 50 |
| Minimum length | 20 m |
| Maximum length | 150 - 250 m |
| Maximum longitudinal slope | 0.50 % |
| Minimum radius | 12 m |
| Flow threshold area | 300 - 700 m2 |
| Target grade | 0.12 % |
| Grade tolerance | 0.18 % |
| Drain break buffer | 5 m |
| Minimum WDI | 55 |
| Maximum flow angle | 12 degrees |

## Field Validation

Before construction, verify:

- active drainage paths
- wet zones
- erosion marks
- soil compaction
- slope breaks
- machinery turning radius
- existing infrastructure