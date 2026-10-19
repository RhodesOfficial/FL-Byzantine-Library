"""D6 B worker: bounded archive/pickle VM, exact binary32 squares and Q192.

Only the B owner may launch this file. No torch/numpy/model/event imports.
The pickle language below constructs inert descriptors; it never calls a global.
"""
import sys
import os
import time
import json
import hashlib
import struct
import io
import zipfile
import pickletools
import math
from pathlib import Path

AUTH = '182e5e60556a020c52effb2e7eccfa071b45b980'
BASE = 'b14ee2b29db32e5cdfbd0e349359f25df7a9fc62'
ROOT = Path(__file__).resolve().parents[1]
OUTBASE = ROOT / 'artifacts/direction_a/phaseG1_3_B_d6_v1'
Q = 1 << 192
CAP = 4096
METADATA = {}
for ds, blobs in (
    ('CIFAR10', ('0f53f6ce8e7f4723f7921947938ba5c419df5b09', 'fa4370a9ac417f24b93b2996fad1897ee3847398')),
    ('CIFAR100', ('ab37f8240a71055a1238174176a68d51e465107a', '87ef2e4ba79378776975956a91eaaa02e9bb8220'))):
    for name, blob in zip(('counts.json', 'info.json'), blobs):
        METADATA[f'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-{ds}-N20-v1/{name}'] = blob
for name, blob in zip(('preregistration.json', 'reference_acceptance.json', 'artifact_hashes.json', 'archive_verification.json'),
                      ('c5bede12ee149329d3a22a24c2985e1bea633932', 'f6f0457990df506635f1d6a3f597a1f2e445897d',
                       '70cb121ab7324f6c170b5cc692165add98c0a175', '8b65168715721277b33224d9bc0ad6e0eefd6cec')):
    METADATA['artifacts/direction_a/phaseG1_2_full_v1/' + name] = blob
METADATA['artifacts/direction_a/backbone_preparation_v1/manifest.json'] = 'd56aaef5a6e0ddf6733353edf3653186531b1dea'
LIMITS = {n: dict(seconds=300, read=167772160, write=8388608, scans=6100000, ops=100000000000) for n in ('V1', 'V2')}
LIMITS.update({n: dict(seconds=120, read=16777216, write=12582912, scans=16384, ops=100000000) for n in ('S1', 'S2', 'S3')})
LIMITS['I'] = dict(seconds=10, read=524288, write=0, scans=12, ops=1000000)


class Gate(RuntimeError):
    pass


class Unresolved(Gate):
    pass


def integer(x, maximum=(1 << 63)-1):
    if type(x) is not int or not 0 <= x <= maximum:
        raise Gate('ACCOUNT_TYPE_RANGE')
    return x


def bits(x):
    if type(x) is not int or x.bit_length() > CAP:
        raise Gate('INTEGER_WIDTH')
    return x


def mul(a, b):
    if a and b and a.bit_length() + b.bit_length() > CAP:
        raise Gate('INTEGER_WIDTH_BEFORE_PRODUCT')
    return bits(a*b)


def shift(a, n):
    if n < 0 or a.bit_length()+n > CAP:
        raise Gate('INTEGER_WIDTH_BEFORE_SHIFT')
    return bits(a << n)


class Account:
    """Precharged named upper debits; observed bytes are recorded separately."""
    def __init__(self, name, initial=None):
        self.name, self.limit = name, LIMITS[name]
        self.used = dict(read=0, write=0, scans=0, ops=0)
        self.observed = dict(read=0, write=0, reads=0, writes=0)
        self.start = time.monotonic()
        self.actions = {}
        self.leased = self.settled = False
        if initial:
            self.charge('owner bootstrap and both pipe ends', **initial)

    def check(self):
        if time.monotonic()-self.start >= self.limit['seconds']-20:
            raise Gate('SOFT_DEADLINE_PRESERVE_S')

    def charge(self, label, **deltas):
        self.check()
        if len(self.actions) >= 128 and label not in self.actions:
            raise Gate('ACTION_CAP')
        for k, v in deltas.items():
            integer(v, self.limit[k])
            if v > self.limit[k]-self.used[k]:
                raise Gate('QUOTA_BEFORE_ACCESS:'+k)
        row = self.actions.setdefault(label, dict(read=0, write=0, scans=0, ops=0))
        for k, v in deltas.items():
            self.used[k] += v
            row[k] += v

    def lease(self):
        if self.leased:
            raise Gate('DUPLICATE_LEASE')
        self.leased = True

    def settle(self):
        if not self.leased or self.settled:
            raise Gate('DUPLICATE_SETTLEMENT')
        self.settled = True

    def report(self):
        return dict(upper_debits=self.used.copy(), observed_explicit_io=self.observed.copy(),
                    seconds_observed=time.monotonic()-self.start, actions=self.actions,
                    exact_scans=None, exact_primitive_ops=None, implicit_io=None)


def blob(raw):
    norm = raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    return hashlib.sha1(b'blob '+str(len(norm)).encode()+b'\0'+norm).hexdigest()


class Access:
    def __init__(self, budget, paths):
        self.budget, self.paths = budget, set(paths)
        self.records = []
        self.cache = {}
        self.observed_total = 0

    def read(self, path, cap, digest=None, identity=None, cache=False):
        if path not in self.paths:
            raise Gate('ACCESS_SCHEMA_BEFORE_STAT')
        target = (ROOT / path).resolve()
        if not target.is_relative_to(ROOT):
            raise Gate('PATH_ESCAPE')
        size = target.stat().st_size
        integer(size, cap)
        self.budget.charge('explicit reads/hash/copies', read=size, scans=4, ops=8*size)
        with target.open('rb') as stream:
            raw = stream.read(size+1)
        self.budget.observed['read'] += len(raw)
        self.budget.observed['reads'] += 1
        self.observed_total += len(raw)
        if len(raw) != size:
            raise Gate('IDENTITY_SIZE_CHANGE')
        sha = hashlib.sha256(raw).hexdigest()
        if digest is not None and sha != digest:
            raise Gate('IDENTITY_SHA_CHANGE')
        if identity is not None and blob(raw) != identity:
            raise Gate('IDENTITY_GIT_CHANGE')
        self.records.append(dict(path=path, bytes=size, sha256=sha, git_object=identity))
        if cache:
            self.cache[path] = raw
        return raw


