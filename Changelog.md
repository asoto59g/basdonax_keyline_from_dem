# Changelog

## 0.7.2 - QGIS 4 / Qt6 compatibility

### Fixed

- Updated PyQGIS enum references for QGIS 4 / Qt6 compatibility.

## 0.7.1 - Security Scan Compliance

### Changed

- Replaced silent `except` branches with explicit fallback values or logged warnings.
- Removed `except ...: pass` and `except ...: continue` patterns flagged by the QGIS security scanner.

## 0.7.0 - Output Reliability and Packaging

### Changed

- Unified release metadata and documentation to version 0.7.0.
- Design Unit output geometries are explicitly converted to MultiPolygon.
- Feature-sink write failures now stop processing with a clear error.

## 0.6.0 - Phase 5.0 - Multicriteria Optimization

### Added

- Phase 5 optimization engine.
- WDI - Water Distribution Index.
- Hydrological line breaking in potential drainage zones.
- Target longitudinal grade evaluation.
- Near-contour behavior evaluation.
- Redistribution score.
- Hydrological safety score.
- Direction score.
- Optimized ICL penalty.
- New output fields:
  - `wdi`
  - `grade_fit`
  - `flow_ang`
  - `near_cont`
  - `redist`
  - `hyd_score`
  - `dir_score`
  - `dr_breaks`
  - `opt_score`
  - `opt_act`
  - `opt_review`

## 0.5.0 - Phase 4.0 - Intelligent Mother Line

### Added

- Intelligent Mother Line by Design Unit.
- Mother line audit layer.
- Centrality, hydrology, slope, radius, coverage and sinuosity scores.
- Fallback to classical Phase 2 mother line selection.

## 0.4.0 - Phase 3.0 - Design Units

### Added

- Multiunit architecture.
- Optional external Design Units.
- Automatic preliminary Design Units.
- Local spacing and maximum length by Design Unit.
- Geomorphometric classification.

## 0.3.2 - Phase 2.2 - Hydrological Analysis

### Added

- Hybrid D8 flow direction.
- Flow accumulation.
- Potential drainage extraction.
- Hydrological line metrics.
- Preliminary hydrological risk classification.

## 0.2.0 - Phase 1 - Strengthened Geometric Engine

### Added

- DEM validation.
- Contour-based mother line.
- Offset generation.
- Slope and radius diagnostics.
- GNSS point export.