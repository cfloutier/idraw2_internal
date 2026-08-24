# Local modifications vs. the vendor source

This file tracks every behavioral change made in this repository on top of
the vendor-supplied `idraw2_0internal` source (originally imported from the
Inkscape extension bundle — see `README.md` → "Source provenance"). It exists
because this repo has no other changelog, and because the next vendor update
will need to be **merged**, not just dropped in: this doc is the checklist
for that merge, for a human maintainer and for an AI assistant alike.

## How to use this file during a vendor merge

1. Get the new vendor source tree (fresh copy of `idraw2_0internal` from the
   updated Inkscape extension bundle).
2. For each entry below, check whether the vendor rewrote the touched
   function/region:
   - **Unchanged upstream** → re-apply the local diff as-is (or just keep
     this repo's version of the touched lines).
   - **Changed upstream** → the fix must be re-implemented against the new
     code, using the "Why" and "What changed" text below to reconstruct
     intent, not just a mechanical patch replay.
3. Re-run the test files listed per entry (`python -m unittest <name>`, run
   from the repo root) after merging, before trusting the result.
4. Update this file — add a new entry, or amend an existing one if the merge
   changed how a fix is implemented.

Do not delete an entry just because a merge succeeded; only remove one if the
vendor update makes the local behavior it describes entirely obsolete
(e.g., upstream ships an equivalent or better fix natively — note that in the
entry before deleting it, don't just silently drop it).

## Entries

### 1. Pen lift/lower timing restored (`PenLiftTiming.update()`)

- **Files:** `idraw2_0internal/pen_handling.py`, `idraw2_0internal/idraw2_0_conf.py`
- **Commit:** `23ebc01` ("fix : added pen lift estimation")
- **Vendor state found:** the entire body of `PenLiftTiming.update()` was
  commented out, so `raise_time`/`lower_time` were always left at their
  `__init__` default of `0` — pen lift/lower time never contributed to the
  plot time estimate, regardless of `pen_lifts` count. `idraw2_0_conf.py`
  was also missing the six constants the formula needs
  (`servo_sweep_time`, `servo_move_min`, `servo_move_slope` and their
  narrow-band `nb_servo_*` equivalents).
- **What changed:** uncommented and restored the formula, re-ported from the
  upstream AxiDraw driver (`evil-mad/axidraw`, `axidraw_conf.py` /
  `pen_handling.py`), and added the six missing constants to
  `idraw2_0_conf.py` using AxiDraw's stock defaults as a starting point.
- **Why:** this was silently zeroing out a real, drawing-dependent
  component of the time estimate (see
  `idraw_ui/docs/AI_HANDOFF_PLAN.md` → "Time-estimation refinement" for the
  calibration work this fed into).
- **Known caveat — do not "fix" this without deliberate testing:**
  - These are **AxiDraw's RC-servo defaults**. This iDraw2 machine's pen
    lift is a **stepper motor**, not an RC servo — the underlying physics
    differ, not just the tuning. Treat the six constants as a first
    approximation pending real-hardware calibration.
  - The formula divides by `ad_ref.options.pen_rate_raise` /
    `pen_rate_lower`, expecting a `1-100` scale (upstream default ~50-75).
    This fork's config default is `5000` (see the comment left in
    `idraw2_0_conf.py`), so the sweep-time term is currently ~66x smaller
    than upstream intended — `raise_time`/`lower_time` are effectively
    dominated by the `servo_move_min`/`servo_move_slope` term alone. This
    was left as-is deliberately (not rescaled) since `idraw_ui` never sets
    these options; rescaling the default is a separate decision.
- **If vendor changed this upstream:** compare their new formula against
  the restored one; if they *also* re-enabled it with different constants
  or a different scale convention, prefer the upstream formula but keep the
  stepper-vs-servo caveat and re-derive the `pen_rate_raise`/`pen_rate_lower`
  scale interaction before trusting the result.
- **Tests:** `test_pen_handling.py` (repo root).

### 2. Preview-mode time estimate mirrors the real-mode `-30ms` discount

- **File:** `idraw2_0internal/dripfeed.py`, function `feed_sm()`
- **Commit:** `6e98844` ("fix estimation")
- **Vendor state found:** in real (non-preview) plotting, the `else` branch
  of `feed_sm()` sleeps `move_time - 30ms` for motion sub-commands (via
  `drawcore_motion.doXYMove` + `time.sleep`) — an existing vendor
  optimization/compensation. The `preview` branch above it did not mirror
  this: it always added the full, un-discounted `move_time` to
  `plot_status.stats.pt_estimate`.
- **What changed:** in the `preview` branch, when `move_time > 50` (ms) and
  `ad_ref.options.mode != "manual"`, subtract 30ms before adding to
  `pt_estimate`, matching the real-mode discount's own threshold/condition.
- **Why:** invisible on drawings with few/short motion segments, but
  compounds into a large systematic overestimate on drawings with many
  pen-up hops longer than 50ms (measured down to ~74% estimated-vs-actual
  on the worst case in `idraw_ui/svg_calibration/`). See
  `idraw_ui/docs/AI_HANDOFF_PLAN.md` → "Time-estimation refinement" for the
  before/after calibration numbers.
- **Known caveat:** this is a threshold-gated patch, not a general fix. It
  does not address the (separately documented, unfixed) finding that real
  per-motion-sub-command time is closer to a constant ~20ms floor
  (serial/USB round-trip latency) than to the theoretical `move_time` for
  *short* segments — that would require changes to
  `idraw2_0internal/motion.py::compute_segment()`, not `dripfeed.py`, and
  was deliberately left for a future session.
- **If vendor changed this upstream:** re-check the exact discount value and
  condition in the real-mode `else` branch first (`move_time - 30`,
  `move_time > 50`, `mode != "manual"`) — the preview-mode fix must keep
  mirroring whatever that branch actually does, not the values written here
  if they've since diverged.
- **Tests:** none automated (this path is timing/threshold logic without a
  vendor test harness around `feed_sm()`); validated via the
  `idraw_ui/svg_calibration/` real-hardware runs referenced above.

### 3. Exact resume point via `pause_path_index` (stippling point-loss fix)

- **Files:** `idraw2_0internal/plot_status.py`, `idraw2_0internal/idraw.py`,
  `idraw2_0internal/path_objects.py`
- **Commit:** *(this change — see repo log for the commit this entry ships
  with)*
- **Vendor state found:** Pause/Resume persists `pause_dist` (cumulative
  pen-down distance at pause time) in the PLOB `<plotdata>` block. On
  resume, `DocDigest.crop(distance)` (`path_objects.py`) walks the digest's
  paths in order, treating each whole path as "already plotted" purely by
  accumulating `path.length()` until it reaches `distance`. For a run of
  many near-zero-length paths (stippling dots — each dot is one `PathItem`
  with length ≈0), this walk cannot distinguish "the dot drawn right before
  pause" from "the next dot, never drawn": both leave the accumulated
  distance almost unchanged, so the skip condition keeps matching well past
  the true resume point, silently dropping a run of genuinely un-plotted
  dots with no error or log.
- **What changed:** added a second, exact signal recorded in parallel with
  `pause_dist`:
  - `PlotStats.paths_completed` (`plot_status.py`) — an integer counter,
    incremented once per fully-completed `PathItem` in
    `idraw.py::plot_doc_digest()` (only when the plot wasn't stopped
    partway through that path).
  - Captured into `SVGPlotData.pause_path_index` at pause time
    (`idraw.py::pause_check()`), alongside the existing `pause_dist`.
  - Serialized/deserialized in the PLOB `<plotdata>` block
    (`ResumeStatus.write_to_svg()` / `read_from_svg()` in
    `plot_status.py`) as the optional attribute `pause_path_index`.
  - `DocDigest.crop()` gained a second parameter, `path_index=-1`. When
    `path_index >= 0`, the whole-path skip decision uses an exact integer
    comparison (`path_counter < path_index`) instead of the distance walk.
    `distance` is still used afterward to splice the one path that was
    genuinely mid-flight at pause time — unaffected, and still exact, for
    paths with real length. A path with `length() <= 1e-9` at the splice
    point is left whole instead of spliced (avoids a division by
    ~zero-length segment in `PathItem.crop_by_distance()`).
- **Why:** see `idraw_ui/docs/AI_HANDOFF_PLAN.md` → "Play/Pause reliability
  fixes" for the full user-facing description and the diagnosis process.
- **Backward compatibility:** `pause_path_index` is read as an *optional*
  PLOB attribute — a resume file saved before this field existed (or one
  manually distance-adjusted via the vendor's own `res_adj_in`/`res_adj_mm`
  CLI/API paths, which explicitly reset `pause_path_index = -1` since a
  manual offset invalidates the count) comes back as `-1`, and
  `crop(distance, path_index=-1)` then reproduces the exact previous
  distance-only behavior. No regression for old resume files or the manual
  CLI offset path.
- **If vendor changed this upstream:** `DocDigest.crop()`'s signature
  changed (new optional second parameter) — if the vendor also rewrote
  `crop()`, re-apply the `path_index`-based branch on top of their version
  rather than discarding it; the distance-only branch should stay
  equivalent to whatever their new distance walk does. Also re-check the
  `plot_doc_digest()` call site in `idraw.py` — the
  `self.plot_status.stats.paths_completed += 1` increment must stay
  *after* `plot_polyline()` returns and gated on `not self.plot_status.stopped`,
  or the count will include paths that were actually interrupted.
- **Tests:** `test_path_objects.py`, `test_plot_status.py` (repo root).
  `test_path_objects.py` includes a synthetic reproduction of the bug
  (`test_distance_only_fallback_loses_dots_past_the_true_resume_point`) —
  keep that test even after a merge, it's the regression guard for this
  specific failure mode. Not yet validated on real hardware with an actual
  mid-plot Pause/Resume on a stippling job.

### 4. `pt_estimate` split into pendown/penup motion time (`down_motion_ms`/`up_motion_ms`)

- **Files:** `idraw2_0internal/plot_status.py`, `idraw2_0internal/dripfeed.py`
- **Commit:** *(this change — see repo log for the commit this entry ships
  with)*
- **Vendor state found:** `PlotStats.pt_estimate` (ms) accumulates the
  preview-mode time estimate as a single opaque scalar. `feed_sm()`
  (`dripfeed.py`) adds every SM move's (already `-30ms`-discounted, per
  entry #2) contribution to `pt_estimate` regardless of pen state — even
  though `ad_ref.pen.phys.z_up` (the flag needed to know whether a move is
  pen-up or pen-down) is read one statement later, for the *distance* split
  (`stats.add_dist(z_up, move_dist)` → `up_travel_inch`/`down_travel_inch`).
  So the distance split already existed; the equivalent time split did not.
- **What changed:** in `feed_sm()`'s preview branch, after computing the
  (possibly `-30ms`-discounted) `discounted_time`, add it to
  `stats.up_motion_ms` if `z_up` else `stats.down_motion_ms` — mirroring the
  existing distance split exactly, same flag, same point in the function.
  `PlotStats` gained the two new fields (`__init__`/`reset()`), and
  `report()`'s existing `pt_estimate *= options.copies` multi-copy handling
  was mirrored for the two new fields too, for consistency (idraw_ui does
  not currently exercise multi-copy plotting).
- **Why:** `down_motion_ms + up_motion_ms` is a lossless partition of
  `pt_estimate`'s SM-move contribution (the remaining contributions — pen
  lift/lower time, page/layer delays — are already separately available:
  lift time via `session.pen.heights.times.raise_time`/`.lower_time`, delay
  via `stats.page_delays`/`layer_delays`). idraw_ui's self-calibrating
  estimate (see `idraw_ui/docs/AI_HANDOFF_PLAN.md` → "Time-estimation
  refinement") needs to correct pendown motion time, penup motion time, and
  pen-lift time *independently*, since prior calibration work showed a
  single opaque estimate can't be corrected safely (a whole-run regression
  predicted negative durations for already-accurate short jobs) — different
  drawings are dominated by different components, so each needs its own
  learned correction weight.