def parse_json(raw, budget, cap=1048576):
    integer(len(raw), cap)
    budget.charge('bounded JSON parse/graph', scans=4, ops=32*len(raw))
    # Bound nesting before invoking the native parser, including rejected inputs.
    depth, quoted, escaped = 0, False, False
    for ch in raw:
        if quoted:
            if escaped:
                escaped = False
            elif ch == 92:
                escaped = True
            elif ch == 34:
                quoted = False
        elif ch == 34:
            quoted = True
        elif ch in (91, 123):
            depth += 1
            if depth > 24:
                raise Gate('JSON_DEPTH')
        elif ch in (93, 125):
            depth -= 1
    def pairs(items):
        result = {}
        for key, val in items:
            if key in result:
                raise Gate('JSON_DUPLICATE')
            result[key] = val
        return result
    def number(s):
        if len(s) > 20:
            raise Gate('JSON_INTEGER_LENGTH')
        return int(s)
    value = json.loads(raw, object_pairs_hook=pairs, parse_int=number,
                       parse_constant=lambda x: (_ for _ in ()).throw(Gate('JSON_NONFINITE')))
    return value


class Tensor:
    __slots__ = ('key', 'shape', 'count')
    def __init__(self, key, shape, count):
        self.key, self.shape, self.count = key, shape, count


