"""Import KayKit-Bundle .gltf assets into godot-3d/assets/.

Single source of truth for which `.gltf` lives where: ``maps/kinds.json``.
Each kind's ``kaykit_source`` field points at a path inside the unzipped
KayKit bundle (e.g. ``Furniture/desk.fbx``); the bundle ships pre-converted
``.gltf`` siblings, so we just copy those plus their referenced ``.bin`` and
texture ``.png`` into ``godot-3d/assets/{furniture,kitchen,server}/``.

The bundle itself is NOT in the repo (~140 MB). Sven keeps it locally.
Re-running on a clean checkout reproduces every staged asset. Idempotent:
copy is skipped if checksums already match.

Usage::

    KAYKIT_BUNDLE=/path/to/KayKit_Bits_Bundle1_1.1 \\
        uv run python scripts/import_kaykit_assets.py [--dry-run] [--force]

After running:
- ``godot-3d/assets/`` is populated with the meshes referenced by ``kinds.json``
- ``maps/kinds.json`` has ``godot_asset`` filled in for every kind that has a
  ``kaykit_source``
- A ``godot-3d/assets/IMPORT_MANIFEST.txt`` records which bundle files seeded
  which staged file (audit trail for the CC0 licenses).

If you add a new kind to ``kinds.json`` with a ``kaykit_source``, just re-run
the script — it picks up the new entry, copies the asset, sets the
``godot_asset`` path. Designers do NOT need Blender or FBX-conversion
tooling; the bundle's pre-shipped ``.gltf`` is what we vendor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KINDS_PATH = REPO_ROOT / "maps" / "kinds.json"
ASSETS_ROOT = REPO_ROOT / "godot-3d" / "assets"
MANIFEST_PATH = ASSETS_ROOT / "IMPORT_MANIFEST.txt"

# Maps the first segment of `kaykit_source` (e.g. "Furniture/desk.fbx") to
# the bundle subdirectory holding pre-converted gltf files plus the destination
# subdir under godot-3d/assets/. One destination per source-pack so each
# pack's shared texture only gets vendored once.
PACK_LAYOUT = {
    "Furniture": {
        "bundle_dir": "Furniture Bits/Assets/gltf",
        "dest_dir": "furniture",
    },
    "Restaurant": {
        "bundle_dir": "Restaurant Bits/Assets/gltf",
        "dest_dir": "kitchen",
    },
    "Space Base": {
        "bundle_dir": "Space Base Bits/Assets/gltf",
        "dest_dir": "server",
    },
}


@dataclass
class CopyJob:
    kind: str
    bundle_gltf: Path
    dest_dir: Path
    dest_gltf: Path
    siblings: list[tuple[Path, Path]]  # (src, dst) for .bin + textures
    godot_asset: str  # res://assets/<dest_subdir>/<file>.gltf

    def all_pairs(self) -> list[tuple[Path, Path]]:
        return [(self.bundle_gltf, self.dest_gltf), *self.siblings]


def _resolve_bundle_root() -> Path:
    bundle = os.environ.get("KAYKIT_BUNDLE")
    if not bundle:
        sys.exit(
            "ERROR: set KAYKIT_BUNDLE to the unzipped bundle path "
            "(should contain 'Furniture Bits/', 'Restaurant Bits/', etc).\n"
            "Bundle download: https://kaylousberg.itch.io/bits-bundle (CC0)."
        )
    root = Path(bundle).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"ERROR: KAYKIT_BUNDLE='{bundle}' is not a directory.")
    sentinel = root / "License.txt"
    if not sentinel.is_file():
        sys.exit(
            f"ERROR: KAYKIT_BUNDLE='{root}' does not look like a KayKit bundle "
            "(no License.txt found at root)."
        )
    return root


def _split_source(kaykit_source: str) -> tuple[str, str]:
    """``"Furniture/desk.fbx"`` -> ``("Furniture", "desk")`` (basename, no ext)."""
    pack, _, file = kaykit_source.partition("/")
    if not pack or not file:
        raise ValueError(f"unexpected kaykit_source: {kaykit_source!r}")
    stem = Path(file).stem
    return pack, stem


def _gltf_referenced_uris(gltf_path: Path) -> list[str]:
    """All relative URIs the .gltf needs as siblings (.bin + textures)."""
    data = json.loads(gltf_path.read_text())
    uris: list[str] = []
    for buf in data.get("buffers", []):
        uri = buf.get("uri")
        if uri:
            uris.append(uri)
    for img in data.get("images", []):
        uri = img.get("uri")
        if uri:
            uris.append(uri)
    return uris


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_jobs(bundle_root: Path, kinds: dict) -> list[CopyJob]:
    jobs: list[CopyJob] = []
    for kind, spec in kinds.items():
        if kind.startswith("_"):
            continue
        source = spec.get("kaykit_source")
        if not source:
            continue
        pack, stem = _split_source(source)
        layout = PACK_LAYOUT.get(pack)
        if layout is None:
            raise ValueError(
                f"kind={kind!r} has unknown source pack {pack!r} (kaykit_source={source!r})"
            )
        bundle_gltf = bundle_root / layout["bundle_dir"] / f"{stem}.gltf"
        if not bundle_gltf.is_file():
            raise FileNotFoundError(f"kind={kind!r} expects {bundle_gltf} but it does not exist")

        dest_dir = ASSETS_ROOT / layout["dest_dir"]
        dest_gltf = dest_dir / f"{stem}.gltf"

        # Resolve every URI the .gltf depends on. Textures live in the pack's
        # ../textures/ folder, while .bin lives next to the .gltf. The runtime
        # loader (Godot + three.js) expects everything as siblings of the
        # .gltf, so we co-locate them when copying.
        pack_root = bundle_root / Path(layout["bundle_dir"]).parts[0]
        textures_dir = pack_root / "Assets" / "textures"
        siblings: list[tuple[Path, Path]] = []
        for uri in _gltf_referenced_uris(bundle_gltf):
            candidates = [bundle_gltf.parent / uri, textures_dir / Path(uri).name]
            src_sibling = next((c for c in candidates if c.is_file()), None)
            if src_sibling is None:
                raise FileNotFoundError(
                    f"kind={kind!r}: gltf references {uri!r}, not found in any of: "
                    + ", ".join(str(c) for c in candidates)
                )
            siblings.append((src_sibling, dest_dir / Path(uri).name))

        jobs.append(
            CopyJob(
                kind=kind,
                bundle_gltf=bundle_gltf,
                dest_dir=dest_dir,
                dest_gltf=dest_gltf,
                siblings=siblings,
                godot_asset=f"res://assets/{layout['dest_dir']}/{stem}.gltf",
            )
        )
    return jobs


def _execute(jobs: list[CopyJob], *, dry_run: bool, force: bool) -> int:
    """Returns count of files actually written (for manifest summary)."""
    written = 0
    for job in jobs:
        job.dest_dir.mkdir(parents=True, exist_ok=True)
        for src, dst in job.all_pairs():
            if dst.exists() and not force and _file_sha256(src) == _file_sha256(dst):
                continue  # identical, skip
            print(f"  {src.relative_to(src.anchor)}  ->  {dst.relative_to(REPO_ROOT)}")
            if not dry_run:
                shutil.copy2(src, dst)
                written += 1
    return written


def _patch_kinds_json(jobs: list[CopyJob], *, dry_run: bool) -> int:
    """Surgically replace ``"godot_asset": <old>`` in each kind block.

    json.dump would lose the existing inter-block whitespace, so we rewrite
    just the one line inside each kind's object literal.
    """
    text = KINDS_PATH.read_text()
    patches = 0
    for job in jobs:
        # match the kind's own block: from '"<kind>": {' to first matching '}',
        # then within that block swap the godot_asset value.
        marker = f'"{job.kind}": {{'
        block_start = text.find(marker)
        if block_start < 0:
            raise RuntimeError(f"kinds.json: block for kind={job.kind!r} not found")
        # find first '}' at the same nesting level (kinds.json uses 2-space
        # indented blocks; the closing brace is on its own line at indent 2).
        block_end = text.find("\n  }", block_start)
        if block_end < 0:
            raise RuntimeError(f"kinds.json: could not locate end of {job.kind!r} block")
        block_text = text[block_start:block_end]

        # replace `"godot_asset": <whatever>,` (could be `null` or an existing path)
        import re

        new_block, n = re.subn(
            r'"godot_asset"\s*:\s*(?:null|"[^"]*")',
            f'"godot_asset": "{job.godot_asset}"',
            block_text,
            count=1,
        )
        if n != 1:
            raise RuntimeError(
                f"kinds.json: expected 1 godot_asset line in {job.kind!r} block, found {n}"
            )
        if new_block == block_text:
            continue
        text = text[:block_start] + new_block + text[block_end:]
        patches += 1

    if patches and not dry_run:
        KINDS_PATH.write_text(text)
    return patches


def _write_manifest(bundle_root: Path, jobs: list[CopyJob]) -> None:
    lines = [
        "# IMPORT_MANIFEST",
        "#",
        "# Auto-generated by scripts/import_kaykit_assets.py — do NOT hand-edit.",
        "# Lists every staged file in godot-3d/assets/ alongside the KayKit-bundle",
        "# source it was copied from, with a SHA256 checksum so we can prove",
        "# nothing has drifted from the upstream CC0 release.",
        "#",
        f"# Bundle root: {bundle_root}",
        f"# Generated for {len(jobs)} kinds.",
        "",
    ]
    seen: set[Path] = set()
    for job in jobs:
        for src, dst in job.all_pairs():
            if dst in seen:
                continue
            seen.add(dst)
            rel_dst = dst.relative_to(REPO_ROOT)
            checksum = _file_sha256(dst) if dst.is_file() else "<missing>"
            try:
                rel_src = src.relative_to(bundle_root)
            except ValueError:
                rel_src = src
            lines.append(f"{rel_dst}  sha256={checksum}  <-  {rel_src}")
    MANIFEST_PATH.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print plan without copying files or editing kinds.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite even if dest checksum already matches source",
    )
    args = parser.parse_args(argv)

    bundle_root = _resolve_bundle_root()
    kinds = json.loads(KINDS_PATH.read_text())
    jobs = _build_jobs(bundle_root, kinds)
    print(f"[import_kaykit_assets] bundle: {bundle_root}")
    print(f"[import_kaykit_assets] {len(jobs)} kinds with kaykit_source")

    written = _execute(jobs, dry_run=args.dry_run, force=args.force)
    print(f"[import_kaykit_assets] wrote {written} file(s)")

    patches = _patch_kinds_json(jobs, dry_run=args.dry_run)
    print(f"[import_kaykit_assets] patched godot_asset for {patches} kind(s) in kinds.json")

    if not args.dry_run:
        _write_manifest(bundle_root, jobs)
        print(f"[import_kaykit_assets] manifest -> {MANIFEST_PATH.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
