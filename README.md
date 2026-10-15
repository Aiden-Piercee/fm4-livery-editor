# fm4livery (alpha 0.1)
Standalone livery tool for the Forza Motorsport 4 PC recompilation. Reads your own game files; ships no keys or game data.

    python run_livery.py --root <recomp folder> info
    python run_livery.py --root <recomp folder> garage
    python run_livery.py --root <recomp folder> make --slot 3 --image logo.png [--panels left,right] [--shapes 450]
    python run_livery.py --root <recomp folder> export --slot 3 --out my.fm4livery
    python run_livery.py --root <recomp folder> import --slot 4 --file my.fm4livery

Needs Python 3.11+, `cryptography`, `numpy`, `pillow`. Close the game before commands that assign a slot (they rewrite PlayerDatabase; a backup is made first).
Replacing an existing .liv works while the game runs. Panels checked in game (Falcon): left, right, front, rear and roof/hood all paint, with +X = screen-right and +Y = up as seen from outside (roof: view it from above with the car facing left). The wing is experimental: it only paints about 60% of the blade, from the car-left end; vinyl cannot cover glass. Console profiles (untested): the tool edits the files, you re-sign the package yourself with your usual save signer.
Status: untested on a second profile or on a clean Windows machine. LZX helper: libfzlzx.so (Linux) - Windows DLL still to build.

## Graphical tool
Run `python run_livery.py` (or double-click `FM4 Livery Tool.exe` from the Windows build) with no arguments. It opens a window (pywebview / Windows' built-in WebView2) and falls back to your browser if the window can't open.
It finds your game folder and profile, lists your garage, fits an image onto the chosen panels with a live preview, writes the livery, and handles import / export and backups. Everything runs locally on 127.0.0.1.
If your game isn't found, type or browse to the folder that contains `default.pe` and your profile.

## Standalone Windows download (no Python needed)
The repo builds a single `fm4livery.exe` for you with GitHub Actions: push this repo to GitHub, move `ci/build-windows.yml` to `.github/workflows/build-windows.yml` (tools that edit your repo for you may not be allowed to write there), then open **Actions -> Build Windows package -> Run workflow**,
then download the `fm4livery-windows` artifact (a zip with `fm4livery.exe`, this README and the licence notes). Tagging a release (`v*`) runs the same build.
`FM4 Livery Tool.exe` opens the GUI (no console window). `fm4livery.exe` is the command-line version; run it from a command prompt, e.g. `fm4livery.exe --root "C:\path\to\your\recomp" garage`. Double-clicking shows the usage.

The LZX helper (`native/fzlzx.c`) is built from libmspack in the same workflow; see THIRD_PARTY.md. It was checked byte-for-byte against the earlier Linux helper on every compressed file of a car zip.

### 3D view

The **3D view** tab shows the real body of the selected car (read from your own car zip at run time, nothing is bundled) in a CAD-style viewer: orbit, pan, zoom, preset views (iso/front/rear/left/right/top), perspective or orthographic, shaded / edges / wireframe, grid, axis gizmo, overall dimensions and a parts list. Your latest preview is projected onto the paintable body panels. The placement is fitted automatically to the car's livery masks and is approximate; the sliders nudge it. Windows glass shows as plain glass because the game cannot paint over it.
