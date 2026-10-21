"""Shape-aware differential cases for the kernels beyond the flat-vector suite.

Packed inputs use the original NEON tile sizes at every RVV VLEN. The oracle
receives the identical bytes; no hand-written RVV kernel or scalar substitute
is used. Config words and buffer descriptors are recorded in replay JSON.
"""
from dataclasses import dataclass
import random
import struct

MAGIC = 0x53425431
LENGTHS = [1, 2, 3, 4, 7, 8, 9, 15, 16, 17, 31, 32, 33, 63, 64, 65,
           127, 128, 129, 255, 256, 257, 2047, 2048, 2049]


@dataclass(frozen=True)
class BufferAdapter:
    body: str

    def header(self):
        return 'static void invoke(uint32_t c[32], Buffer b[8]) {\n' + self.body + '\n}\n'


def minmax(record='xnn_f32_minmax_params'):
    return f'struct {record} p = {{0}}; p.scalar.min = F(24); p.scalar.max = F(25);\n'


ADAPTERS = {}
def adapter(name, body):
    ADAPTERS[name] = BufferAdapter(body)

adapter('f32-f16-vcvt', 'TEST_ENTRY(c[0]*4, B(0), B(1), NULL);')
adapter('f32-vcmul', 'struct xnn_f32_default_params p = {0}; TEST_ENTRY(c[0]*4, B(0), B(1), B(2), &p);')
adapter('f32-vmulc', 'struct xnn_f32_default_params p = {0}; TEST_ENTRY(c[0]*4, B(0), B(1), B(2), &p);')
adapter('f32-vlrelu', 'struct xnn_f32_lrelu_params p = {0}; p.scalar.slope = F(24); TEST_ENTRY(c[0]*4, B(0), B(1), &p);')
for prefix, typ in [('qs8', 'int8_t'), ('qu8', 'uint8_t')]:
    adapter(prefix+'-f32-vcvt', f'struct xnn_{prefix}_f32_cvt_params p = {{0}}; p.scalar.zero_point = S(24); p.scalar.scale = F(25); TEST_ENTRY(c[0], B(0), B(1), &p);')
    adapter(prefix+'-rdsum', 'struct xnn_qs8_rsum_params p = {0}; TEST_ENTRY(c[0], c[1], B(0), c[2], B(1), B(2), &p);')
adapter('qs8-vcvt', 'struct xnn_qs8_cvt_params p = {0}; p.scalar.input_zero_point = S(24); p.scalar.multiplier = S(25); p.scalar.output_zero_point = S(26); TEST_ENTRY(c[0], B(0), B(1), &p);')
adapter('qs8-vlrelu', 'struct xnn_qs8_lrelu_params p = {0}; p.scalar.input_zero_point = S(24); p.scalar.positive_multiplier = S(25); p.scalar.negative_multiplier = S(26); p.scalar.output_zero_point = S(27); TEST_ENTRY(c[0], B(0), B(1), &p);')
adapter('qs8-vmul-minmax-fp32', '''union xnn_qs8_mul_minmax_params p = {0};
 p.scalar.a_zero_point = S(24); p.scalar.b_zero_point = S(25); p.scalar.scale = F(26);
 p.scalar.output_zero_point = S(27); p.scalar.output_min = S(28); p.scalar.output_max = S(29);
 TEST_ENTRY(c[0], B(0), B(1), B(2), &p);''')
adapter('f32-raddstoreexpminusmax', 'TEST_ENTRY(c[0]*4, B(0), B(1), B(2), B(3), NULL);')
adapter('x32-transposec', 'TEST_ENTRY(B(0), B(1), c[2], c[3], c[0], c[1]);')
adapter('x32-packw-gemm-goi', 'TEST_ENTRY(c[0], c[1], c[2], 2, 1, 1, B(0), c[4] ? B(1) : NULL, NULL, B(2), c[3], NULL);')
adapter('f32-dwconv2d-chw', minmax()+'TEST_ENTRY(c[0], c[1]*4, B(0), B(1), B(2), B(3), 1, &p);')
adapter('f32-conv-hwc2chw', minmax()+'TEST_ENTRY(c[0], c[1], c[2], c[3], B(0), B(1), B(2), B(3), c[4], c[5], c[6], c[7], &p);')
for name in ['f32-argmaxpool', 'f32-maxpool', 'f32-dwconv-minmax']:
    body = 'const float** ptr = (const float**)pointers(&b[0], &b[1], &b[2]);\n'
    if name == 'f32-argmaxpool':
        body += 'TEST_ENTRY(c[0], c[1], c[2], ptr, c[3], c[4], B(3), B(4), c[1]*sizeof(void*), c[5], c[5]);'
    elif name == 'f32-maxpool':
        body += minmax()+'TEST_ENTRY(c[0], c[1], c[2], ptr, c[3], c[4], B(3), c[1]*sizeof(void*), c[5], &p);'
    else:
        body += minmax()+'TEST_ENTRY(c[2], c[0], ptr, B(4), B(3), 3*sizeof(void*), c[5]-c[2]*4, c[3], c[4], B(2), &p);'
    adapter(name, body+'\nfree(ptr);')
