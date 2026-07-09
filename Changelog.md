# Changelog

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