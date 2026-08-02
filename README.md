# idraw2_internal

Standalone repository for iDraw2 internal plotting modules extracted from the Inkscape extension bundle.

## Scope

This repository currently contains:
- `idraw2_0internal/` (core plotting pipeline)
- `hta/` minimal wrappers (`py_api.py`, `idraw2_plot_utils_import.py`, `__init__.py`)

Excluded on purpose:
- bundled third-party vendor dependencies from `idraw_deps/`
- `__pycache__` and runtime artifacts

## Source provenance

Initial import source:
- `C:\Users\cflou\AppData\Roaming\inkscape\extensions\idraw_deps\idraw2_0internal`
- selected files from `...\idraw_deps\hta`

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
3. Re-run import smoke tests and update this README with version notes.

## Quick smoke check

```powershell
python -c "import idraw2_0internal.idraw as m; print(m.__version__)"
```