adapter('f32-gemm-minmax', minmax()+'TEST_ENTRY(c[0], c[1], c[2]*4, B(0), c[3], B(1), B(2), c[4], c[5], &p);')
adapter('f32-igemm-minmax', minmax()+'''const float** ptr = (const float**)pointers(&b[0], &b[1], &b[2]);
 TEST_ENTRY(1, c[1], c[2]*4, c[0]*sizeof(void*), ptr, B(3), B(4), c[4], c[5], c[3], B(2), &p); free(ptr);''')
for name in ['qd8-f32-qc4w-gemm-minmax', 'qd8-f32-qc8w-gemm-minmax', 'qd8-f32-qc8w-igemm-minmax', 'qs8-qc8w-gemm-minmax-fp32']:
    if name.startswith('qs8'):
        body = '''union xnn_qs8_qc8w_conv_minmax_params p = {0};
 p.fp32_neon.magic_bias = 12582912.0f; p.fp32_neon.magic_bias_less_output_zero_point = 0x4B400000-S(26);
 p.fp32_neon.output_min = S(24); p.fp32_neon.output_max = S(25);
 TEST_ENTRY(1, c[1], c[2], B(0), c[3], B(1), B(2), c[4], c[5], &p);'''
    else:
        body = minmax('xnn_f32_qc4w_minmax_params' if 'qc4w' in name else 'xnn_f32_minmax_params')
        body += 'struct xnn_qd8_quantization_params q = { .zero_point = S(26), .inv_scale = F(27) };\n'
        if 'igemm' in name:
            body += '''const int8_t** ptr = (const int8_t**)pointers(&b[0], &b[1], &b[2]);
 TEST_ENTRY(1, c[1], c[2], c[0]*sizeof(void*), ptr, B(3), B(4), c[4], c[5], c[3], B(2), B(5), &p, &q); free(ptr);'''
        else:
            body += 'TEST_ENTRY(1, c[1], c[2], B(0), c[3], B(1), B(2), c[4], c[5], &p, &q);'
    adapter(name, body)
adapter('f32-spmm-minmax', minmax()+'TEST_ENTRY(c[0]*4, c[1], (float*)B(0)+c[3], B(1), B(2), B(3), B(4), c[2], &p);')


def pack(fmt, values):
    return struct.pack('<'+str(len(values))+fmt, *values)


def word(f):
    return struct.unpack('<I', struct.pack('<f', f))[0]


class CaseBuilder:
    def __init__(self, name, seed, index, pattern, domain, rng):
        self.case = dict(kernel=name, seed=seed, index=index, pattern=pattern,
                         float_domain=domain, protocol='buffers-v1')
        self.c = [0]*32
        self.buffers = []
        self.rng, self.pattern = rng, pattern

    def add(self, label, data, writable=False):
        self.buffers.append((dict(label=label, size=len(data), writable=int(writable)), data))

    def out(self, label, size, initial=None):
        self.add(label, bytes([0xA5])*size if initial is None else initial, True)

    def floats(self, n, *, broad=False):
        # Accumulation kernels use bounded finite numbers to avoid overflow and
        # the compiler-dependent competing-NaN FMA operand-order ambiguity.
        if broad:
            edges = [0, 0x80000000, 1, 0x80000001, 0x007fffff, 0x00800000,
                     0x3f800000, 0xbf800000, 0x7f7fffff, 0xff7fffff,
                     word(2**-24), word(2**-14), word(65504), word(65520),
                     word(1+2**-11), word(1+3*2**-11)]
            if self.case['float_domain'] == 'ieee':
                edges += [0x7f800000, 0xff800000, 0x7fc12345, 0xffc23456, 0x7f812345]
            if self.pattern == 'zero': return pack('I', [0x80000000 if i%2 else 0 for i in range(n)])
            if self.pattern == 'edges': return pack('I', [edges[i%len(edges)] for i in range(n)])
            words = [self.rng.getrandbits(32) for _ in range(n)]
            if self.case['float_domain'] == 'finite':
                words = [v ^ 0x00800000 if v & 0x7f800000 == 0x7f800000 else v for v in words]
            return pack('I', words)
        vals = [0., -0., -2., -.5, .5, 1., 2., 3.25]
        return pack('f', [0. if self.pattern == 'zero' else vals[i%len(vals)] if self.pattern == 'edges'
                          else self.rng.uniform(-4, 4) for i in range(n)])

    def integers(self, n):
        edges = [0, 127, 128, 255, 1, 254]
        return bytes(0 if self.pattern == 'zero' else edges[i%6] if self.pattern == 'edges'
                     else self.rng.getrandbits(8) for i in range(n))

    def finish(self):
        self.c = [v & 0xffffffff for v in self.c]
        payload = pack('I', [MAGIC]+self.c+[len(self.buffers)])
        for desc, data in self.buffers:
            payload += pack('I', [desc['size'], desc['writable']])+data
        return dict(self.case, config=self.c, buffers=[b[0] for b in self.buffers], input_hex=payload.hex())


