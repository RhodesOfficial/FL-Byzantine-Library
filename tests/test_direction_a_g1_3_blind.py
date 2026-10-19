"""Small B-only same-cycle suite; never imports/reruns the 92-case A suite."""
import io
import struct
import zipfile


def archive(code, storage=b'', extra=None, compressed=False):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED) as z:
        z.writestr('fixture/data.pkl', code)
        z.writestr('fixture/version', b'3\n')
        z.writestr('fixture/byteorder', b'little')
        if storage:
            z.writestr('fixture/data/0', storage)
        if extra:
            z.writestr('fixture/'+extra, b'x')
    return stream.getvalue()


def minimal_tensor(count=10, shape=10):
    # PROTO2, rebuild_tensor_v2(storage FloatStorage key0 cpu count, offset0,
    # (shape,), (1,), requires_grad=False, OrderedDict()). No executable pickle.
    def text(s):
        b = s.encode(); return b'X'+struct.pack('<I', len(b))+b
    pid = b'('+text('storage')+b'ctorch\nFloatStorage\n'+text('0')+text('cpu')+b'J'+struct.pack('<i', count)+b'tQ'
    return b'\x80\x02ctorch._utils\n_rebuild_tensor_v2\n('+pid+b'K\x00K'+bytes([shape])+b'\x85K\x01\x85\x89ccollections\nOrderedDict\n)RtR.'


