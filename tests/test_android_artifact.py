import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.validate_android_artifact import elf_load_alignments, validate_artifact


def elf64_with_alignment(alignment):
    data = bytearray(120)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<Q", data, 32, 64)  # program-header table offset
    struct.pack_into("<H", data, 54, 56)  # program-header entry size
    struct.pack_into("<H", data, 56, 1)   # one entry
    struct.pack_into("<I", data, 64, 1)   # PT_LOAD
    struct.pack_into("<Q", data, 64 + 48, alignment)
    return bytes(data)


class AndroidArtifactTests(unittest.TestCase):
    def test_elf_program_alignment_parser(self):
        bits, alignments = elf_load_alignments(elf64_with_alignment(16384))
        self.assertEqual(bits, 64)
        self.assertEqual(alignments, [16384])

    def test_arm64_artifact_requires_16kb_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            good = Path(directory) / "good.apk"
            with zipfile.ZipFile(good, "w") as archive:
                archive.writestr("lib/arm64-v8a/libmain.so",
                                 elf64_with_alignment(16384))
            checked, abis = validate_artifact(good, {"arm64-v8a"})
            self.assertEqual(checked, 1)
            self.assertEqual(abis, {"arm64-v8a"})

            bad = Path(directory) / "bad.apk"
            with zipfile.ZipFile(bad, "w") as archive:
                archive.writestr("lib/arm64-v8a/libmain.so",
                                 elf64_with_alignment(4096))
            with self.assertRaises(SystemExit):
                validate_artifact(bad, {"arm64-v8a"})


if __name__ == "__main__":
    unittest.main()