class Decoder:
    """ZIP_STORED only, <=206 members, <=128 KiB program, <=8 MiB storage.

    genops is a tokenizer, not an unpickler. Its individual allocation is bounded
    by the 128 KiB input. Every stack/memo/container/argument is checked below.
    No getattr, import, pickle.load(s), executable REDUCE, or BUILD is used.
    """
    allowed = {('torch._utils', '_rebuild_tensor_v2'), ('torch', 'FloatStorage'),
               ('collections', 'OrderedDict')}

    def __init__(self, budget):
        self.budget = budget
        self.tokens = self.storage_bytes = 0

    def decode(self, raw):
        integer(len(raw), 1929208)
        self.budget.charge('archive inspection and bounded VM', scans=6, ops=32*len(raw))
        if len(raw) < 22 or raw[:4] != b'PK\x03\x04':
            raise Gate('ARCHIVE_FORMAT')
        end = raw.rfind(b'PK\x05\x06', max(0, len(raw)-65557))
        if end < 0 or end+22 > len(raw):
            raise Gate('ARCHIVE_DIRECTORY')
        disk, c_disk, n_disk, n, size, offset, comment = struct.unpack_from('<4H2IH', raw, end+4)
        if disk or c_disk or n_disk != n or not 1 <= n <= 206 or size > 32768 or offset+size > end or end+22+comment != len(raw):
            raise Gate('ARCHIVE_DIRECTORY_BOUND')
        # Central directory prepass prevents ZipFile from allocating an unbounded
        # member list; all declared lengths are <= remaining raw before addition.
        pos = offset
        for _ in range(n):
            if pos+46 > offset+size or raw[pos:pos+4] != b'PK\x01\x02':
                raise Gate('ARCHIVE_MEMBER_HEADER')
            nl, el, cl = struct.unpack_from('<3H', raw, pos+28)
            if nl > 256 or el > 256 or cl > 256 or pos+46+nl+el+cl > offset+size:
                raise Gate('ARCHIVE_MEMBER_LENGTH')
            pos += 46+nl+el+cl
        if pos != offset+size:
            raise Gate('ARCHIVE_MEMBER_COUNT')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) != n:
                raise Gate('ARCHIVE_MEMBER_COUNT')
            names, prefix, storage_total = {}, None, 0
            for entry in infos:
                parts = entry.filename.split('/')
                if len(parts) < 2 or len(parts) > 3 or any(not x or x in ('.', '..') for x in parts):
                    raise Gate('ARCHIVE_MEMBER_NAME')
                if prefix is None:
                    prefix = parts[0]
                key = '/'.join(parts[1:])
                if parts[0] != prefix or key in names or entry.compress_type != 0 or entry.flag_bits & 1 or entry.file_size != entry.compress_size:
                    raise Gate('ARCHIVE_COMPRESSION_ALIAS')
                if key.startswith('data/'):
                    if not key[5:].isascii() or not key[5:].isdigit() or len(key[5:]) > 6 or entry.file_size % 4:
                        raise Gate('STORAGE_KEY_SIZE')
                    integer(entry.file_size, 8388608-storage_total)
                    storage_total += entry.file_size
                elif key == 'data.pkl':
                    integer(entry.file_size, 131072)
                elif key in ('version', 'byteorder', '.data/serialization_id'):
                    integer(entry.file_size, 128)
                else:
                    raise Gate('ARCHIVE_ALLOWLIST')
                if entry.header_offset < 0 or entry.header_offset+30 > offset:
                    raise Gate('ARCHIVE_LOCAL_HEADER')
                names[key] = entry
            if 'data.pkl' not in names or 'version' not in names:
                raise Gate('ARCHIVE_REQUIRED')
            if 'byteorder' in names and archive.read(names['byteorder']) != b'little':
                raise Gate('ARCHIVE_ENDIAN')
            if archive.read(names['version']).strip() != b'3':
                raise Gate('ARCHIVE_VERSION')
            self.storage_bytes = storage_total
            code = archive.read(names['data.pkl'])
            value, descriptors = self.vm(code)
            # Validate all storage sizes before the first archive storage read.
            if set('data/'+key for key in descriptors) != set(k for k in names if k.startswith('data/')):
                raise Gate('STORAGE_SET')
            for key, count in descriptors.items():
                if names['data/'+key].file_size != mul(count, 4):
                    raise Gate('STORAGE_DECLARED_SIZE')
            self.budget.charge('storage extraction/copies', scans=2*len(descriptors), ops=4*storage_total)
            storages = {key: archive.read(names['data/'+key]) for key in descriptors}
        return value, storages

    def vm(self, raw):
        stack, marks, memo, descriptors = [], [], {}, {}
        stop = False
        def push(x):
            if len(stack) >= 4096:
                raise Gate('PICKLE_STACK')
            stack.append(x)
        def items():
            if not marks:
                raise Gate('PICKLE_MARK')
            at = marks.pop()
            values = stack[at:]
            del stack[at:]
            return values
        def put(target, values):
            if type(target) is not dict or len(values) % 2:
                raise Gate('PICKLE_DICT')
            for k, v in zip(values[::2], values[1::2]):
                if type(k) not in (int, str) or k in target or len(target) >= 4096:
                    raise Gate('PICKLE_KEY')
                target[k] = v
        for index, (opcode, arg, pos) in enumerate(pickletools.genops(raw)):
            if index >= 32768:
                raise Gate('PICKLE_OP_CAP')
            self.tokens += 1
            name = opcode.name
            if name == 'PROTO':
                if arg != 2 or index != 0:
                    raise Gate('PICKLE_PROTOCOL')
            elif name == 'EMPTY_DICT': push({})
            elif name == 'EMPTY_LIST': push([])
            elif name == 'EMPTY_TUPLE': push(())
            elif name == 'MARK':
                if len(marks) >= 24:
                    raise Gate('PICKLE_DEPTH')
                marks.append(len(stack))
            elif name in ('BININT', 'BININT1', 'BININT2', 'LONG1'):
                integer(arg, 2147483647)
                push(arg)
            elif name in ('NEWTRUE', 'NEWFALSE', 'NONE'):
                push({'NEWTRUE': True, 'NEWFALSE': False, 'NONE': None}[name])
            elif name == 'BINUNICODE':
                if len(arg) > 1024:
                    raise Gate('PICKLE_STRING')
                push(arg)
            elif name in ('BINPUT', 'LONG_BINPUT'):
                integer(arg, 4095)
                if arg in memo or not stack:
                    raise Gate('PICKLE_MEMO')
                memo[arg] = stack[-1]
            elif name in ('BINGET', 'LONG_BINGET'):
                integer(arg, 4095)
                push(memo[arg])
            elif name == 'GLOBAL':
                symbol = tuple(arg.split(' '))
                if symbol not in self.allowed:
                    raise Gate('PICKLE_GLOBAL_ALLOWLIST')
                push(('symbol', symbol))
            elif name == 'TUPLE': push(tuple(items()))
            elif name in ('TUPLE1', 'TUPLE2', 'TUPLE3'):
                count = int(name[-1])
                if len(stack) < count:
                    raise Gate('PICKLE_TUPLE')
                values = tuple(stack[-count:]); del stack[-count:]; push(values)
            elif name == 'BINPERSID':
                pid = stack.pop()
                if type(pid) is not tuple or len(pid) != 5 or pid[0] != 'storage' or pid[1] != ('symbol', ('torch', 'FloatStorage')) or pid[3] != 'cpu':
                    raise Gate('PICKLE_STORAGE_DESCRIPTOR')
                key, count = pid[2], integer(pid[4], 2097152)
                if type(key) is not str or not key.isascii() or not key.isdigit() or len(key) > 6:
                    raise Gate('PICKLE_STORAGE_KEY')
                if key in descriptors and descriptors[key] != count:
                    raise Gate('PICKLE_STORAGE_ALIAS')
                descriptors[key] = count
                if len(descriptors) > 200 or sum(descriptors.values()) > 2097152:
                    raise Gate('STORAGE_ALLOCATOR_CAP')
                push(('storage', key, count))
            elif name == 'REDUCE':
                args, fn = stack.pop(), stack.pop()
                if type(args) is not tuple:
                    raise Gate('PICKLE_REDUCE_ARGS')
                if fn == ('symbol', ('collections', 'OrderedDict')) and not args:
                    push({})
                elif fn == ('symbol', ('torch._utils', '_rebuild_tensor_v2')):
                    if len(args) != 6:
                        raise Gate('TENSOR_ARGS')
                    storage, offset, shape, strides, requires, hooks = args
                    if type(storage) is not tuple or len(storage) != 3 or storage[0] != 'storage' or offset != 0 or requires is not False or hooks != {}:
                        raise Gate('TENSOR_STORAGE_OFFSET')
                    if type(shape) is not tuple or shape not in ((10, 128), (100, 128), (10,), (100,)):
                        raise Gate('TENSOR_SHAPE')
                    count = 1
                    for dim in shape: count = mul(count, integer(dim, 128))
                    expected = (128, 1) if len(shape) == 2 else (1,)
                    if strides != expected or count != storage[2]:
                        raise Gate('TENSOR_CONTIGUITY')
                    push(Tensor(storage[1], shape, count))
                else:
                    raise Gate('PICKLE_REDUCE_ALLOWLIST')
            elif name == 'SETITEMS':
                values = items(); put(stack[-1], values)
            elif name == 'SETITEM':
                val, key = stack.pop(), stack.pop(); put(stack[-1], [key, val])
            elif name in ('APPENDS', 'APPEND'):
                values = items() if name == 'APPENDS' else [stack.pop()]
                if type(stack[-1]) is not list or len(stack[-1])+len(values) > 4096:
                    raise Gate('PICKLE_LIST')
                stack[-1].extend(values)
            elif name == 'STOP':
                if marks or len(stack) != 1 or pos != len(raw)-1:
                    raise Gate('PICKLE_STOP')
                stop = True
            else:
                raise Gate('PICKLE_OPCODE_ALLOWLIST:'+name)
        if not stop:
            raise Gate('PICKLE_NO_STOP')
        # Acyclic, depth-limited graph check precedes any recursive consumer.
        todo, seen, nodes = [(stack[0], 0)], set(), 0
        while todo:
            item, depth = todo.pop(); nodes += 1
            if nodes > 32768 or depth > 24:
                raise Gate('PICKLE_GRAPH_BOUND')
            if type(item) in (dict, list, tuple):
                if id(item) in seen:
                    raise Gate('PICKLE_CONTAINER_ALIAS')
                seen.add(id(item))
                vals = item.values() if type(item) is dict else item
                todo.extend((v, depth+1) for v in vals)
            elif type(item) not in (str, int, bool, type(None), Tensor):
                raise Gate('PICKLE_VALUE_TYPE')
        return stack[0], descriptors


def scaled32(raw):
    """Exact binary32 = returned signed integer / 2**149, including subnormals."""
    out = []
    for (word,) in struct.iter_unpack('<I', raw):
        exp, frac = (word >> 23) & 255, word & 0x7fffff
        if exp == 255:
            raise Gate('NONFINITE_BINARY32')
        n = frac if exp == 0 else ((1 << 23) | frac) << (exp-1)
        out.append(-n if word >> 31 else n)
    return out


