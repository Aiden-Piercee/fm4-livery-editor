# Third-party components

- **libmspack** (`lzxd.c`, LGPL-2.1) by Stuart Caie - used only inside the small `fzlzx` helper (`native/fzlzx.c`) that reads Xbox "method 21" zip entries.
  It is built as a separate shared library (`fzlzx.dll` / `libfzlzx.so`) and loaded dynamically; source: https://github.com/kyz/libmspack (pinned commit in `ci/build-windows.yml`).
- **cryptography** (Apache-2.0 / BSD), **NumPy** (BSD), **Pillow** (HPND) - installed from PyPI at build time.
- **PyInstaller** (GPL-2.0 with the bootloader exception) - used to build `fm4livery.exe`.

fm4livery contains no game files and no game keys; it reads them from the user's own installation at run time.
