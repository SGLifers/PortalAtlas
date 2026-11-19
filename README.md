# Portal Atlas

A local web app that reads **Splitgate: Arena Reloaded's installed game assets**
into a 3D map and directed portal-route graph. **Portal walls are destination
nodes; placement angles and movement are edges.**

Open **http://127.0.0.1:8741** while the local server is running.

```bash
./run.sh
```

The viewer supports orbit and top views, a cutaway with a configurable cutoff height,
selectable walls, outgoing placement angles, route objectives, difficulty limits,
unavailable walls, browser-local saved routes, and JSON export. Everything needed
by the browser is served locally; there are no CDN or account dependencies.

Use the **Cutoff height (m)** slider or number field beneath the layer toggles
to change the cutaway live. Heights use world Z in metres and are remembered per
map in this browser. **Auto** restores the map's automatic cutoff height.

**Surfaces → Map colors** enables asset colors across the imported arenas. It uses recovered
material color/tint parameters, with neutral fallback for unresolved surfaces.
The selector remembers your preference and reports recovered triangle coverage.
Run `tools/import_colors.py --all-arenas` to import colors for ready scenes.
This is a simplified color preview; original textures,
material masks and game lighting are not reproduced. Routes and cutaway work in
both modes. See [map colors](docs/MAP_COLORS.md) for scope and import commands.

Click **Screenshot** beside the **3D / Top** controls to download the current map
viewport as a PNG. It captures the camera angle, surface mode, cutaway, visible
geometry, portal/route overlays and visible wall labels at the current render
resolution. Toolbars and side panels are excluded. Hide **Labels** before capture
for an unlabeled image. Filenames include the map, view and a UTC timestamp.
Capture happens entirely in the browser and does not upload the image.

For Portle clue captures, use **Portals** to toggle all portal overlays, or open
**Choose portals for clues** to select a subset. The portal list also has individual
visibility checkboxes plus **Show all**, **Hide all** and **Only selected**.
Hidden portals lose their labels and connected overlay lines in the viewer and
screenshots. Visibility is remembered per map and does not exclude walls from
route planning. The map's underlying wall geometry remains intact.
Uncheck **Labels** and **Lines** for clean clues without wall IDs or route/angle
lines, while retaining the portal overlays you selected.

To work with several walls, open **Wall groups → Select walls on map**. Click
portal faces or their labels to toggle selection, or drag a rectangle around
wall centers to add several at once. Shift-drag removes walls from the selection.
Box selection includes enabled portal overlays behind map geometry.
Selected walls turn gold. Camera navigation pauses while selecting; **Done** or
Escape resumes navigation and opens the group panel. The layer controls are
temporarily tucked away to leave room for selecting on smaller screens.

Use **Show / Hide / Only these** immediately on a selection, or enter a name and
**Save group**. Each saved group has the same visibility actions. Click its name
to load its members, change the selection or name, then **Update group**. **Save
as new…** keeps the selection and starts another group, useful for successive
Portle clues. Groups may overlap; a visibility action applies to the actual walls
in that group. Hidden walls remain members: show them before picking them again.
Groups persist separately for each map in this browser. Gold editing highlights
and selection controls are excluded from screenshot downloads.

## First setup

Requirements: Linux x64, Python 3.12+, Bash, Git, and either the local Docker game
image recorded in `tools/versions.json` or a legitimate PC installation. The
current machine's installation is already copied and indexed under ignored
`data/`. Do not run SplitgateHost or launch the game for this application.

```bash
./setup.sh
.venv/bin/python tools/import_maps.py
./run.sh
```

Setup installs isolated Python tools and the pinned .NET SDK/CUE4Parse reader.
The first run downloads development dependencies; subsequent analysis is offline.
It copies approximately **35.6 GiB** of archives from a stopped, read-only Docker
snapshot. It never starts Steam or the game and never touches existing workers.
The temporary snapshot is removed after copying.

For an installation outside Docker, prepare it before setup:

```bash
python3 tools/prepare_assets.py --game-dir '/absolute/path/to/Splitgate 2'
./setup.sh
```

Extraction is pinned to the installed executable's SHA256. An unknown build
stops key/schema recovery instead of silently using incompatible offsets.

## Import maps

The initial command imports Academy, Abyss, Grit, and Oasis. The browser's
**Import installed map** dialog lists every indexed map feature and runs imports
one at a time. Large maps take longer because every directed placement is checked.

```bash
.venv/bin/python tools/import_maps.py MAP_Karman_Station
.venv/bin/python tools/import_maps.py --all-arenas
```

`--all-arenas` imports 31 standalone arena/training maps in this build, including
six Simulation maps cooked inside the shared `MAP_Simulation` feature. Each has
its own scene ID and selected root, so their portal layouts stay separate.
Shared Ozone sublevel libraries are resolved as dependencies of Ozone Night. It is not a claim about which maps are in a particular playlist.
Completed imports are reused; `--force` extracts and compiles them again.
`--refresh` upgrades stale compiled models using the existing extracted assets.
Cooked variants stay separate. The selected root is shown in source details;
`tools/compile_scene.py MAP_Name --root /MAP_Name/OtherWorld` selects an alternative.
For example, import Simulation Charlie with
`.venv/bin/python tools/import_maps.py MAP_Simulation_Charlie`. Captures use the
same batch controls as other maps. Representative Simulation material colors are
available through the existing color importer; portal-only captures do not use
geometry colors.

## Model and limits

- **Nodes:** actual portal-wall actors, mesh transforms, face directions,
  dimensions, and serialized launch properties.
- **Placement edges:** rays to the destination wall, front-face checks, aiming
  incidence, angular target clearance, and camera turn from the exit face.
- **Movement edges:** direct floor-supported corridors and sampled jump arcs.
  Movement includes placing an entry portal at the destination before chaining.
- **Search:** Dijkstra over each wall's face and arrival state. The search cannot
  silently switch faces or turn a launch-portal arrival into a standing player.
- **Costs:** fastest minimizes estimated seconds; easiest minimizes accumulated
  effort; balanced combines both. The summary difficulty is the hardest step.

Ray tests use asset simple collision hulls, conservative bounds for unsupported
primitives, and render-triangle fallbacks. Terrain uses the heightmap at its
serialized collision mip with visibility holes. Shared mesh BVHs and an instance
BVH keep large maps practical. These proxies do not reproduce every game trace
channel or physics behavior. Coverage checks retain extraction errors and withhold
routes when required geometry is missing. Blocking brushes use their Pawn and
PortalLauncher channel responses; empty and physics-only brushes are distinguished.
Cross-feature always-loaded levels are resolved from the archive index. Portal centers are sampled, so this
is not an exhaustive enumeration of every placement on a large wall. Walking
around corners, forced launch trajectories, and full momentum conservation are
not inferred. A launch wall can be a route destination; its unmodeled outgoing
motion cannot be chained as a stationary exit.

Serialized base walking speed and navigation dimensions are recovered where
available. Active mode modifiers, gravity/jump behavior, aiming time, and human
difficulty remain qualified estimates. These are planning candidates and training
references, not measured speedrun records or guaranteed executable inputs.

## Random Portle clue groups

Open **Wall groups → Create 6 random groups** to shuffle every portal wall on the
current map into six disjoint groups, including currently hidden walls. Each wall
belongs to exactly one random group. Sizes are equal when the count divides by
six, otherwise they differ by at most one. Maps with fewer than six walls have
empty groups. Existing manually saved wall selections stay intact.

Use **Reshuffle 6 groups** until you like the distribution. Creation/reshuffling
previews group1. **Only this** isolates one group; **Through here** shows groups
1 through that row, so six captures can progressively reveal the entire map.
Use **Screenshot** after each visibility choice; the camera and cutaway stay put.
Random groups are remembered separately for each map in this browser and survive
reload. A partition that no longer matches the map's walls must be regenerated.
These controls change visibility only; they do not alter route graphs, extracted
assets or upload/publish Portle clues.