def validate_case(case):
    if case.get('protocol') != 'buffers-v1': raise ValueError('invalid buffer protocol')
    cfg, buffers = case['config'], case['buffers']
    if len(cfg) != 32 or any(type(v) is not int or not 0 <= v <= 0xffffffff for v in cfg):
        raise ValueError('invalid buffer config')
    if not 1 <= len(buffers) <= 8: raise ValueError('invalid buffer count')
    data = bytes.fromhex(case['input_hex'])
    if data[:136] != pack('I', [MAGIC]+cfg+[len(buffers)]): raise ValueError('buffer header mismatch')
    offset = 136
    for b in buffers:
        if type(b['size']) is not int or not 1 <= b['size'] <= 16777216 or b['writable'] not in (0, 1):
            raise ValueError('invalid buffer descriptor')
        if data[offset:offset+8] != pack('I', [b['size'], b['writable']]): raise ValueError('buffer descriptor mismatch')
        offset += 8+b['size']
    if offset != len(data): raise ValueError('invalid buffer input byte count')
    if not any(b['writable'] for b in buffers): raise ValueError('missing output buffer')
    return data


def output_size(case):
    return sum(b['size'] for b in case['buffers'] if b['writable'])


def make_cases(name, seed, random_cases, domain):
    rng = random.Random(f'salty-buffer-v1:{name}:{seed}')
    cases = []
    for index in range(50+random_cases):
        pattern = ('zero' if index%2 == 0 else 'edges') if index < 50 else 'random'
        t = index//2 if index < 50 else index
        n = LENGTHS[t] if index < 50 else rng.randint(1, 4096)
        b = CaseBuilder(name, seed, index, pattern, domain, rng)
        c = b.c
        c[24:26] = [word(-16 if t%2 else -1e6), word(16 if t%2 else 1e6)]
        # A rotating dimension grid hits tile boundaries without a Cartesian
        # explosion; random cases independently vary every shape dimension.
        def dim(values, shift=0):
            return values[(t+shift)%len(values)] if index < 50 else rng.choice(values)
        def gap(): return dim([0, 1, 3])
        def zp(): return rng.randint(-128, 127)
        def scale(): return word(rng.choice([2**-12, 2**-8, .125, .5, 1., 1.75]))
        if name in ['f32-f16-vcvt', 'f32-vcmul', 'f32-vmulc', 'f32-vlrelu']:
            c[0] = n
            count = 2*n if name == 'f32-vcmul' else n
            b.add('input_a', b.floats(count+32, broad=True))
            if name in ['f32-vcmul', 'f32-vmulc']:
                b.add('input_b', b.floats(count+32 if name == 'f32-vcmul' else 1, broad=True))
            if name == 'f32-vlrelu': c[24] = word(rng.choice([0., -0., .01, .5, 1., -1.]))
            b.out('output', count*(2 if name == 'f32-f16-vcvt' else 4))
        elif name in ['qs8-f32-vcvt', 'qu8-f32-vcvt', 'qs8-vcvt', 'qs8-vlrelu', 'qs8-vmul-minmax-fp32']:
            c[0] = n
            b.add('input_a', b.integers(n+32))
            if name == 'qs8-vmul-minmax-fp32':
                b.add('input_b', b.integers(n+32))
                c[24:30] = [zp(), zp(), scale(), zp(), rng.randint(-128, -1), rng.randint(0, 127)]
            elif name.endswith('f32-vcvt'):
                c[24:26] = [rng.randint(0, 255) if name.startswith('qu8') else zp(), scale()]
            elif name == 'qs8-vcvt': c[24:27] = [zp(), rng.choice([1, 128, 192, 256, 512, 32767]), zp()]
            else: c[24:28] = [zp(), rng.choice([128, 256, 512, 32767]), rng.choice([-256, 0, 1, 128, 256]), zp()]
            b.out('output', n*(4 if name.endswith('f32-vcvt') else 1))
        elif name.endswith('-rdsum'):
            rows = dim([1, 2, 6, 7, 8, 14, 251, 252, 253, 504, 505])
            channels = dim([1, 2, 3, 4, 7, 8, 9, 15, 16, 17, 31, 32, 33], 3)
            stride = channels+gap()
            c[:3] = [rows, channels, stride]
            b.add('input', b.integers(rows*stride+32)); b.add('zero', bytes(channels+32))
            initial = [rng.randint(-1000, 1000) if name.startswith('qs8') else rng.randint(0, 1000) for _ in range(channels)]
            b.out('accumulator', channels*4, pack('i', initial))
        elif name == 'f32-raddstoreexpminusmax':
            c[0] = n
            values = [0.]*n if pattern == 'zero' else [-(i%81) for i in range(n)] if pattern == 'edges' else [rng.uniform(-80, 0) for _ in range(n)]
            maximum = max(values)
            b.add('input', pack('f', values+[0.]*32)); b.add('maximum', pack('f', [maximum]))
            b.out('exponentials', n*4); b.out('sum', 4)
        elif name == 'x32-transposec':
            width, height = dim([1, 2, 3, 4, 7, 8, 9, 16, 17]), dim([1, 3, 2, 5, 8, 9], 2)
            ins, outs = (width+gap())*4, (height+gap())*4
            c[:4] = [width, height, ins, outs]
            b.add('input', b.integers(height*ins+32)); b.out('output', width*outs)
        elif name == 'x32-packw-gemm-goi':
            groups, nc, kc = dim([1, 2, 3]), dim([1, 2, 3, 7, 8, 9], 1), dim([1, 2, 3, 4, 7, 8, 9], 3)
            extra = gap()*4
            c[:5] = [groups, nc, kc, extra, t%2]
            b.add('weights', b.integers(groups*nc*kc*4)); b.add('bias', b.integers(groups*nc*4))
            b.out('packed_weights', groups*((nc+1)//2)*(8*(kc+1)+extra))
        elif name in ['f32-argmaxpool', 'f32-maxpool', 'f32-dwconv-minmax']:
            pixels, taps = dim([1, 2, 3, 5]), dim([1, 2, 8, 9, 10, 17, 18, 19, 27, 28])
            if name == 'f32-dwconv-minmax': taps = 3
            channels = dim([1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17], 2)
            offset, pixel_stride = gap()*4, dim([0, 4, 12], 1)
            row = offset+pixel_stride*(pixels-1)+(channels+8)*4
            c[:6] = [pixels, taps, channels, offset, pixel_stride, (channels+gap())*4]
            b.add('input', b.floats(pixels*taps*row//4))
            offsets = [i*row for i in range(pixels*taps)]
            rng.shuffle(offsets)
            if name == 'f32-dwconv-minmax':
                offsets = [0xffffffff if (i+t)%4 == 0 else o for i,o in enumerate(offsets)]
            b.add('pointer_offsets', pack('I', offsets)); b.add('zero', bytes((channels+32)*4))
            b.out('output', pixels*c[5])
            if name == 'f32-argmaxpool': b.out('indices', pixels*c[5])
            if name == 'f32-dwconv-minmax': b.add('packed_weights', b.floats(((channels+3)//4)*16))
        elif name == 'f32-dwconv2d-chw':
            height, width = dim([1, 2, 3, 4, 5, 6, 7]), dim([1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17], 2)
            c[:2] = [height, width]
            b.add('input', b.floats(height*width+32)); b.add('weights', b.floats(10))
            b.add('zero', bytes((width+32)*4)); b.out('output', height*width*4)
        elif name == 'f32-conv-hwc2chw':
            height, width, channels = dim([2, 3, 4, 5, 6, 7, 9]), dim([1, 2, 3, 4, 5, 7, 8, 9], 2), dim([1, 2, 3, 4, 5, 7, 8, 9], 4)
            top = t%2
            oh, ow = (height+top)//2, (width+1)//2
            start = dim([0, max(0, oh-1)])
            end = oh if t%3 else start+1
            hs = (ow+gap())*4; cs = oh*hs+gap()*4
            c[:8] = [height, width, start, end, top, channels, hs, cs]
            b.add('input', b.floats(height*width*3+32)); b.add('zero', bytes((width*3+32)*4))
            b.add('packed_weights', b.floats(((channels+3)//4)*112)); b.out('output', channels*cs)
        elif name == 'f32-spmm-minmax':
            m, nc, k = dim([1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17]), dim([1, 2, 3, 5], 1), dim([1, 2, 4, 7], 2)
            lists = [sorted(rng.sample(range(k), rng.randint(0, k))) for _ in range(nc)]
            if pattern == 'zero': lists = [[] for _ in range(nc)]
            flat = [v for vs in lists for v in vs]
            deltas = [(flat[(i+1)%len(flat)]-v)*m*4 for i,v in enumerate(flat)]
            weights = b''.join(b.floats(1+len(vs)) for vs in lists)
            c[:4] = [m, nc, (m+gap())*4, flat[0]*m if flat else 0]
            b.add('input', b.floats(k*m+32)); b.add('packed_weights', weights)
            b.add('byte_deltas', pack('i', deltas or [0])); b.add('nonzero_counts', pack('I', [len(vs) for vs in lists]))
            b.out('output', nc*c[2])
        else:
            # Dense and indirect GEMM: bias / K-major weight vectors / scales
            # and optional float bias, repeated per original NEON channel tile.
            indirect = 'igemm' in name
            floating = name.startswith('f32')
            qc4 = 'qc4w' in name
            qs8 = name.startswith('qs8')
            nr = 16 if qc4 else 8
            nc, k = dim([1, 2, 3, 4, 7, 8, 9, 15, 16, 17, 31, 32, 33]), dim([1, 2, 3, 4, 7, 8, 9, 15, 16, 17], 3)
            mr = dim([1, 2, 3, 4]) if name == 'f32-gemm-minmax' else 1
            taps = dim([1, 2, 3, 5], 1) if indirect else 1
            item = 4 if floating else 1
            offset = gap()*item if indirect else 0
            row = offset+(k+32)*item
            cn = (nr+gap())*(1 if qs8 else 4)
            cm = ((nc+nr-1)//nr)*cn+gap()*4
            c[:6] = [taps if indirect else mr, nc, k, offset if indirect else row, cm, cn]
            qzp = zp()
            if not floating:
                c[26:28] = [qzp, scale()]
                if qs8: c[24:27] = [rng.randint(-128,-1), rng.randint(0,127), zp()]
            inputs = b.floats((taps if indirect else mr)*row//4) if floating else b.integers((taps if indirect else mr)*row)
            b.add('input', inputs)
            if indirect:
                offsets = [i*row if (i+t)%3 else 0xffffffff for i in range(taps)]
                rng.shuffle(offsets)
                b.add('pointer_offsets', pack('I', offsets))
                b.add('zero', bytes((k+32)*item))
            weights = b''
            for block in range((nc+nr-1)//nr):
                if floating:
                    weights += b.floats(nr*(1+taps*k))
                else:
                    # QC4 nibbles are signed; an odd K is padded with zero.
                    padded_k = (k+1)//2*2 if qc4 else k
                    vals = [[rng.randint(-8,7) if qc4 else rng.randint(-127,127) for _ in range(nr)] for _ in range(taps*k)]
                    if pattern == 'zero': vals = [[0]*nr for _ in vals]
                    if qc4 and padded_k != k: vals.append([0]*nr)
                    sums = [-(16 if qc4 else 1)*sum(v[j] for v in vals) for j in range(nr)]
                    weights += pack('i', [rng.randint(-1000,1000) for _ in range(nr)] if qs8 else sums)
                    if qc4:
                        weights += bytes((vals[i][j]&15)|((vals[i+1][j]&15)<<4) for i in range(0,padded_k,2) for j in range(nr))
                    else: weights += bytes(v&255 for rowvals in vals for v in rowvals)
                    weights += pack('f', [rng.choice([.0001, .001, .01, .1]) for _ in range(nr)])
                    if not qs8: weights += b.floats(nr)
            b.add('packed_weights', weights)
            b.out('output', mr*cm)
            if indirect and not floating: b.add('zero_data', bytes([qzp&255])*(k+32))
        cases.append(b.finish())
    return cases
