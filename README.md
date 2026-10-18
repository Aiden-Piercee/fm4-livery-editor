
# FM4 Livery Tool (alpha)

A free tool for the Forza Motorsport 4 fans who don't have any talent (like me) to create liveries using layers. This tool allows you to drag and drop images that are then baked into the vehicle's texture map and can be applied to the car. It reads your own game files and ships none of them.



## **This tool comes with absolutely no warranty, use your thinking noodle and make sure to  backup any files first that may be modified.** 



**What it does**
- **Liveries:** fit any image onto a car's panels with a live preview, then save it to a garage slot. Import and export `.fm4livery` files to share.
- **Texture edits:** change a car's textures and ship the change as a normal DLC package. Your original files are never touched, and removing the package undoes it.
- **New cars:** save an edit as a brand-new car that appears in the dealership next to the original.
- **3D view:** see the real car body with your design on it.
- **DLC Packager** This approach means your modifies files are completely modular, and do not affect the original games files. Delete the packed DLC - delete the changes. Nice.

## Get it
Download `fm4livery-windoza.zip` from the Actions tab of this repo (latest run, "fm4livery-windows"). Unzip it and double-click **FM4 Livery Tool.exe**. Nothing else needs installing.

Prefer Python? Install Python 3.11+, run `pip install -r requirements.txt`, then `python run_livery.py`.


## Use it
1. Open the tool and point it at your recomp folder (it usually finds it by itself). For texture edits and the 3D view it also needs the extracted game files: the `Media` folder that contains `cars`.
2. Pick a car, add your image or edit its textures, and check the preview.
3. **Livery:** close the game and write it to a garage slot. A backup of your profile is made first.
4. **Texture edit or new car:** press **Save**. For an original car you choose *overwrite the original* (it is backed up, but always keep your own backup too) or *create a unique clone*. Then press **Install** with the game closed.

To undo an install, remove the package from the library and install again. The package is moved to a backup folder, never deleted.

## Good to know
- On normal road cars the body paint is not in the texture you can edit. Edits there show on small badges and the interior (dials, cockpit view). Race cars carry full body art, so they change the most.
- Windows glass can't be painted over.
- Only base-game cars can be cloned for now. A clone also keeps the original car's Damage Plus damage settings if you have that installed.
- Xenia works with texture edits once the tool has installed them, because the install step unpacks the zips Xenia needs. Clones in Xenia are untried.
- If you have a lot of DLC installed, YMMV in terms of whether your changes appear. Test this first.

## Status
Works in the recomp: liveries, texture edits, clones (body, cockpit, dials, audio, damage, dealership thumbnail). Works in Xenia: texture edits. Untested: a second profile, a clean Windows machine, and the console package export (`STFS`), which needs re-signing for a console and is only for modded consoles.
Features, implementations may be broken, YMMV.

## Command line
`fm4livery.exe --root <recomp folder> garage` lists your garage. Other commands: `info`, `make --slot 3 --image logo.png`, `export --slot 3 --out my.fm4livery`, `import --slot 4 --file my.fm4livery`. Run it with no arguments to open the window.

Licence notes for the bundled LZX helper are in `THIRD_PARTY.md`.

<img width="1280" height="720" alt="Clipboard Image (4)" src="https://github.com/user-attachments/assets/915680d5-d9cb-46e0-a400-fce30498db92" />
<img width="1280" height="720" alt="Clipboard Image (5)" src="https://github.com/user-attachments/assets/fc74c672-6602-442d-9de9-84ee8e0255e2" />
<img width="1280" height="720" alt="Clipboard Image (6)" src="https://github.com/user-attachments/assets/68acd9ae-f15d-4757-a3e1-b7c11f0f4763" />
<img width="1280" height="720" alt="Clipboard Image (7)" src="https://github.com/user-attachments/assets/0fc21cec-51fa-45fd-bf1c-c85c759a8f77" />
