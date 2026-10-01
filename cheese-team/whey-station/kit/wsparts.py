# Architectural parts on top of the kit (same API as the Wash Junction parts).
import math
PI = math.pi


class Parts:
    def __init__(self, K, team='C'):
        self.K = K; self.T = team

    def tm(self, base):
        return base + '_' + self.T

    # straight railing from (x0,z0) to (x1,z1) at floor y
    def rail(self, x0, z0, x1, z1, y, h=1.07, mat='Steel', panel=None, toe=True, col=True):
        K = self.K; L = math.hypot(x1 - x0, z1 - z0)
        if L < 0.05:
            return
        ang = math.atan2(z1 - z0, x1 - x0); n = max(1, math.ceil(L / 1.5)); cx, cz = (x0 + x1) / 2, (z0 + z1) / 2; ry = -ang
        for i in range(n + 1):
            t = i / n
            K.cyl(mat, x0 + (x1 - x0) * t, y, z0 + (z1 - z0) * t, 0.03, h, seg=8)
        K.at(cx, y + h, cz, ry); K.cyl(mat, -L / 2 - 0.03, 0, 0, 0.032, L + 0.06, axis='x', seg=8); K.pop()
        if panel:
            K.obox(panel, cx, y + 0.12 + (h - 0.24) / 2, cz, L, h - 0.24, 0.025, (0, ry, 0))
        else:
            K.at(cx, y + h * 0.52, cz, ry); K.cyl(mat, -L / 2, 0, 0, 0.022, L, axis='x', seg=6); K.pop()
        if toe:
            K.obox(mat, cx, y + 0.07, cz, L, 0.12, 0.015, (0, ry, 0))
        if col:
            K.col(min(x0, x1) - 0.06, y, min(z0, z1) - 0.06, max(x0, x1) + 0.06, y + h + 0.05, max(z0, z1) + 0.06)

    # stairs ascending along local +x from (x,z), frame rotated ry; kind 'steel' | 'conc'. Returns the run length.
    def stairs(self, x, z, ry, w, y0, y1, kind='steel', base=None, rail_sides=(-1, 1), rails=True, going=0.27):
        K = self.K; rise = y1 - y0; n = max(2, round(rise / 0.19)); r = rise / n; g = going; L = n * g; hw = w / 2
        K.at(x, 0, z, ry)
        for i in range(n):
            top = y0 + (i + 1) * r; a0 = i * g; a1 = (i + 1) * g + (-0.005 if i == n - 1 else 0.02)
            if kind == 'conc':
                K.box('Conc', a0, y0 if base is None else base, -hw, a1, top - 0.03, hw)
                K.box('AntiSlip', a0, top - 0.03, -hw, a1, top, hw)
                K.box('SafetyY', a0 - 0.006, top - 0.04, -hw + 0.05, a0 + 0.05, top + 0.006, hw - 0.05)
            else:
                K.box('Plate', a0, top - 0.05, -hw, a1, top, hw)
                K.box(self.tm('SteelT'), a0 - 0.01, top - 0.07, -hw, a0 + 0.04, top + 0.003, hw)
            K.col(a0, y0 if base is None else base, -hw, a1, top, hw)
        ang = math.atan2(rise, L); sl = math.hypot(rise, L)
        if kind == 'steel':
            for s in (-1, 1):
                K.obox('Steel', L / 2, y0 + rise / 2 - 0.09, s * (hw + 0.035), sl + 0.25, 0.3, 0.07, (0, 0, ang))
        if rails:
            for s in rail_sides:
                zz = s * (hw + (0.07 if kind == 'steel' else -0.08))
                K.obox('Steel', L / 2, y0 + rise / 2 + 0.95, zz, sl, 0.05, 0.05, (0, 0, ang))
                K.obox('Steel', L / 2, y0 + rise / 2 + 0.5, zz, sl, 0.04, 0.04, (0, 0, ang))
                for i in range(0, n + 1, 4):
                    a = min(L, i * g + 0.1); yy = y0 + min(n, i + 1) * r
                    K.cyl('Steel', a, yy, zz, 0.028, 0.98, seg=8)
                K.col(0, y0, zz - 0.05, L, y1 + 1.0, zz + 0.05)
        K.pop()
        return L

    def _B(self, axis, a0, b0, c0, a1, b1, c1, m, col=False):
        if axis == 'x':
            self.K.box(m, a0, b0, c0, a1, b1, c1, col=col)
        else:
            self.K.box(m, c0, b0, a0, c1, b1, a1, col=col)

    # frame trim around an opening in a wall (axis 'x' = wall along x at z=c)
    def opening(self, axis, s0, s1, c, t, y0, y1, mat='Steel', w=0.1, dp=0.04, faces=(1, -1), sill=False, record=True, sill_mat='Brushed'):
        if record:
            self.K.opening_rec(axis, s0, s1, c, t, y0, y1)
        for f in faces:
            z0 = c + f * t / 2; z1 = z0 + f * dp
            self._B(axis, s0 - w, y0, z0, s0, y1 + w, z1, mat); self._B(axis, s1, y0, z0, s1 + w, y1 + w, z1, mat)
            self._B(axis, s0, y1, z0, s1, y1 + w, z1, mat)
            if sill:
                self._B(axis, s0 - w * 1.5, y0 - 0.07, z0, s1 + w * 1.5, y0, z1 + f * 0.06, sill_mat)
        self._B(axis, s0, y0, c - t / 2, s0 + 0.02, y1, c + t / 2, mat)
        self._B(axis, s1 - 0.02, y0, c - t / 2, s1, y1, c + t / 2, mat)
        self._B(axis, s0, y1 - 0.02, c - t / 2, s1, y1, c + t / 2, mat)

    # window: frame, mullions, glass, sill, optional bars
    def window(self, axis, s0, s1, c, t, y0, y1, trim='Steel', pane=1.1, transom=False, open_=False, bars=False, col=True, inset=0.0):
        K = self.K
        self.opening(axis, s0, s1, c, t, y0, y1, mat=trim, w=0.08, sill=True, record=False)
        n = max(1, round((s1 - s0) / pane)); mid = c + inset
        for i in range(1, n):
            s = s0 + (s1 - s0) * i / n; self._B(axis, s - 0.03, y0, mid - 0.04, s + 0.03, y1, mid + 0.04, 'Steel')
        if transom:
            ty = y0 + (y1 - y0) * 0.68; self._B(axis, s0, ty - 0.03, mid - 0.04, s1, ty + 0.03, mid + 0.04, 'Steel')
        self._B(axis, s0, y0, mid - 0.04, s1, y0 + 0.05, mid + 0.04, 'Steel'); self._B(axis, s0, y1 - 0.05, mid - 0.04, s1, y1, mid + 0.04, 'Steel')
        if not open_:
            self._B(axis, s0, y0, mid - 0.006, s1, y1, mid + 0.006, 'Glass')
        if bars:
            s = s0 + 0.12
            while s < s1:
                self._B(axis, s - 0.012, y0, c + t / 2 + 0.02, s + 0.012, y1, c + t / 2 + 0.045, 'Steel'); s += 0.14
        if col and not open_:
            if axis == 'x':
                K.col(s0, y0, c - t / 2, s1, y1, c + t / 2)
            else:
                K.col(c - t / 2, y0, s0, c + t / 2, y1, s1)

    # CMU block wall with pilasters, cap and footing
    def cmu_wall(self, axis, s0, s1, c, t, h, holes=(), faces=(1, -1), y0=0.0):
        K = self.K
        K.wall('CMU', axis, s0, s1, c, t, y0, y0 + h, holes, col=True)
        self._B(axis, s0, y0 + h, c - t / 2 - 0.05, s1, y0 + h + 0.12, c + t / 2 + 0.05, 'Brushed', col=True)
        for f in faces:
            self._B(axis, s0, y0, c + f * t / 2, s1, y0 + 0.3, c + f * (t / 2 + 0.06), 'Conc')
        s = s0 + 0.25
        while s <= s1 - 0.1:
            if not any(s + 0.25 > hh[0] and s - 0.25 < hh[1] for hh in holes):
                for f in faces:
                    self._B(axis, s - 0.25, y0 + 0.3, c + f * t / 2, s + 0.25, y0 + h, c + f * (t / 2 + 0.12), 'CMU')
            s += 4

    def ibeam(self, x, z, y0, y1, w=0.3, mat='Steel', axis='z', base=True, col=True):
        K = self.K; f = 0.025
        if axis == 'x':
            K.box(mat, x - w / 2, y0, z - w / 2, x + w / 2, y1, z - w / 2 + f); K.box(mat, x - w / 2, y0, z + w / 2 - f, x + w / 2, y1, z + w / 2); K.box(mat, x - 0.012, y0, z - w / 2, x + 0.012, y1, z + w / 2)
        else:
            K.box(mat, x - w / 2, y0, z - w / 2, x - w / 2 + f, y1, z + w / 2); K.box(mat, x + w / 2 - f, y0, z - w / 2, x + w / 2, y1, z + w / 2); K.box(mat, x - w / 2, y0, z - 0.012, x + w / 2, y1, z + 0.012)
        if base:
            K.box('Steel', x - w / 2 - 0.08, y0, z - w / 2 - 0.08, x + w / 2 + 0.08, y0 + 0.03, z + w / 2 + 0.08)
        if col:
            K.col(x - w / 2, y0, z - w / 2, x + w / 2, y1, z + w / 2)

    # horizontal I-beam spanning along x (for ceilings); axis='z' spans along z at x=z param
    def hbeam(self, x0, x1, z, ytop, d=0.3, w=0.18, mat='Steel', axis='x'):
        K = self.K; f = 0.022
        if axis == 'x':
            K.box(mat, x0, ytop - f, z - w / 2, x1, ytop, z + w / 2); K.box(mat, x0, ytop - d, z - w / 2, x1, ytop - d + f, z + w / 2)
            K.box(mat, x0, ytop - d, z - 0.01, x1, ytop, z + 0.01)
        else:
            K.box(mat, z - w / 2, ytop - f, x0, z + w / 2, ytop, x1); K.box(mat, z - w / 2, ytop - d, x0, z + w / 2, ytop - d + f, x1)
            K.box(mat, z - 0.01, ytop - d, x0, z + 0.01, ytop, x1)

    # vertical pipe on a wall
    def downpipe(self, x, z, y0, y1, mat='Steel'):
        K = self.K
        K.cyl(mat, x, y0 + 0.3, z, 0.06, y1 - y0 - 0.3, seg=10)
        K.cyl(mat, x, y0, z, 0.06, 0.3, seg=10)
        for yy in range(int(y0) + 1, int(y1), 2):
            K.cyl(mat, x, yy, z, 0.075, 0.06, seg=10)
