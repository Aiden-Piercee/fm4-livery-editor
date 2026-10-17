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
No Python on the machine? Use the Windows download below (`FM4 Livery Tool.exe`): it needs nothing installed.
Run `python run_livery.py` (or double-click `FM4 Livery Tool.exe` from the Windows build) with no arguments. It opens a window (pywebview / Windows' built-in WebView2) and falls back to your browser if the window can't open.
It finds your game folder and profile, lists your garage, fits an image onto the chosen panels with a live preview, writes the livery, and handles import / export and backups. Everything runs locally on 127.0.0.1.
If your game isn't found, type or browse to the folder that contains `default.pe` and your profile.

## Standalone Windows download (no Python needed)
The repo builds a single `fm4livery.exe` for you with GitHub Actions: push this repo to GitHub (the workflow is already at `.github/workflows/build-windows.yml` and runs on every push to main), then open **Actions -> Build Windows package** and open the latest run,
then download the `fm4livery-windows` artifact (a zip with `fm4livery.exe`, this README and the licence notes). Tagging a release (`v*`) runs the same build.
`FM4 Livery Tool.exe` opens the GUI (no console window). `fm4livery.exe` is the command-line version; run it from a command prompt, e.g. `fm4livery.exe --root "C:\path\to\your\recomp" garage`. Double-clicking shows the usage.

The LZX helper (`native/fzlzx.c`) is built from libmspack in the same workflow; see THIRD_PARTY.md. It was checked byte-for-byte against the earlier Linux helper on every compressed file of a car zip.

### 3D view

The **3D view** tab shows the real body of the selected car (read from your own car zip at run time, nothing is bundled) in a CAD-style viewer: orbit, pan, zoom, preset views (iso/front/rear/left/right/top), perspective or orthographic, shaded / edges / wireframe, grid, axis gizmo, overall dimensions and a parts list. Your latest preview is projected onto the paintable body panels. The placement is fitted automatically to the car's livery masks and is approximate; the sliders nudge it. Windows glass shows as plain glass because the game cannot paint over it.

## Texture packs, new cars and install targets
Beyond liveries, the **Library** tab edits a car's textures and ships them as a normal DLC package, so nothing in the game files is touched and undo is just removing the package.

- **Override pack (edit a car's texture).** Saving an edit of an original car asks: *overwrite the original* (the original is backed up first, but always keep your own backup) or *create a unique clone*. Edits to an original are written as a high-priority override zip (`Tex<CAR>_pri_27300.zip`, mounted on that car's folder) inside the package, so the car's own zip is never modified. Uninstall = move the package folder and its `.header` out of the game (the tool parks them in a backup folder, never deletes).
- **Clone as new car.** Tick *as new car* (or choose *unique clone* in the save dialog) to add a separate dealership entry: new database rows (a free car id is picked by scanning installed packs), its own name strings, and the donor's files copied under the new media name. The original car is untouched. The clone also inherits the donor's Damage Plus damage tuning, if you have it installed.
- **What an edit can show.** On plain road cars the body paint is not in `nodamage.xds` (only badges, interior bits and brake tiles are), so a visible road-car edit belongs in the interior atlas (dials, cockpit view); baked race cars carry full body art in the atlas.
- **Installing.** *Install* copies the package into the recomp's `4D530910\00000002` folder (with its header) and also unpacks every zip beside itself (`<name>_pri_NN\`), because **Xenia only reads those extracted folders and never opens the zips**; the recomp reads the zips. Xenia also has a stock limit of 37 content entries, and every stray folder or file in `00000002` (backup folders, `_to_delete`, archives) uses a slot - keep that folder to real packages and park the rest elsewhere. Leftover `.bak` files in a pack's `DLCZips` are probed on every file lookup; remove them.
- **STFS export** wraps a package for a console. The tool rebuilds the file system and hashes and checks every file reads back byte-identical, but the console signature cannot be re-created, so it is left stale: Xenia and the recomp ignore it, a retail console rejects it, and a modded console needs it re-signed with your own tools. Hardware use is untested.

Status: override packs and clones confirmed in the recomp (body, cockpit, dials, audio, damage, dealership thumbnail). Override packs also confirmed in Xenia (Mazda 2 cockpit dials) once the zips are unpacked; clones in Xenia are untried. STFS on hardware is untested.
