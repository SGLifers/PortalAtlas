# Asset color preview

In the layer controls, choose **Surfaces → Map colors** or **Neutral**. The choice
is remembered in this browser; a map without imported appearance data uses neutral
geometry. The importer supports all already-extracted standalone arena/training
maps, with Academy as the original reference pilot.
Both modes retain wall selection, routes, top/orbit views and configurable cutaway.

## What the preview represents

Colors are read from the installed assets. The exporter retains each mesh's
material sections, follows material parents/layers, and reads base-color and tint
parameters. Per-component material overrides remain separate, so two instances of
the same mesh can have different colors. Every recovered color records its source
asset, parameter name and whether it came through a material layer. No colors are
invented from asset names or sampled from screenshots.

This is a **representative parameter-color preview**, not a reproduction of Unreal
materials. It does not evaluate textures, layer blending/masks, shader switches,
vertex paint, transparency effects or game lighting. A tint can look different
when multiplied by its original texture. Layered materials use the first
recoverable representative color. Neutral teal is retained when no supported color
can be recovered. Browser lights and filmic tone mapping provide a simple shaded
preview; switching back to Neutral restores the original viewer lighting.

Landscape heightfields use the component's serialized override or material
instance selected for its collision LOD. They receive a representative parameter
color from that shader; terrain texture layers and weightmaps are not evaluated.
Collision-hull overview proxies receive a material only when their source mesh
has exactly one slot and every source LOD section uses that slot. Multi-material
proxies stay neutral because their render sections cannot be mapped reliably to
the simplified hull. Per-component overrides still apply to the sole proxy slot.

The control reports the percentage of **rendered mesh triangles** with a recovered
color. This weights visible instances and component overrides, and uses actual
collision-proxy triangle counts when the viewer draws proxies. Terrain is included;
portal overlays and the grid are excluded. It is not surface-area coverage or an
accuracy score. Texture-driven materials often have no supported tint parameter,
so coverage can be low even when the entire map was imported successfully.

## Validated map coverage

All 25 standalone arena/training scenes in this installed dataset have current
validated appearance data. Shared Ozone/Ozone Graffiti sublevel libraries are
excluded. Each export has zero mesh/level/material exceptions. Material counts
include component overrides and embedded landscape instances; shared materials
are counted separately for each map. Unresolved records remain explicit fallbacks.

| Map | Recovered / referenced materials | Colored mesh triangles |
| --- | ---: | ---: |
| Abyss | 35 / 172 | 0.7% |
| Academy | 179 / 441 | 69.0% |
| Bypass | 183 / 909 | 63.5% |
| Containment | 39 / 97 | 77.4% |
| Core | 144 / 404 | 81.1% |
| Eden | 148 / 456 | 8.5% |
| Erosion | 238 / 1714 | 10.1% |
| Foregone Destruction | 36 / 197 | 13.6% |
| Fracture | 280 / 1969 | 3.6% |
| Frontier | 141 / 331 | 53.0% |
| Glacier | 274 / 2078 | 33.2% |
| Grit | 85 / 433 | 84.2% |
| Hammerhead | 312 / 901 | 13.3% |
| HangmanR3 | 33 / 360 | 9.4% |
| Inferno | 176 / 1305 | 3.5% |
| Karman Station | 54 / 144 | 12.0% |
| Oasis | 136 / 349 | 71.0% |
| Ozone Night | 225 / 1174 | 71.4% |
| Runway | 556 / 1885 | 43.9% |
| Sanctum | 235 / 1407 | 12.0% |
| Stadium | 160 / 579 | 61.9% |
| Terra13 | 115 / 369 | 85.4% |
| Training | 5 / 119 | 0.1% |
| TriHard | 32 / 122 | 61.3% |
| Zenith | 378 / 986 | 62.2% |

The wide coverage range is expected for a parameter-only preview. In particular,
Training and Abyss rely heavily on unsupported texture/shader inputs; most of
their surfaces remain neutral. No colors are fabricated to fill those gaps.

Academy remains the parity reference: its complete material, mesh section and
component override tables match the original pilot after reader optimizations.
All 25 scene/graph files stayed byte-identical throughout the rollout.

