# Architecture and acceptance

## Scope

- Read the installed PC game archives without modifying the installation.
- Extract map instances, transforms, portal surfaces, and usable geometry.
- Display the extracted maps in a local browser application.
- Use actual portal walls as destination nodes. Directed edges encode angles,
  line of sight, placement, and movement; retain the distinction between those
  actions in both the UI and search.
- Compare routes by estimated time, aiming difficulty, movement demands, and
  confidence. Portal-pair state is needed for executable chained routes.
- Save/load local analyses and export route data with source provenance.

## Data boundary

Game data and generated scene files remain ignored under data/. The Git
repository contains source, schemas, tests, and documentation only. No synthetic
map may be displayed as a real map. Missing extraction must remain visible.

## Validation

1. Identify actual archive formats, engine compatibility, and encryption state.
2. Deserialize a real map and identify portal actor/mesh semantics.
3. Verify transforms and geometry with asset metadata and independent checks.
4. Test graph invariants, occlusion, directed movement, and route search.
5. Exercise the browser interface on real extracted data.
6. Document which physics parameters are asset-derived versus estimates.

## Initial implementation direction

Python local HTTP/API server, browser ES modules and locally vendored 3D viewer,
with a CUE4Parse-based command-line extractor if archives are compatible.
Prefer reproducible local tooling over a hosted dependency or in-game injection.