- **Known caveat:** this is purely an additional read/split of data the
  vendor already computes — it does not change `pt_estimate`'s value or any
  existing behavior. `down_motion_ms`/`up_motion_ms` are only meaningful in
  preview mode (never incremented during a real plot), matching
  `pt_estimate`'s own existing preview-only semantics.
- **If vendor changed this upstream:** if the vendor rewrote `feed_sm()`'s
  preview branch (e.g. changed the discount logic from entry #2), re-apply
  the `z_up`-gated split on top of whatever the new discounted-time
  computation is — the split must always add the *same* value that goes
  into `pt_estimate`, not the raw undiscounted `move_time`. If the vendor
  added their own down/up split with different field names, prefer theirs
  and update idraw_ui's `idraw2_runtime.py::_extract_metrics()` to read the
  new names (it already reads these defensively via `getattr(..., 0.0)`, so
  it degrades gracefully rather than crashing either way).
- **Tests:** `test_dripfeed.py` (repo root, new) — covers the split by pen
  state, that the discount is applied before splitting, and that the two
  fields sum back to `pt_estimate`'s SM-move total across a mixed sequence
  of moves. `test_plot_status.py` — covers `__init__`/`reset()` defaults.

## Files with no local modifications (as of this writing)

Everything else under `idraw2_0internal/` and `hta/` is the unmodified
vendor import — safe to overwrite wholesale with a fresh vendor copy without
consulting this file.
