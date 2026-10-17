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

## Decals and texture sheet (baked-livery cars)

Cars with a baked race-livery texture (`nodamage.xds`) can be decorated in two ways. Both end up in the same texture.

* **Texture sheet tab** - the car's texture atlas laid flat with UV outlines. Drop or add PNG/JPG/SVG images, move/scale/rotate them, or load a sheet you painted elsewhere ("Save atlas + UV template" exports the atlas and the outlines for that).
* **3D view** - lock to Left / Right / Front / Rear / Top (orthographic) and drag and drop images or SVGs onto the car. They are baked through the car's UV map, hidden surfaces excluded, onto every visible panel. "Send 3D decals to the editor" instead fits them into garage `.liv` layers (approximate).

"Build texture files" writes the edited `nodamage.xds` / `nodamage_lod0.xds` (and a stored-entry copy of the car zip) into `fm4livery_exports/textures/<car>/`. Nothing is installed into the game; copy files in yourself with the game closed. Mip levels above 16 texels are regenerated; the tail tile is kept from the original.

## Two sections
- **In-game livery:** Image to livery, Import / export, Editor, Backups (the game's own livery layers).
- **Texture studio:** Texture sheet and 3D decals (drag and drop onto the car's baked texture), plus a **Library**. *Save to library* keeps each edit per car; choose the active edit per car (or original) and *Apply to game* builds ONE combined pack from them (older per-car packs are absorbed and moved out). *Export STFS* wraps that pack for Xenia / modded consoles (stale signature; needs a retail FM4 DLC package as template). Nothing in the car zips is ever changed; originals are copied once to `fm4livery_backups/originals`.