## Batch screenshot capture

Open **Batch clues** in the viewer. Capture all imported standalone arenas, the
current arena, or a checked subset. Each map produces six PNGs and a manifest in
one downloadable ZIP. No images are uploaded or published to Portle.

Choose a resolution (1280×800, 1600×1000 or 1920×1080), random camera angles per
clue or one random angle per map, and progressive groups 1–N or one disjoint group
per clue. **New seed** makes another distribution. Reusing the seed, map data and
settings reproduces the portal groups and camera poses. **Group sizes** defaults
to growing groups scaled to each map's portal count, with a minimum of four
portals in the first clue. Reserve four portals per
group, then distribute the remaining portals with weights 1, 2, 3, 4, 5, 6,
rounding by largest remainder (ties favor later groups). For 50 portals the
groups are 5, 7, 8, 9, 10, 11; cumulative screenshots show 5, 12, 20, 29, 39, 50
portals. A 30-portal map starts with 4; a 447-portal map starts with 24. Every
portal appears in exactly one group, and for maps with at least 24 portals each
later group is at least as large as the previous one. Smaller maps start with
four (or all portals if fewer than four exist) and divide the rest evenly among
the remaining five clues; six nondecreasing groups starting at four are
impossible below 24 portals. Changing this planner affects new captures;
existing PNGs keep their
original portal counts and must be recaptured to use the new progression.
**Even groups** retains the previous partition. Batch groups do not replace
browser-saved groups from Wall groups, whose six random groups remain balanced.

Captures show portals and hide labels, route lines, all angles, the grid and editing
highlights. Geometry and cutaway default to off; enable either in the batch dialog
if desired. Surface mode and each map's saved cutoff height (when cutaway is enabled)
are respected. Camera positions stay above the
map and frame its full portal apertures. Architecture may still hide walls, so
review the images before uploading them into the local Portle editor. This is an
asset-color/proxy preview, with the same fidelity limits as the normal viewer.

Keep the tab open while capturing. Maps load sequentially with two mesh loaders.
Progress and Cancel remain available; cancellation discards an unfinished map
and keeps completed maps in the ZIP. Failed map loads are skipped and listed in
both the report and manifest. The original map, camera, render resolution, layer
settings and portal visibility are restored when the run finishes or is cancelled.
The archive has a 384 MiB memory limit; choose smaller batches if it is reached.
If browser downloads are unavailable, click **Save ZIP locally** after capture.
Atlas saves the same archive under ignored `.local/captures/` and shows its full
path. Each save creates a new private file; existing captures are preserved.
The manifest records map IDs/names, revisions, portal groups, camera poses,
cutaway/color settings and any errors. Its folders identify answers for author
review; PNGs have generic clue filenames. Treat the archive as private clue data.

## Verify

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/audit_maps.py
node --test tests/*.test.mjs
```

Tests cover geometry intersections/transforms, face continuity, launch arrival
state, directed search, objectives/filters, API isolation, and real asset graph
invariants when the private data is available. Browser QA and the imported dataset counts are documented in
[docs/VALIDATION.md](docs/VALIDATION.md).

## Repository and data

- `server/`: local HTTP API, mesh/instance BVHs, route search.
- `web/`: browser UI and locally vendored Three.js.
- `tools/AssetReader/`: CUE4Parse asset/mesh exporter.
- `tools/reflection_emulator.py`, `native_metadata.py`, `build_mappings.py`:
  isolated offline reflection-schema recovery.
- `data/`: ignored installation, local key, recovered schemas, extracted assets,
  movement defaults, compiled scenes, and import reports.
- `.local/`: ignored server/import logs and verification artifacts.

Game binaries, extracted proprietary assets, local keys, and account state never
enter Git. This repository has no remote and publishes nothing. Read
[docs/HANDOFF.md](docs/HANDOFF.md) before continuing development.
