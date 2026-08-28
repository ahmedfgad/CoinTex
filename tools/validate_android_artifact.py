#!/usr/bin/env python3
"""Validate native ABI and 16 KB ELF alignment in an Android APK or AAB."""

from __future__ import annotations

import argparse
import struct
import zipfile
from pathlib import Path


PT_LOAD = 1
REQUIRED_ALIGNMENT = 16 * 1024
SIXTY_FOUR_BIT_ABIS = {"arm64-v8a", "x86_64"}
P4A_DATA_LIBRARIES = {"libpybundle.so"}


def elf_load_alignments(data: bytes) -> tuple[int, list[int]]:
    """Return (ELF class in bits, PT_LOAD alignments) from a shared library."""
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    elf_class = data[4]
    byte_order = data[5]
    if elf_class not in (1, 2) or byte_order not in (1, 2):
        raise ValueError("unsupported ELF class or byte order")
    endian = "<" if byte_order == 1 else ">"
    if elf_class == 1:
        phoff = struct.unpack_from(endian + "I", data, 28)[0]
        phentsize = struct.unpack_from(endian + "H", data, 42)[0]
        phnum = struct.unpack_from(endian + "H", data, 44)[0]
        align_offset = 28
        align_format = "I"
        bits = 32
    else:
        phoff = struct.unpack_from(endian + "Q", data, 32)[0]
        phentsize = struct.unpack_from(endian + "H", data, 54)[0]
        phnum = struct.unpack_from(endian + "H", data, 56)[0]
        align_offset = 48
        align_format = "Q"
        bits = 64
    if phentsize <= align_offset or phnum > 4096:
        raise ValueError("invalid ELF program-header table")

    alignments = []
    for index in range(phnum):
        offset = phoff + index * phentsize
        if offset + phentsize > len(data):
            raise ValueError("truncated ELF program-header table")
        segment_type = struct.unpack_from(endian + "I", data, offset)[0]
        if segment_type == PT_LOAD:
            alignments.append(struct.unpack_from(
                endian + align_format, data, offset + align_offset)[0])
    if not alignments:
        raise ValueError("ELF file has no loadable segments")
    return bits, alignments


def native_entry_abi(name: str) -> str | None:
    parts = name.split("/")
    try:
        lib_index = parts.index("lib")
    except ValueError:
        return None
    if lib_index + 2 >= len(parts) or not name.endswith(".so"):
        return None
    return parts[lib_index + 1]


def validate_artifact(path: Path, expected_abis: set[str]) -> tuple[int, set[str]]:
    checked = 0
    found_abis: set[str] = set()
    failures = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            abi = native_entry_abi(info.filename)
            if abi is None:
                continue
            found_abis.add(abi)
            data = archive.read(info)
            if Path(info.filename).name in P4A_DATA_LIBRARIES and not data.startswith(b"\x7fELF"):
                # python-for-android intentionally gives its packaged Python
                # data bundle a .so name so Android extracts it with the other
                # ABI resources. It is not a loadable native library.
                continue
            try:
                bits, alignments = elf_load_alignments(data)
            except (OSError, ValueError) as error:
                failures.append(f"{info.filename}: {error}")
                continue
            checked += 1
            if abi in SIXTY_FOUR_BIT_ABIS:
                if bits != 64:
                    failures.append(f"{info.filename}: expected a 64-bit ELF")
                bad = [value for value in alignments if value < REQUIRED_ALIGNMENT]
                if bad:
                    rendered = ", ".join(str(value) for value in bad)
                    failures.append(
                        f"{info.filename}: PT_LOAD alignment below 16384 ({rendered})")

    missing = expected_abis - found_abis
    if missing:
        failures.append("missing native ABI(s): " + ", ".join(sorted(missing)))
    if not checked:
        failures.append("artifact contains no native shared libraries")
    if failures:
        raise SystemExit("Android artifact validation failed:\n- " + "\n- ".join(failures))
    return checked, found_abis


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--expected-abis", default="arm64-v8a,armeabi-v7a")
    args = parser.parse_args()
    expected = {item.strip() for item in args.expected_abis.split(",") if item.strip()}
    checked, found = validate_artifact(args.artifact, expected)
    print("Validated {} native libraries in {} (ABIs: {}); 64-bit PT_LOAD "
          "alignment is 16 KB compatible.".format(
              checked, args.artifact, ", ".join(sorted(found))))


if __name__ == "__main__":
    main()
