#!/usr/bin/env python3
"""Recover this installed build's archive key by reading its static callback.

No process injection, game execution, or credentials. The build hash and opcode
checks deliberately reject future binaries until their callback is reviewed.
The caller must validate the result by mounting the original archives.
"""
import argparse
import hashlib
import pathlib
import struct

BUILD_SHA256 = '619e4753e2f68c721764a19afe61b01daee723beaa946ef94ec6bb4e0c7c5747'
CALLBACK_LEA = 0x890D375
WRAPPER_XOR = 0x4B1EC82


def recover(executable: pathlib.Path) -> bytes:
    data = executable.read_bytes()
    if hashlib.sha256(data).hexdigest() != BUILD_SHA256:
        raise ValueError('Unrecognized game build; inspect its key callback before extracting')
    if data[CALLBACK_LEA:CALLBACK_LEA + 3] != bytes.fromhex('4c8d05'):
        raise ValueError('Archive-key callback signature mismatch')
    if data[WRAPPER_XOR:WRAPPER_XOR + 4] != bytes.fromhex('80730a2f'):
        raise ValueError('Archive-key delegate wrapper signature mismatch')
    pe = struct.unpack_from('<I', data, 60)[0]
    count = struct.unpack_from('<H', data, pe + 6)[0]
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    sections = []
    for i in range(count):
        h = pe + 24 + optional_size + 40 * i
        virtual_size, rva, size, offset = struct.unpack_from('<IIII', data, h + 8)
        sections.append((rva, virtual_size, size, offset))
    text = next(s for s in sections if s[3] <= CALLBACK_LEA < s[3] + s[2])
    instruction_rva = CALLBACK_LEA - text[3] + text[0]
    target = instruction_rva + 7 + struct.unpack_from('<i', data, CALLBACK_LEA + 3)[0]
    section = next(s for s in sections if s[0] <= target < s[0] + s[2])
    offset = target - section[0] + section[3]
    key = bytearray()
    for (word,) in struct.iter_unpack('<Q', data[offset:offset + 32]):
        # Two ROL64 by 0x24 in the callback are ROL64 by 8.
        key.extend((((word << 8) | (word >> 56)) & ((1 << 64) - 1)).to_bytes(8, 'little'))
    key[10] ^= 0x2F  # Executed by the bound delegate after the callback.
    return bytes(key)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    key = recover(args.executable)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(key.hex())
    args.output.chmod(0o600)
    print('Recovered local archive key. Archive validation is still required.')
