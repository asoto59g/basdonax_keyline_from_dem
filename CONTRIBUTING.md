# Contributing

Thank you for your interest in contributing to Basdonax Keyline from DEM.

## Development Guidelines

Contributions should preserve the methodological structure of the plugin:

1. DEM validation
2. Hydrological analysis
3. Design Units
4. Intelligent Mother Line
5. Multicriteria Optimization
6. Future professional plugin interface

## Code Style

- Use clear Python code.
- Avoid hidden dependencies.
- Keep QGIS Processing parameters explicit.
- Avoid hardcoded local paths.
- Preserve compatibility with QGIS 3.x unless otherwise stated.
- Use metric CRS for design operations.

## Reporting Issues

When reporting an issue, please include:

- QGIS version
- Operating system
- DEM resolution
- CRS
- Processing parameters used
- Error message
- Minimal dataset if possible

## Pull Requests

Before submitting a pull request:

- Run syntax checks.
- Test with a small DEM.
- Update `CHANGELOG.md`.
- Document new parameters in `README.md`.