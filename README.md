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

`--all-arenas` imports 25 standalone arena/training features in this build.
Shared Ozone sublevel libraries are resolved as dependencies of Ozone Night. It is not a claim about which maps are in a particular playlist.
Completed imports are reused; `--force` extracts and compiles them again.
`--refresh` upgrades stale compiled models using the existing extracted assets.
Cooked variants stay separate. The selected root is shown in source details;
`tools/compile_scene.py MAP_Name --root /MAP_Name/OtherWorld` selects an alternative.

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

## Verify

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/audit_maps.py
node --test tests/colors.test.mjs
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