## Import or refresh colors

Use the existing local installation, recovered mappings and compiled scene. Build
the reader once after updating its source, then run the independent color importer:

```bash
CUE4PARSE_SKIP_NATIVE=1 DOTNET_PROCESSOR_COUNT=2 .tools/dotnet/dotnet build tools/AssetReader -c Release -m:2
.venv/bin/python tools/import_colors.py MAP_Academy
.venv/bin/python tools/import_colors.py --all-arenas
.venv/bin/python tools/audit_colors.py
```

With no map argument, `import_colors.py` defaults to Academy. Pass one or more map
IDs or **--all-arenas** for all imported standalone arena/training scenes. Shared
sublevel libraries are excluded from that batch. Current, validated sidecars are
reused; add **--refresh** after changing the reader or to force asset recovery.
Color availability depends on material parameters. Never overwrite the reader
binary while an asset import is using it.

The importer shares `.local/import.lock` with geometry imports. It reads archives
without launching the game, and writes only ignored `data/appearance/<map>.json`
using an atomic replacement. Logs go to `.local/<map>-colors.log`. It does not
rewrite geometry buffers, scenes, portal nodes, route costs or collision data.
After an import, reload that map in the viewer. If the server was already running
before the color endpoint was added, restart this checkout's Atlas server once.

The wrapper exports into temporary staging, audits the result against the exact
scene/buffer revision, then publishes it atomically. A failed map leaves the last
published sidecar intact; the batch continues with other maps and exits nonzero.
Private rejected outputs remain in `.local/<map>-colors-rejected.json` for diagnosis.
`data/color-import-report.json` records progress and failures; the independent
audit writes `data/color-validation-report.json`. Both are ignored local data.

Appearance data is tied to the existing scene revision. After recompiling a scene,
rerun the color importer; the viewer withholds stale appearance data and keeps
neutral geometry available. Rebuilding the route graph is not required just to
import colors. Extracted materials and color sidecars stay out of Git.

## Implementation and checks

- `ColorExporter.cs`: separate `export-colors` reader command; resolves archive
  aliases for GameFeature plugins and nested material exports. Reads serialized
  parameters with recovered property names, including indexed property suffixes.
- `tools/import_colors.py`: bounded, locked, resumable import wrapper.
- `tools/audit_colors.py`: buffer/section/provenance checks and triangle coverage.
- `/api/colors/<map>`: optional appearance endpoint, validating map ID, format,
  version and scene revision. The graph API remains independent.
- `web/colors.js`: validates RGB triples and exact triangle-section coverage;
  invalid data falls back to neutral. Component overrides keep null-slot fallback.
- `web/app.js`: groups instances by mesh and material assignment, retains linear
  RGB colors, applies cutaway planes to every surface material, and disposes color
  resources when changing arenas. A stale asynchronous map response is discarded.

Validation: **54 Python tests** and **9 Node tests** pass. Real-asset tests compare
all 25 current sidecars and appearance section counts to the existing mesh/proxy buffers, verify color
provenance/finite linear values and preserve component overrides. API tests cover
missing, stale, malformed and wrong-map appearance data. Node tests cover gaps,
overlapping sections, unsafe material slots, invalid colors and independent
instance assignments.

The original pilot browser checks confirmed the Academy color view, Neutral preference persistence,
colored cutaway at 20 m, clipping off/on, top view, neutral fallback on Abyss and
return to Academy colors. P01→P06 remained four steps, approximately 4.5 seconds
and peak difficulty 78 across surface modes. At 390×844 the controls fit without
horizontal overflow. No browser console warnings/errors were observed.

The all-map rollout also verified Core colors (81.1%), Neutral preference after
reload, Bypass landscape colors (63.5%), top/orbit switching, cutaway off/on and
a 20m cutoff, and the screenshot success response. At390×844 the coverage label
fits without horizontal overflow. No console warnings/errors were observed.
The browser download-event API did not expose the blob download, so this run
verifies its success toast rather than claiming independent PNG-file inspection.

Next steps toward a more faithful view are texture/UV extraction, material-layer
evaluation and transparency handling. Keep reporting unresolved materials rather
than substituting guessed colors.