def run_suite(api, budget, results):
    def case(name, fn, expected='PASS', rejection=None):
        row = dict(name=name, expected=expected, status='RUNNING')
        results.append(row)
        try:
            actual = fn()
            if rejection:
                raise AssertionError('expected refusal '+rejection)
            row.update(status='PASS', actual=actual)
        except (api.Gate, ValueError, KeyError, IndexError, struct.error, zipfile.BadZipFile) as exc:
            if not rejection or rejection not in str(exc):
                row.update(status='FAIL', actual=type(exc).__name__+':'+str(exc))
                raise
            row.update(status='PASS', actual=type(exc).__name__+':'+str(exc), zero_restricted_access=True)
    budget.charge('B synthetic envelope', scans=16000, ops=100000000)
    def legal():
        d = api.Decoder(budget)
        value, storages = d.decode(archive(minimal_tensor(), b'\0'*40))
        assert isinstance(value, api.Tensor) and value.shape == (10,) and value.count == 10
        assert storages == {'0': b'\0'*40}
        return dict(shape=[10], count=10, storage_bytes=d.storage_bytes, tokens=d.tokens)
    case('decoder/minimum-legal-inert-tensor', legal)
    case('decoder/format', lambda: api.Decoder(budget).decode(b'not-a-zip'), rejection='ARCHIVE_FORMAT')
    case('decoder/compression', lambda: api.Decoder(budget).decode(archive(b'\x80\x02}.', compressed=True)), rejection='ARCHIVE_COMPRESSION_ALIAS')
    case('decoder/global', lambda: api.Decoder(budget).decode(archive(b'\x80\x02cos\nsystem\n.')), rejection='PICKLE_GLOBAL_ALLOWLIST')
    case('decoder/member-allowlist', lambda: api.Decoder(budget).decode(archive(b'\x80\x02}.', extra='evil')), rejection='ARCHIVE_ALLOWLIST')
    case('decoder/declared-storage-size', lambda: api.Decoder(budget).decode(archive(minimal_tensor(), b'\0'*44)), rejection='STORAGE_DECLARED_SIZE')
    case('decoder/storage-overflow', lambda: api.Decoder(budget).decode(archive(minimal_tensor(2147483647))), rejection='ACCOUNT_TYPE_RANGE')
    case('decoder/shape', lambda: api.Decoder(budget).decode(archive(minimal_tensor(11,11), b'\0'*44)), rejection='TENSOR_SHAPE')
    case('decoder/string-length', lambda: api.Decoder(budget).decode(archive(b'\x80\x02X'+struct.pack('<I',1025)+b'x'*1025+b'.')), rejection='PICKLE_STRING')
    case('decoder/depth', lambda: api.Decoder(budget).decode(archive(b'\x80\x02'+b'('*25)), rejection='PICKLE_DEPTH')
    case('decoder/raw-cap', lambda: api.Decoder(budget).decode(b'x'*1929209), rejection='ACCOUNT_TYPE_RANGE')
    case('integer/pre-product-width', lambda: api.mul(1 << 4095, 2), rejection='INTEGER_WIDTH_BEFORE_PRODUCT')
    case('integer/pre-shift-width', lambda: api.shift(1 << 4095, 1), rejection='INTEGER_WIDTH_BEFORE_SHIFT')
    case('binary32/nonfinite', lambda: api.scaled32(struct.pack('<I',0x7f800000)), rejection='NONFINITE_BINARY32')
    def f32():
        values = api.scaled32(struct.pack('<4I',0,0x80000000,1,0x3f800000))
        assert values == [0,0,1,1 << 149]
        return 'signed zeros=0, minimum subnormal=1/2^149, one exact'
    case('binary32/exact-values', f32)
    case('interval/near-zero-unresolved', lambda: api.divide((1,2),(0,1)), rejection='SCALE_INTERVAL_TOUCHES_ZERO')
    def guarded():
        b = api.Account('V1')
        # Same Account.charge used by all real I/O. Account rejection occurs
        # before touching a sentinel; it leaves usage unchanged atomically.
        zero = 0
        for value in (True, None, -1, 1.5, '1', 167772161):
            try:
                b.charge('reject sentinel', read=value)
                zero += 1
            except api.Gate:
                pass
        assert zero == 0 and b.used['read'] == 0
        b.lease()
        try:
            b.lease()
        except api.Gate:
            pass
        else: raise AssertionError('duplicate lease accepted')
        b.settle()
        try:
            b.settle()
        except api.Gate:
            pass
        else: raise AssertionError('duplicate settlement accepted')
        return dict(zero_accesses=zero, invalids=6, duplicate_lease='refused', duplicate_settle='refused')
    case('account/type-quota-duplicate-refusal', guarded)
    def isolation():
        a = api.Access(budget, [])
        for p in ('F/mechanism.json','checkpoints/model.pt','../outside'):
            try: a.read(p, 1)
            except api.Gate as exc: assert str(exc) == 'ACCESS_SCHEMA_BEFORE_STAT'
            else: raise AssertionError('forbidden stat/read')
        assert a.records == []
        return dict(denied=3, zero_accesses=True)
    case('blind/access-schema', isolation)
    def failure_seal():
        # Exercise the actual Seal.write path against an in-memory filesystem;
        # no extra output or independent helper launch, even on injected failure.
        class File:
            value = None
            def exists(self): return self.value is not None
            def write_bytes(self, raw): self.value = raw
            def read_bytes(self): return self.value
        class Directory:
            def __init__(self): self.file = File()
            def __truediv__(self, name): return self.file
        directory = Directory(); closed = False
        try:
            raise ValueError('INJECTED_BEFORE_SCIENCE')
        except ValueError:
            pass
        finally:
            s = api.Seal(directory, api.Account('S1'))
            s.write('failure.json', {'status':'FAIL','new_scientific_results':0},128)
            assert s.hashes['failure.json']['readback'] == 'PASS'
            closed = True
        assert closed
        return dict(injected='INJECTED_BEFORE_SCIENCE', actual_seal_path='PASS', independent_readback='PASS')
    case('failure/actual-seal-finally', failure_seal)
    unit = 1 << 149
    for h in (1290,12900):
        def graph(kind, h=h):
            a, b = [0]*h, [0]*h
            if kind == 'orthogonal': a[0], b[-1] = unit, unit
            elif kind in ('single','identical'): a[0], a[-1] = 3*unit, 4*unit; b = a.copy()
            elif kind == 'opposite': a[0], b[0] = unit,-unit
            elif kind == 'near': a[0], b[0] = 1,2
            vectors = [a] if kind == 'single' else [a,b]
            counts = [2] if kind == 'single' else [1,1]
            r = api.metric(counts,vectors,h,budget)
            expected_D_square = {'orthogonal':2*unit*unit,'single':0,'identical':0,'zero':0,'opposite':4*unit*unit,'near':1}[kind]
            assert max(r['_pair_squares'],default=0) == expected_D_square
            # Independent Q256 source root sum and distance root; each square is
            # checked by integer inequalities in oracle256, then ratio propagation.
            source = [api.oracle256(x) for x in r['_norm_squares']]
            N = sum(counts)
            sl = sum(n*v[0] for n,v in zip(counts,source))//N
            sh = -((-sum(n*v[1] for n,v in zip(counts,source)))//N)
            d = api.oracle256(expected_D_square)
            if sh == 0:
                oracle = (0,0)
            else:
                oracle = ((d[0] << 256)//(N*sh), -((-(d[1] << 256))//(N*sl)))
            got = r['_tau']
            assert got is not None and (got[0] << 64) <= oracle[0] <= oracle[1] <= (got[1] << 64)
            if kind == 'orthogonal':
                assert r['_S'] == (api.Q,api.Q)
                assert oracle[0]**2 <= (1 << 512)//2 <= oracle[1]**2
            if kind in ('single','identical'):
                assert r['_S'] == (5*api.Q,5*api.Q) and got == (0,0)
            if kind == 'zero': assert r['degenerate']=='STRUCTURAL_ALL_ZERO'
            if kind == 'opposite': assert got == (api.Q,api.Q)
            assert r['uniform']['d_exact_zero'] and r['replacement']['all_squared_order_checks'] and r['replacement']['maximum_equality']
            return dict(expected=dict(D_square_scaled=str(expected_D_square),uniform_d=0,signs=[1,-1]),
                        actual=dict(S=r['S'],tau=r['tau'],degenerate=r['degenerate']),
                        oracle_Q256=[format(oracle[0],'x'),format(oracle[1],'x')], interval_contains_oracle=True)
        for kind in ('orthogonal','single','identical','zero','opposite','near'):
            case(f'Q192-v-independent-Q256/{h}/{kind}',lambda k=kind: graph(k))
        case(f'illegal-dimension/{h}', lambda: api.metric([1],[[0]*h],h+1,budget), rejection='METRIC_SHAPE')
        case(f'illegal-count/{h}', lambda: api.metric([0],[[0]*h],h,budget), rejection='METRIC_COUNT')
        def denominator(h=h):
            C=10 if h==1290 else 100
            rows=[{'_tau':(api.Q,api.Q)} for _ in range(C)]
            tail=list(range((2*C)//3,C))
            assert api.macro(rows,list(range(C)),C)==(api.Q,api.Q)
            assert api.macro(rows,tail,len(tail))==(api.Q,api.Q)
            rows[-1]['_tau']=None
            assert api.macro(rows,list(range(C)),C) is None and api.macro(rows,tail,len(tail)) is None
            return dict(all_denominator=C,tail_denominator=len(tail),missing='null, fixed denominator retained')
        case(f'fixed-macro-denominator/{h}',denominator)
    assert results and all(row['status']=='PASS' for row in results)
    return results
