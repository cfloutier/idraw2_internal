# idraw2_internal

Standalone repository for iDraw2 internal plotting modules extracted from the Inkscape extension bundle.

## Scope

This repository currently contains:

- `idraw2_0internal/` (core plotting pipeline used for plot, preview, pause, and resume)
- `hta/` wrappers and helper modules from the extension layer

Excluded on purpose:

- bundled third-party vendor dependencies from `idraw_deps/`
- `__pycache__` and runtime artifacts

## Architecture notes

### What is HTA

`hta` refers to the historical extension helper layer (including Hershey Text Advanced wrappers
and related utility modules) that lives around the core plotting engine.

In this repository, `hta` is kept to preserve import compatibility and access to extension-side
helpers (for example merge helpers, text wrappers, and import bridges).

### What HTA contains

Typical content includes:

- API wrappers (for example `hta/py_api.py`)
- Hershey/text related modules (`hershey_advanced.py`, `hershey_conf.py`, options)
- merge and utility scripts (`idraw2_merge.py`, `axidraw_merge.py`, etc.)
- assets used by these wrappers (`svg_fonts/`, `inx_images/`)

### What is the core runtime path

The primary plotting runtime remains `idraw2_0internal`.

This is where the key behaviors live:

- SVG parsing and digest pipeline
- path ordering and clipping
- motion command generation and plot execution
- pause and resume management
- progress and timing status tracking

For downstream applications such as `idraw_ui`, the recommended approach is to build a dedicated
adapter/facade that targets `idraw2_0internal` first, while keeping `hta` available as a
compatibility and utility layer.

## Source provenance

Initial import source:

- `C:\Users\cflou\AppData\Roaming\inkscape\extensions\idraw_deps\idraw2_0internal`
- `C:\Users\cflou\AppData\Roaming\inkscape\extensions\idraw_deps\hta`

## Licensing

Source files keep their original headers. Several files state GPL terms (v2 or later).
Use and redistribution of this repository must follow those terms.

## Install (editable)

```powershell
pip install -e .
```

## Sync policy with vendor updates

Recommended update process:

1. Import upstream changes from the Inkscape extension source tree.
2. Keep changes in isolated commits:
   - `upstream import: <version/date>`
   - `local adaptation: <topic>`
3. Before merging, read `docs/LOCAL_MODIFICATIONS.md` — it lists every local
   behavioral change made on top of the vendor source (file, what changed,
   why, and what to check when re-merging). Re-apply or re-derive each entry
   against the new vendor code, then re-run its listed tests.
4. Re-run import smoke tests and update this README with version notes.

See `docs/LOCAL_MODIFICATIONS.md` for the current list of local changes.

## Quick smoke check

```powershell
python -c "import idraw2_0internal.idraw as m; print(m.__version__)"
```
