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
