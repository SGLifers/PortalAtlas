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

Academy recovery currently includes:

| Item | Count |
| --- | ---: |
| Existing mesh assets with appearance sections | 459 |
| Referenced materials | 441 |
| Materials with usable color parameters | 179 |
| Materials retaining neutral fallback | 262 |
| Component override arrays | 1,297 |

Resolved parameters apply to roughly 69% of visible instanced mesh triangles.
That is a triangle-count measure, not surface-area coverage or an accuracy score.
No mesh/level export errors or material exceptions remain in the pilot export.

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

Validation: **48 Python tests** and **5 Node tests** pass. Real-asset tests compare
all appearance section counts to the existing mesh buffers, verify color
provenance/finite linear values and preserve component overrides. API tests cover
missing, stale, malformed and wrong-map appearance data. Node tests cover gaps,
overlapping sections, unsafe material slots, invalid colors and independent
instance assignments.

Browser checks confirmed the Academy color view, Neutral preference persistence,
colored cutaway at 20 m, clipping off/on, top view, neutral fallback on Abyss and
return to Academy colors. P01→P06 remained four steps, approximately 4.5 seconds
and peak difficulty 78 across surface modes. At 390×844 the controls fit without
horizontal overflow. No browser console warnings/errors were observed.

Next steps toward a more faithful view are texture/UV extraction, material-layer
evaluation and transparency handling. A broader map rollout should retain the
same source qualification and report unresolved materials rather than substitute
guessed colors.
