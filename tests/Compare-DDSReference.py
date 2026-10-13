"""Compare exported PNG pixels against Pillow's independent DDS decoder."""
import argparse
import hashlib
import json
from pathlib import Path
import PIL
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument("manifest")
parser.add_argument("output")
args = parser.parse_args()
records = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
results = []
for record in records:
    with Image.open(record["SourcePath"]) as original:
        reference = original.convert("RGBA")
        expected = reference.tobytes()
    with Image.open(record["PngPath"]) as exported:
        actual = exported.convert("RGBA")
        pixels = actual.tobytes()
    if actual.size != reference.size or pixels != expected:
        raise AssertionError(f"DDS/PNG pixel mismatch: {record['SourcePath']}")
    digest = hashlib.sha256(pixels).hexdigest().upper()
    if digest != record["RgbaSHA256"]:
        raise AssertionError(f"PNG round-trip changed RGBA bytes: {record['SourcePath']}")
    results.append({"SourcePath": record["SourcePath"], "RgbaSHA256": digest})
with Path(args.output).open("x", encoding="utf-8") as output:
    json.dump({"PillowVersion": PIL.__version__, "ExactMatches": len(results), "Results": results}, output, indent=2)
print(f"Pillow {PIL.__version__}: {len(results)} exact RGBA comparisons passed.")
