# Validation — 2026-11-03

The local app is complete and served at http://127.0.0.1:8741. This report
validates the installed asset pipeline and computed graph, not measured gameplay.

## Results

- 25 standalone arena/training features; 3,432 wall nodes and 14,722 directed edges.
- 2,234 active landscape patches decoded at their serialized collision mip.
- All 25 datasets pass source coverage, variant isolation, graph invariants and
  browser buffer checks. No missing expected map features.
- 40 Python tests pass. Browser JavaScript syntax check passes. C# reader builds
  with zero errors. Setup was rerun successfully using the prepared local cache.
- Source: immutable local game image2a8c85545524, executable619e4753e2f68c72.
  215,239 mounted files; 1,794 indexed map packages. Model5 + finalization1.
- No game process was started, game files modified, or live host worker operated.

## Browser verification

Academy P01→P06 returns four placement steps,4.5 estimated seconds and peak
difficulty78. Easiest chooses five steps including walking,6.8 estimated seconds
and peak62. Avoiding P46 recalculates the route. Movement filters and a difficulty
limit10 produce the expected no-route state. Saved routes restore their map,
objective and filters. Native route and full-graph JSON attachments download and
parse correctly, retaining source/revision/model details.

Fracture renders1,327 shared mesh buffers and457 walls without console errors.
Top/3D/cutaway layers, adaptive labels, source inspection, map switching and URL
restore were checked. At390×844 the planner stacks below the map with no horizontal
overflow. The temporary viewport override was reset.

A browser import of Creative EmptySpace completed through the real reader and
compiler; the app correctly reported zero portal walls. Its generated QA scene
was removed afterwards; cached source extraction/logs remain local. The default
25 arena scenes remain available. App preview: `.local/portal-atlas-preview.jpg`.

## Dataset audit

| Feature | Walls | Edges | Terrain patches | Geometry coverage |
|---|---:|---:|---:|---|
| Abyss | 58 | 181 | 0 | Passed |
| Academy | 69 | 313 | 0 | Passed |
| Bypass | 105 | 478 | 109 | Passed |
| Containment | 39 | 99 | 0 | Passed |
| Core | 48 | 99 | 0 | Passed |
| Eden | 54 | 156 | 0 | Passed |
| Erosion | 447 | 1808 | 132 | Passed |
| Foregone Destruction | 83 | 288 | 0 | Passed |
| Fracture | 457 | 2086 | 131 | Passed |
| Frontier | 87 | 319 | 511 | Passed |
| Glacier | 489 | 2209 | 155 | Passed |
| Grit | 75 | 204 | 256 | Passed |
| Hammerhead | 94 | 318 | 188 | Passed |
| HangmanR3 | 16 | 0 | 0 | Passed |
| Inferno | 417 | 2158 | 125 | Passed |
| Karman Station | 70 | 324 | 0 | Passed |
| Oasis | 76 | 580 | 26 | Passed |
| Ozone Night | 74 | 242 | 0 | Passed |
| Runway | 78 | 291 | 187 | Passed |
| Sanctum | 275 | 910 | 254 | Passed |
| Stadium | 54 | 169 | 0 | Passed |
| Terra13 | 112 | 505 | 160 | Passed |
| Training | 50 | 593 | 0 | Passed |
| TriHard | 46 | 210 | 0 | Passed |
| Zenith | 59 | 182 | 0 | Passed |

HangmanR3 has16 zone-wall actors and no candidate edges under this model. Ozone
and Ozone Graffiti are shared sublevel libraries, not standalone arena roots;
Ozone Night resolves their required dependencies. These counts do not describe
current matchmaking playlists.

## Practical limits

Portal wall centers are sampled. Timing/difficulty and gravity/jump behavior are
estimates; base movement defaults come from assets, while mode overrides remain
unresolved. The start wall must already have a portal. Launch-wall arrivals are
terminal because forced outgoing trajectories are not modeled. Direct walking
and sampled jumps do not enumerate routes around corners or full momentum state.

Collision hulls, conservative primitive bounds and render fallbacks remain
proxies. Terrain hole-boundary cells are approximated. BlockingVolume Pawn and
PortalLauncher responses are checked; this does not reproduce all game trace
channels, dynamic objects, enemies or runtime rule changes. Nongeometry schema
warnings are retained in each map's source notes. Rejected geometry or missing
required sources withhold edges.

## Re-run

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/audit_maps.py
.venv/bin/python tools/import_maps.py --all-arenas --refresh
```

Detailed private reports: data/validation-report.json, data/import-report.json.
Logs: .local/audit-final.log, .local/tests-final.log, .local/setup-verify.log,
.local/build.log and the per-map import logs. Proprietary map data stays ignored.
