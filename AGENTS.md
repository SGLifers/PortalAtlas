# Portal Atlas

Read docs/HANDOFF.md before continuing. Keep this repository independent of
SplitgateHost and never operate its live game workers. The installed asset
source is an immutable local Docker image; inspect it using separate read-only,
network-disabled containers. Do not launch Steam or the game.

The user requires game assets, not video, screenshots, hand-authored maps, or
synthetic demonstration maps. Portal walls are destination nodes; angles,
placement opportunities, and movement are directed edges. Preserve provenance
and distinguish computed candidates from collision-validated routes and measured
game physics. Never present unknown data or estimates as verified.

Commit useful milestones. Update docs/HANDOFF.md at each milestone and before
context handoff with exact commands, results, blockers, and next actions.
Keep game binaries, extracted proprietary assets, tools, and local settings out
of Git. Run bounded commands with at most four CPUs so the existing host remains
usable. The requested deliverable is a local web application; no publication.