def root192(square, denominator=1):
    """Bisection with a fixed 4096-step bound; Q192 enclosure by squares."""
    integer(denominator)
    bits(square)
    if square < 0 or denominator == 0:
        raise Gate('ROOT_DOMAIN')
    n = shift(square, 86)  # 2*192 - 2*149
    left, right = 0, 1 << ((n.bit_length()+1)//2)
    for _ in range(4096):
        if left >= right:
            return left, left+(mul(mul(left, left), denominator) != n)
        mid = (left+right+1)//2
        if mul(mul(mid, mid), denominator) <= n:
            left = mid
        else:
            right = mid-1
    raise Gate('ROOT_STEP_CAP')


def oracle256(square, denominator=1):
    """Independent integer library root, certified by exact rational squares."""
    n = shift(square, 214)
    base = math.isqrt(n//denominator)
    if not mul(mul(base, base), denominator) <= n < mul(mul(base+1, base+1), denominator):
        raise Gate('ORACLE_SQUARE_CERTIFICATE')
    return base, base+(mul(mul(base, base), denominator) != n)


def divide(a, b):
    if b[0] <= 0:
        raise Unresolved('SCALE_INTERVAL_TOUCHES_ZERO')
    return shift(a[0], 192)//b[1], -((-shift(a[1], 192))//b[0])


def encode(interval):
    return [format(interval[0], 'x'), format(interval[1]-interval[0], 'x')]


def metric(counts, vectors, h, budget, on_result=None, progress=None):
    m = len(counts)
    if h not in (1290, 12900) or not 1 <= m <= 20 or len(vectors) != m or any(len(v) != h for v in vectors):
        raise Gate('METRIC_SHAPE')
    if any(integer(n, 2147483647) == 0 for n in counts):
        raise Gate('METRIC_COUNT')
    N = sum(counts); integer(N)
    pairs = m*(m-1)//2
    # All scalar loops below are bounded by h*(m+pairs), all roots by m+pairs+2.
    budget.charge('Q192 source/pair graph', scans=64*(m+pairs)+8,
                  ops=64*h*(m+pairs)+65536*(m+pairs+2))
    squares, norms = [], []
    structural = True
    if progress is not None:
        progress.update(status='PARTIAL', source_norms_partial=[], pairs_partial=[])
    for v in vectors:
        budget.check()
        if any(type(x) is not int or x.bit_length() > 278 for x in v):
            raise Gate('SOURCE_INTEGER_WIDTH')
        square = bits(sum(x*x for x in v)); squares.append(square)
        structural = structural and square == 0
        norms.append(root192(square))
        if on_result is not None:
            on_result('source_norm')
        if progress is not None:
            progress['source_norms_partial'].append(encode(norms[-1]))
    low = sum(n*r[0] for n, r in zip(counts, norms))//N
    high = -((-sum(n*r[1] for n, r in zip(counts, norms)))//N)
    S = (bits(low), bits(high))
    distances, exact_pairs, maximum, sumsq, best = [], [], 0, 0, None
    for i in range(m):
        for j in range(i+1, m):
            budget.check()
            sq = bits(sum((x-y)*(x-y) for x, y in zip(vectors[i], vectors[j])))
            exact_pairs.append(sq); sumsq = bits(sumsq+sq)
            distances.append([i, j, *encode(root192(sq))])
            if progress is not None:
                progress['pairs_partial'].append(distances[-1])
            if best is None or sq > maximum:
                maximum, best = sq, [i, j]
    D = root192(maximum)
    rms = root192(sumsq, pairs) if pairs else (0, 0)
    if structural:
        tau, degenerate = (0, 0), 'STRUCTURAL_ALL_ZERO'
    elif S[0] == 0:
        tau, degenerate = None, 'UNRESOLVED_SCALE'
    else:
        tau = divide(D, (mul(N, S[0]), mul(N, S[1])))
        degenerate = 'SINGLE_SOURCE' if m == 1 else ('IDENTICAL_SOURCES' if maximum == 0 else 'NONE')
    # Independent algebraic replacement certificates: exact squared pair order
    # implies ||+/- (gi-gj)/N||/S <= max_distance/(N*S). No p is supplied.
    control_checks = all(sq <= maximum for sq in exact_pairs)
    equal = best is None or exact_pairs[max(range(len(exact_pairs)), key=exact_pairs.__getitem__)] == maximum
    return dict(n=counts, N=N, m=m, h=h, S=encode(S), source_norms=[encode(x) for x in norms],
                pairs=distances, max=encode(D), RMS=encode(rms), tau=encode(tau) if tau else None,
                degenerate=degenerate, uniform=dict(b_equals_a=True, d_exact_zero=True),
                replacement=dict(signs=[1, -1], pair_ratio='distance/(N*S); distance interval from pairs; common positive S',
                                 all_squared_order_checks=control_checks, maximum_pair=best, maximum_equality=equal,
                                 interval_inclusion=control_checks and equal, structural_zero=structural),
                _tau=tau, _S=S, _norm_squares=squares, _pair_squares=exact_pairs)


def macro(rows, ids, denominator):
    if len(ids) != denominator or any(rows[i]['_tau'] is None for i in ids):
        return None
    lo = sum(rows[i]['_tau'][0] for i in ids)//denominator
    hi = -((-sum(rows[i]['_tau'][1] for i in ids))//denominator)
    return lo, hi


def public(value):
    if type(value) is dict:
        return {k: public(v) for k, v in value.items() if not k.startswith('_')}
    if type(value) is list:
        return [public(v) for v in value]
    return value


def metadata(access, budget, projection):
    cache = {}
    total = 0
    for path, identity in METADATA.items():
        raw = access.read(path, 1048576-total, identity=identity, cache=True)
        total += len(raw)
        cache[path] = parse_json(raw, budget)
    gs = 'artifacts/direction_a/phaseG1_2_full_v1/'
    accepted = cache[gs+'reference_acceptance.json']['references']
    archive = cache[gs+'artifact_hashes.json']['files']
    backbone = cache['artifacts/direction_a/backbone_preparation_v1/manifest.json']['references']
    refs, total_bytes, sum_mh, sum_ph, sum_m, sum_pairs = [], 0, 0, 0, 0, 0
    for binding in projection['bindings']:
        ds, C, ref = binding['dataset'], binding['classes'], binding['ref']
        if ds not in ('CIFAR10', 'CIFAR100') or C != (10 if ds == 'CIFAR10' else 100):
            raise Gate('BINDING_DATASET')
        dp = f'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-{ds}-N20-v1/'
        counts, info = cache[dp+'counts.json'], cache[dp+'info.json']
        n, N = counts['n_ic'], counts['N_c']
        if len(n) != 20 or len(N) != C or any(len(row) != C for row in n):
            raise Gate('DENOMINATOR_SHAPE')
        for c in range(C):
            if integer(N[c], 2147483647) == 0 or sum(integer(n[i][c], 2147483647) for i in range(20)) != N[c]:
                raise Gate('DENOMINATOR_SUM')
            m = sum(n[i][c] > 0 for i in range(20)); pairs = m*(m-1)//2
            sum_mh += m*129*C; sum_ph += pairs*129*C; sum_m += m; sum_pairs += pairs
        tail = sorted(range(C), key=lambda c: (-N[c], c))[(2*C)//3:]
        if tail != counts['class_groups']['tail'] or len(tail) != binding['tail_denominator']:
            raise Gate('TAIL_DENOMINATOR')
        if sorted(info['label_mapping'].values()) != list(range(C)) or info['spec']['classes'] != C or info['spec']['clients'] != 20:
            raise Gate('LABEL_SCHEMA')
        entry = next(x for x in accepted if x['reference']['reference_id'] == ref)
        r, b = entry['reference'], entry['binding']
        if r != next(x for x in backbone if x['reference_id'] == ref) or r['state_sha256'] != binding['state'] or r['checkpoint_path'] != binding['checkpoint']:
            raise Gate('REFERENCE_INDEX')
        if r['dataset'] != ds or r['task_identity'] != binding['task'] or r['task_identity'] != info['spec']['identity'] or r['task_identity'] != b['task_identity']:
            raise Gate('REFERENCE_TASK')
        if str(r['training_progress']) != binding['progress'] or any(entry[k] != r['state_sha256'] for k in ('state_before', 'state_after', 'repeated_read')):
            raise Gate('REFERENCE_STATE')
        if b['class_groups'] != counts['class_groups'] or b['label_mapping'] != info['label_mapping']:
            raise Gate('REFERENCE_LABELS')
        sha = info['artifact_sha256']['counts.json']
        if b['source_files']['counts.json']['sha256'] != sha or b['split_identity']['counts_source']['sha256'] != sha:
            raise Gate('DENOMINATOR_BINDING')
        if b['split_identity']['validation_rule'] != info['validation_rule'] or b['split_identity']['test_rule'] != info['test_rule']:
            raise Gate('SPLIT_BINDING')
        paths, hashes, sizes = [], [], []
        for i in range(20):
            relative = f'messages/{ref}/client_{i:03d}.pt'
            path = gs+relative
            sha = archive[relative]
            if type(sha) is not str or len(sha) != 64:
                raise Gate('MESSAGE_INDEX_SHA')
            # No data read at stat; all sizes freeze before real entry.
            size = (ROOT/path).stat().st_size
            integer(size, 1929208)
            paths.append(path); hashes.append(sha); sizes.append(size); total_bytes += size
        if hashlib.sha256(''.join(hashes).encode()).hexdigest() != binding['message_index_sha256']:
            raise Gate('MESSAGE_INDEX_BINDING')
        refs.append(dict(binding=binding, counts=counts, C=C, tail=tail, paths=paths, hashes=hashes, sizes=sizes))
    if len(refs) != 4 or total_bytes != 62840948:
        raise Gate('FROZEN_MESSAGE_SCALE')
    if (sum_mh > 52116000 or sum_ph > 495102000 or sum_m > 4400 or sum_pairs > 41800):
        raise Gate('FROZEN_LOOP_ENVELOPE')
    return refs, dict(message_bytes=total_bytes, source_coordinates=sum_mh, pair_coordinates=sum_ph,
                      sources=sum_m, pairs=sum_pairs, metadata_bytes=total)


def qualify_packet(packet, storages, ref, client, budget):
    expected = {'reference_id', 'state_sha256', 'client_id', 'C', 'd', 'bias', 'class_ids',
                'missing_class_ids', 'denominators', 'gradients', 'layout'}
    if type(packet) is not dict or set(packet) != expected:
        raise Gate('MESSAGE_SCHEMA')
    C, binding = ref['C'], ref['binding']
    if (packet['reference_id'] != binding['ref'] or packet['state_sha256'] != binding['state'] or
            type(packet['client_id']) is not int or packet['client_id'] != client or packet['C'] != C or packet['d'] != 128 or packet['bias'] is not True or
            packet['layout'] != 'gradients[class_id][0]=C*128 weight, [1]=C bias; float32'):
        raise Gate('MESSAGE_IDENTITY')
    n = ref['counts']['n_ic'][client]
    active = [c for c in range(C) if n[c] > 0]
    if packet['class_ids'] != active or packet['missing_class_ids'] != [c for c in range(C) if c not in active] or packet['denominators'] != {c: n[c] for c in active} or set(packet['gradients']) != set(active):
        raise Gate('MESSAGE_CLASS_COUNT')
    packed, seen = {}, set()
    for c in active:
        values = packet['gradients'][c]
        if type(values) not in (list, tuple) or len(values) != 2:
            raise Gate('HEAD_WEIGHT_BIAS')
        chunks = []
        for tensor, shape in zip(values, ((C, 128), (C,))):
            if type(tensor) is not Tensor or tensor.shape != shape or tensor.key in seen:
                raise Gate('HEAD_SHAPE_STORAGE_ALIAS')
            seen.add(tensor.key)
            raw = storages[tensor.key]
            budget.charge('finite check and packed copy', scans=2, ops=16*tensor.count)
            # Finite test is a full-bit scan; vectors are converted per class later.
            if any((x[0] >> 23) & 255 == 255 for x in struct.iter_unpack('<I', raw)):
                raise Gate('NONFINITE_BINARY32')
            chunks.append(raw)
        packed[c] = b''.join(chunks)
    if seen != set(storages):
        raise Gate('UNUSED_STORAGE')
    return packed


def interval_decimal(interval):
    # Display only; all evidence and aggregation above uses exact Q192 integers.
    return [interval[0]/Q, interval[1]/Q] if interval is not None else None


def freeze_plan(projection, run, source_hashes):
    return dict(schema='G13-B-D6-plan-v1', authorization_commit=AUTH, base_commit=BASE, run=run,
        source_hashes=source_hashes, limits=LIMITS, counts_before=[6, 3, 4, 4], allocation=[3, 2, 2, 2],
        cycle=dict(seconds=970, read=386400256, write=54525952, scans=12249164, ops=200301000000),
        inheritance=projection['inheritance'], bindings=projection['bindings'],
        input_schema=dict(metadata=METADATA, message_pattern='four indexed refs/client_000..019.pt only',
                          excluded=['s', 'L', 'p', 'F', 'V', 'M', 'model contents', 'main rho/results']),
        graph=[
            dict(action='B00', length=524288, loops=10, scans_upper=24000, ops_upper=64000000,
                 objects='parent projection only; prior raw released before worker; no whole A bundle in worker'),
            dict(action='B01', length=1048576, loops=9, scans_upper=16000, ops_upper=100000000,
                 objects='cached metadata/source <=1.75 MiB; tests sequential'),
            dict(action='B02', length=1929208, loops=80, scans_upper=40000, ops_upper=12000000000,
                 objects='raw<=1929208, ZIP storage<=8388608, one-message packed copies; ref packed<=103200000'),
            dict(action='B03', length=62840948, loops=80, scans_upper=400, ops_upper=600000000,
                 objects='one raw only, no decode'),
            dict(action='B04', length=12900, sources=4400, pairs=41800,
                 scans_upper=5913600, ops_upper=86000000000,
                 derivation='64h(m+pairs)+65536(m+pairs+2) Q192; Q256 synthetic only, charged separately; sums <=4096 bits; root<=4096 iterations',
                 objects='one class signed integers <=20*12900*(8+68) <20 MiB; root temporaries sequential; no Q256 arena overlap'),
            dict(action='B05/failure/IPC', length=8388608, loops=12, scans_upper=20000, ops_upper=1000000000,
                 objects='output <=8MiB; 16KiB frames; bidirectional each<=2MiB'),
            dict(action='S', length=8388608, loops=12, scans_upper=16384, ops_upper=100000000,
                 objects='one output raw at a time; double encoding and independent disk readback; no message reread')],
        graph_totals=dict(V_scans=6014000, V_ops=99764000000, V_read_upper=159907840, V_write_upper=8388608,
                          S_read_upper=16777216, S_write_upper=12582912),
        decoder=dict(archive='uncompressed ZIP only', members=206, directory_bytes=32768, pickle_bytes=131072,
                     pickle_ops=32768, stack=4096, memo=4096, depth=24, dict_or_list=4096,
                     storage_bytes=8388608, allocator='lengths/products checked before archive storage reads; inert Tensor descriptors; no torch import',
                     allowed_globals=sorted('/'.join(x) for x in Decoder.allowed), implicit_allocator_peak=None),
        lifetime=dict(packed=103200000, arena_upper=211353600, class_float64_upper=2064000,
                      raw=1929208, storage=8388608, auxiliary=33554432, simultaneous_proxy_upper=360489848,
                      proxy_limit=536870912, Windows_job_limit=2147483648, CUDA_initializations=0),
        width=dict(source_scaled_bits=278, pair_difference_bits=279, square_sum_bits=574,
                   largest_sqrt_shift_bits=788, cap=4096, sqrt_steps=4096),
        science=dict(target='exact sealed binary32 full weight(C,128) then bias(C)',
                     oracle='independent Q256 squared brackets; Q192 bisection measured',
                     precision=192, epsilon_bias_rule='blind mean tau upper endpoint, pending reviewer freeze',
                     historical_Ri=None, ideal_vi=None, continuous_eta=None, continuous_projection=None),
        preparation=dict(observed_commands_seconds=[0.6513037,0.8822233,0.9095145,0.7528799,0.7358923,0.7126296,0.854336,0.7578627],
                         complete_read_bytes=None, complete_write_bytes=None, full_wall_seconds=None, full_peak=None,
                         issue='single startup accounting gap: exact aggregate prep I/O unavailable; bounded directed preparation continued under ROLE'),
        platform_seconds_proof=None, full_peak_proof=None, physical_implicit_io=None)


class Seal:
    def __init__(self, out, budget):
        self.out, self.budget, self.hashes = out, budget, {}

    def write(self, name, value, cap):
        # Pre-reserve two serialized representations plus one independent read.
        # Actual serialization bytes are recorded after bounded graph creation.
        self.budget.charge('seal double serialization/hash/readback', scans=8, ops=8*cap)
        raw = (json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':'))+'\n').encode()
        integer(len(raw), cap)
        if raw != (json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':'))+'\n').encode():
            raise Gate('SEAL_SERIALIZATION_DIFFERENCE')
        self.budget.charge('seal explicit bytes', read=len(raw), write=len(raw))
        path = self.out/name
        if path.exists():
            raise Gate('OUTPUT_OVERWRITE')
        path.write_bytes(raw)
        self.budget.observed['write'] += len(raw); self.budget.observed['writes'] += 1
        verify = path.read_bytes()
        self.budget.observed['read'] += len(verify); self.budget.observed['reads'] += 1
        sha = hashlib.sha256(raw).hexdigest()
        if verify != raw or hashlib.sha256(verify).hexdigest() != sha:
            raise Gate('SEAL_READBACK_IDENTITY')
        self.hashes[name] = dict(bytes=len(raw), sha256=sha, readback='PASS')


def main():
    if os.environ.get('G13_B_AUTH') != AUTH or os.environ.get('G13_B_JOB_VERIFIED') != '1':
        raise SystemExit('B owner and inherited Job required')
    run = os.environ['G13_B_RUN']
    if run not in ('V1', 'V2'):
        raise SystemExit('registered V required')
    out = OUTBASE/run
    outer = json.loads(os.environ['G13_B_BOOT'])
    budget = Account(run, outer['debits'])
    budget.start -= outer['active_elapsed']
    paths = set(METADATA) | {outer['projection_path'], 'tests/test_direction_a_g1_3_blind.py', 'scripts/measure_direction_a_g1_3_blind.py', 'scripts/measure_direction_a_g1_3_blind_outer.ps1'}
    access = Access(budget, paths)
    qualification = dict(status='NOT_RUN', decoder_static='see plan.decoder', messages=[], metadata=None)
    synthetic = dict(status='NOT_RUN', cases=[])
    results = dict(status='NOT_RUN', refs=[], epsilon_bias=None, epsilon_num=None)
    checkpoint = dict(status='NOT_COMPLETED', completed=['B00'], partial=[], not_started=['B01','B02','B03','B04','B05'],
                      real_entries=0, scientific_results=0, first_result=None, formal_events=0, fits=0, fees=0, models=0,
                      counts=list(outer['counts_before']))
    checkpoint['counts'][0] += 1
    if run == 'V2':
        checkpoint['counts'][1] += 1
    failure = dict(status='NONE', signature=None, type=None, location=None, cause=None)
    plan = None
    phase = 'B00'
    budget.lease()
    try:
        projection_raw = access.read(outer['projection_path'], 524288, digest=outer['projection_sha256'], cache=True)
        projection = parse_json(projection_raw, budget, 524288)
        if set(projection) != {'schema','authorization_commit','bindings','B_requirements','error_objects','inheritance'} or projection['schema'] != 'G13-B-input-v1' or projection['authorization_commit'] != AUTH:
            raise Gate('BLIND_SCHEMA')
        if len(projection['bindings']) != 4 or len(projection['B_requirements']) != 220:
            raise Gate('BLIND_PROJECTION_LENGTH')
        source_hashes = []
        for source in ('scripts/measure_direction_a_g1_3_blind.py', 'tests/test_direction_a_g1_3_blind.py', 'scripts/measure_direction_a_g1_3_blind_outer.ps1'):
            raw = access.read(source, 262144, cache=True)
            source_hashes.append(dict(path=source, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        if source_hashes[0]['sha256'] != outer['source_sha256']:
            raise Gate('SOURCE_BOOTSTRAP_IDENTITY_CHANGE')
        if sum(x['bytes'] for x in source_hashes) > 262144:
            raise Gate('SOURCE_COMBINED_CAP')
        plan = freeze_plan(projection, run, source_hashes)
        # V2 is admissible only with its own verified complete predecessor ledger.
        if run == 'V2' and not outer.get('predecessor_verified'):
            raise Gate('B_PREDECESSOR_UNVERIFIED')
        phase = 'B01/syntax'
        checkpoint['counts'][2] += 1
        for source in ('scripts/measure_direction_a_g1_3_blind.py', 'tests/test_direction_a_g1_3_blind.py'):
            budget.charge('syntax cached sources', scans=1, ops=100*len(access.cache[source]))
            compile(access.cache[source], source, 'exec')
        checkpoint['counts'][3] += 1
        phase = 'B01/synthetic'
        suite = {'__name__':'G13_B_registered_suite'}
        exec(compile(access.cache['tests/test_direction_a_g1_3_blind.py'], 'tests/test_direction_a_g1_3_blind.py', 'exec'), suite)
        suite['run_suite'](sys.modules[__name__], budget, synthetic['cases'])
        synthetic['status'] = 'PASS'
        checkpoint['completed'].append('B01/synthetic')
        phase = 'B01/metadata'
        refs, envelope = metadata(access, budget, projection)
        qualification['metadata'] = envelope
        checkpoint['completed'].append('B01/metadata')
        budget.charge('whole remaining real graph reservation check', scans=0)
        # Check the remaining graph before entering a real message. The cycle is
        # never renewed; precharges are per actual class/decoder, not a second lease.
        future_ops = 64*(envelope['source_coordinates']+envelope['pair_coordinates']) + 65536*(envelope['sources']+envelope['pairs']+440) + 12000000000
        future_scans = 64*(envelope['sources']+envelope['pairs'])+100000
        if (2*envelope['message_bytes']+1048576 > budget.limit['read']-budget.used['read'] or
                future_ops > budget.limit['ops']-budget.used['ops'] or future_scans > budget.limit['scans']-budget.used['scans']):
            raise Gate('REAL_GRAPH_REMAINING_BUDGET')
        qualification['static_and_same_cycle_synthetic'] = 'PASS'
        access.paths.update(path for ref in refs for path in ref['paths'])
        phase = 'B02'
        checkpoint['real_entries'] = 1
        results['status'] = 'PARTIAL'
        for ref in refs:
            C, packed = ref['C'], []
            first_records = []
            for i, (path, sha, size) in enumerate(zip(ref['paths'], ref['hashes'], ref['sizes'])):
                phase = 'B02'
                raw = access.read(path, size, digest=sha)
                if len(raw) != size:
                    raise Gate('FROZEN_STAT_CHANGED')
                decoder = Decoder(budget)
                packet, storages = decoder.decode(raw)
                packed.append(qualify_packet(packet, storages, ref, i, budget))
                first_records.append(dict(path=path, sha256=sha, bytes=size, client=i, classes=packet['class_ids'],
                                          denominators=packet['denominators'], dtype='binary32', storage_bytes=decoder.storage_bytes,
                                          pickle_ops=decoder.tokens, full_order='weight(C,128),bias(C)', first_pass='PASS', second_pass='NOT_RUN'))
                qualification['messages'].append(first_records[-1])
                del raw, decoder, packet, storages
            phase = 'B03'
            for path, sha, size, record in zip(ref['paths'], ref['hashes'], ref['sizes'], first_records):
                raw = access.read(path, size, digest=sha)
                if len(raw) != size:
                    raise Gate('SECOND_PASS_SIZE')
                record['second_pass'] = 'PASS'
                del raw
            phase = 'B04'
            rows = []
            result = dict(ref=ref['binding']['ref'], classes=rows, tail_classes=ref['tail'],
                          denominators=dict(all=C, tail=len(ref['tail'])), mean_tau=None,
                          epsilon_bias_candidate=None, status='PARTIAL')
            results['refs'].append(result)
            for c in range(C):
                indices = [i for i in range(20) if c in packed[i]]
                budget.charge('one-class exact scaled conversion', scans=len(indices), ops=16*len(indices)*129*C)
                vectors = [scaled32(packed[i][c]) for i in indices]
                def mark_result(object_name):
                    if checkpoint['first_result'] is None:
                        checkpoint['first_result'] = dict(monotonic=time.monotonic(), wall_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                                          ref=ref['binding']['ref'], c=c, object=object_name)
                    checkpoint['scientific_results'] += 1
                pending = dict(c=c, clients=indices, status='PARTIAL', _tau=None)
                rows.append(pending)
                row = metric([ref['counts']['n_ic'][i][c] for i in indices], vectors, 129*C, budget, mark_result, pending)
                row.update(c=c, clients=indices)
                pending.clear(); pending.update(row); pending['status'] = 'PASS'
                del vectors
            all_mean = macro(rows, list(range(C)), C)
            tail_mean = macro(rows, ref['tail'], len(ref['tail']))
            result.update(
                          mean_tau=dict(all=encode(all_mean) if all_mean else None, tail=encode(tail_mean) if tail_mean else None),
                          epsilon_bias_candidate=dict(all=interval_decimal(all_mean), tail=interval_decimal(tail_mean),
                                                      adopt='upper endpoint; outward arithmetic and fixed class denominator; awaiting reviewer freeze'),
                          status='PASS' if all_mean is not None and tail_mean is not None else 'FAIL')
            del packed
        qualification['status'] = 'PASS'
        results['epsilon_bias'] = dict(rule='per-ref all/tail blind mean tau upper; values in refs; not frozen')
        results['epsilon_num'] = dict(target='exact sealed binary32', source_perturbation='0 conditional on qualified identity',
            p_independent=['S', 'source norms', 'pair distances', 'max', 'RMS', 'tau', 'all/tail mean tau'],
            p_independent_numeric='every reported interval: absolute width=hex(width)*2^-192; no universal scalar epsilon',
            dependent=dict(d='2*max(E_i)+E_d_arith', rho='E_A/S_- + abs(Ahat)*E_S/(Shat*S_-)+E_div',
                           X='M*(zeta/z_*+t/(Z*z_*))', X0='M*(zeta0/p_*+eta0/(p0*p_*))',
                           P='((1+E_u)*E_W+E_u*R_W+E_dot)/S_- + abs(That)*E_S/(Shat*S_-)+E_div',
                           endpoints='mean(e_s)+sqrt(722/39)*sqrt(sum(e_s^2))/sqrt(6)+E_endpoint'),
            historical_Ri=None, ideal_vi=None, eta=None, continuous_projection=None, epsilon_total=None,
            targets='historical/ideal/continuous extrapolation and C projections remain uncertified; B does not substitute for complete G1.3')
        results['status'] = 'PASS' if all(x['status'] == 'PASS' for x in results['refs']) else 'FAIL'
        checkpoint['completed'] = ['B00','B01','B02','B03','B04','B05']
        checkpoint['not_started'] = []
        checkpoint['status'] = results['status']
    except Exception as exc:
        failure.update(status='FAIL', type=type(exc).__name__, location=phase, cause=str(exc)[:768],
                       signature=type(exc).__name__+'|'+phase+'|'+str(exc)[:256])
        checkpoint['partial'].append(phase)
        checkpoint['status'] = 'NOT_COMPLETED_ENGINEERING_BLOCKED' if checkpoint['scientific_results'] == 0 else 'PARTIAL_SCIENCE_SEALED_NO_RETRY'
    finally:
        budget.settle()
        # Parent switches the Job's deadline from the original 300s V deadline
        # to the reserved S account after this bounded message, before disk I/O.
        print(json.dumps(dict(action='seal', auth=AUTH, run=run)), flush=True)
        if sys.stdin.readline(16385).strip() != 'S_GRANTED':
            raise Gate('S_OWNER_HANDSHAKE')
        seal_budget = Account('S'+run[-1])
        seal = Seal(out, seal_budget)
        seal.write('plan.json', plan or dict(status='PARTIAL', authorization_commit=AUTH, limits=LIMITS), 65536)
        seal.write('qualification.json', qualification, 131072)
        seal.write('synthetic_acceptance.json', synthetic, 131072)
        seal.write('blind_results.json', public(results), 7602176)
        seal.write('failure.json', failure, 16384)
        checkpoint.update(synthetic=synthetic['status'], qualification=qualification['status'], artifacts='see artifact_hashes.json',
                          stop='first success' if checkpoint['status'] == 'PASS' else 'see failure; no retry after science')
        seal.write('state_checkpoint.json', checkpoint, 131072)
        seal_budget.charge('ledger/receipt/manifest/owner terminal reserved', read=262144+16384+32768+16384,
                           write=262144+16384+32768+16384, scans=64, ops=4000000)
        ledger = dict(schema='G13-B-D6-ledger-v1', authorization_commit=AUTH, run=run, limits=LIMITS,
                      V=budget.report(), S_preterminal=seal_budget.report(), S_terminal_reservation=dict(read=327680,write=327680,scans=64,ops=4000000),
                      counts=checkpoint['counts'], real_entries=checkpoint['real_entries'], scientific_results=checkpoint['scientific_results'],
                      history=outer['inheritance'], risk_not_actual=True, full_process_peak=None, physical_io=None,
                      full_cycle_wall_seconds=None, implicit_interpreter_io=None,
                      access_log=access.records, whitelist_violations=0, CUDA_initializations=0,
                      cpu_proxy_upper=360489848, observed_cpu_proxy_peak=None,
                      source_cache_hashes=plan['source_hashes'] if plan else None,
                      note='upper debits include pre-reserved terminal bytes; explicit observed bytes are lower bounds; owner terminal observation covers process exit separately')
        seal.write('resource_ledger.json', ledger, 262144)
        receipt = dict(schema='G13-B-D6-receipt-v1', authorization_commit=AUTH, run=run, status=checkpoint['status'],
                       counts=checkpoint['counts'], real_entries=checkpoint['real_entries'], scientific_results=checkpoint['scientific_results'],
                       inputs=dict(metadata=9, message_first_pass=sum(r['first_pass']=='PASS' for r in qualification['messages']),
                                   message_second_pass=sum(r['second_pass']=='PASS' for r in qualification['messages'])),
                       output_hashes=seal.hashes.copy(), failure=failure, old_FAIL_null='preserved', complete_G13='NOT_PASSED',
                       C_events_fits_fees=0, V_account=budget.used.copy(), S_account_before_receipt=seal_budget.used.copy(),
                       unknowns=['whole process peak','physical/implicit IO','exact full scans','exit tail until owner terminal observation'])
        seal.write('receipt.json', receipt, 16384)
        seal.write('artifact_hashes.json', dict(schema='G13-B-manifest-v1', authorization_commit=AUTH, files=seal.hashes.copy(),
                   manifest_self='self hash intentionally excluded; owner terminal hashes this file', input_cache_hashes=source_hashes if plan else None), 32768)
        print(json.dumps(dict(action='done', status=checkpoint['status'], counts=checkpoint['counts'],
                              V=budget.used, S=seal_budget.used, science=checkpoint['scientific_results'])), flush=True)
    return 0 if checkpoint['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
