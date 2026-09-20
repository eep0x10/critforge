"""Bounded structural validation of STL and GLB downloads, not printability."""
import json
import math
from pathlib import Path
import struct
from common import WorkflowError


def fail():
    raise WorkflowError('Corrupt or unsupported asset structure; preserve original and retry download if needed.')


def validate_stl(path):
    size = path.stat().st_size
    low = [math.inf, math.inf, math.inf]
    high = [-math.inf, -math.inf, -math.inf]

    def include(vertex):
        for index, value in enumerate(vertex):
            low[index] = min(low[index], value)
            high[index] = max(high[index], value)

    with path.open('rb') as stream:
        header = stream.read(84)
        if len(header) == 84:
            count = struct.unpack('<I', header[80:])[0]
            if count and size == 84 + count * 50:
                while block := stream.read(50 * 8192):
                    for triangle in struct.iter_unpack('<12fH', block):
                        if not all(math.isfinite(x) for x in triangle[:12]):
                            fail()
                        for offset in (3, 6, 9):
                            include(triangle[offset:offset + 3])
                return {'format': 'binary-stl', 'triangles': count,
                        'bounds_units': [low, high],
                        'dimensions_units': [high[i] - low[i] for i in range(3)]}
    # Parse ASCII grammar instead of accepting any file beginning with "solid".
    with path.open('r', encoding='ascii') as stream:
        def line():
            while True:
                value = stream.readline(4097)
                if len(value) > 4096:
                    fail()
                if not value or value.strip():
                    return value.strip().split()
        def vector(tokens, prefix):
            if tokens[:len(prefix)] != prefix or len(tokens) != len(prefix) + 3:
                fail()
            values = [float(v) for v in tokens[len(prefix):]]
            if not all(math.isfinite(v) for v in values):
                fail()
            return values
        first = line()
        if not first or first[0] != 'solid':
            fail()
        count = 0
        while True:
            tokens = line()
            if tokens and tokens[0] == 'endsolid':
                if not count or line():
                    fail()
                return {'format': 'ascii-stl', 'triangles': count,
                        'bounds_units': [low, high],
                        'dimensions_units': [high[i] - low[i] for i in range(3)]}
            vector(tokens, ['facet', 'normal'])
            if line() != ['outer', 'loop']:
                fail()
            for _ in range(3):
                include(vector(line(), ['vertex']))
            if line() != ['endloop'] or line() != ['endfacet']:
                fail()
            count += 1


def validate_glb(path):
    size = path.stat().st_size
    with path.open('rb') as stream:
        head = stream.read(12)
        if len(head) != 12:
            fail()
        magic, version, length = struct.unpack('<4sII', head)
        if magic != b'glTF' or version != 2 or length != size:
            fail()
        kinds = []
        while stream.tell() < size:
            chunk = stream.read(8)
            if len(chunk) != 8:
                fail()
            length, kind = struct.unpack('<I4s', chunk)
            if length % 4 or stream.tell() + length > size or kind in kinds:
                fail()
            if not kinds:
                if kind != b'JSON' or length > 32 * 1024 * 1024:
                    fail()
                data = json.loads(stream.read(length).decode('utf-8'))
                if not isinstance(data, dict) or data.get('asset', {}).get('version') != '2.0':
                    fail()
            else:
                stream.seek(length, 1)
            kinds.append(kind)
        if not kinds:
            fail()
    return {'format': 'glb2', 'chunks': len(kinds)}


def validate_asset(path, suffix=None):
    path = Path(path)
    try:
        kind = (suffix or path.suffix).lower()
        if kind == '.stl':
            return validate_stl(path)
        if kind == '.glb':
            return validate_glb(path)
        fail()
    except (ValueError, UnicodeError, struct.error, TypeError, AttributeError):
        fail()
