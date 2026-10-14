# empty livery design (no layers); creator id is zeroed here and patched by design.new_design()
import base64, zlib
EMPTY = zlib.decompress(base64.b64decode('eNpLLsopY2BgYGaAA9YWRhCVU1ZUCaT4EBIMfTlllekwjn0DAzZANWFnE6zCTlsYiAKMjP8F1Pzpo6ShoQG/Euo4lwhfAwAh4hTy'))
CREATOR_OFFSET = 33
