import math
import cairo

# Mannequin palette (matte neutral gray)
SK_HI = (0.88, 0.885, 0.895)
SK_BASE = (0.70, 0.71, 0.73)
SK_SH = (0.42, 0.43, 0.46)
SK_DEEP = (0.28, 0.29, 0.32)
SHORTS = (0.14, 0.15, 0.17)
SHORTS_HI = (0.26, 0.27, 0.30)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def mul(c, k):
    return tuple(clamp(v * k) for v in c)


def skin_grad(p0, p1, dark=1.0):
    """Linear gradient across a limb (p0 -> p1 is the cross axis)."""
    g = cairo.LinearGradient(p0[0], p0[1], p1[0], p1[1])
    g.add_color_stop_rgb(0.0, *mul(SK_SH, dark))
    g.add_color_stop_rgb(0.28, *mul(SK_HI, dark))
    g.add_color_stop_rgb(0.62, *mul(SK_BASE, dark))
    g.add_color_stop_rgb(1.0, *mul(SK_DEEP, dark))
    return g


def capsule_path(ctx, p0, p1, r0, r1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / L, dx / L
    an = math.atan2(ny, nx)
    ctx.new_path()
    ctx.move_to(p0[0] + nx * r0, p0[1] + ny * r0)
    ctx.line_to(p1[0] + nx * r1, p1[1] + ny * r1)
    ctx.arc_negative(p1[0], p1[1], r1, an, an - math.pi)
    ctx.line_to(p0[0] - nx * r0, p0[1] - ny * r0)
    ctx.arc_negative(p0[0], p0[1], r0, an + math.pi, an)
    ctx.close_path()
    return nx, ny


def capsule(ctx, p0, p1, r0, r1, dark=1.0, color=None):
    nx, ny = capsule_path(ctx, p0, p1, r0, r1)
    if color is not None:
        ctx.set_source_rgb(*color)
    else:
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        r = max(r0, r1)
        # light from upper-left: orient gradient so highlight is on the lit side
        if nx * -0.6 + ny * -0.8 < 0:
            nx, ny = -nx, -ny
        ctx.set_source(skin_grad((mx + nx * r, my + ny * r), (mx - nx * r, my - ny * r), dark))
    ctx.fill()


def ellipse(ctx, cx, cy, rx, ry, rot=0.0):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(rot)
    ctx.scale(rx, ry)
    ctx.new_path()
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def ik2(root, target, l1, l2, bend=1):
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(dx, dy)
    d = clamp(d, abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)
    a = math.atan2(dy, dx)
    cosA = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    A = math.acos(clamp(cosA, -1, 1))
    ang = a + bend * A
    j = (root[0] + l1 * math.cos(ang), root[1] + l1 * math.sin(ang))
    # recompute actual end
    ex = j[0] + l2 * math.cos(math.atan2(target[1] - j[1], target[0] - j[0]))
    ey = j[1] + l2 * math.sin(math.atan2(target[1] - j[1], target[0] - j[0]))
    return j, (ex, ey)


def smooth_closed(ctx, pts):
    """Catmull-Rom closed spline through pts."""
    n = len(pts)
    ctx.new_path()
    ctx.move_to(*pts[0])
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        ctx.curve_to(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    ctx.close_path()


# ---------------------------------------------------------------- FRONT VIEW

def front_dims(f, m):
    return dict(
        sh=112 + 26 * m,
        nw=22 + 8 * m,
        lat=98 + 24 * m - 2 * f,
        w=78 + 50 * f + 5 * m,
        hw=94 + 14 * f,
    )


def draw_head_front(ctx, cx, cy):
    # ears
    for s in (-1, 1):
        ellipse(ctx, cx + s * 49, cy + 4, 9, 16)
        ctx.set_source_rgb(*SK_SH)
        ctx.fill()
    ellipse(ctx, cx, cy, 50, 64)
    g = cairo.RadialGradient(cx - 16, cy - 22, 6, cx, cy, 70)
    g.add_color_stop_rgb(0, *SK_HI)
    g.add_color_stop_rgb(0.55, *SK_BASE)
    g.add_color_stop_rgb(1, *SK_SH)
    ctx.set_source(g)
    ctx.fill()
    # soft jaw shadow only (featureless, non-identifiable)
    g = cairo.RadialGradient(cx, cy + 70, 5, cx, cy + 40, 60)
    g.add_color_stop_rgba(0, 0.2, 0.2, 0.23, 0.25)
    g.add_color_stop_rgba(1, 0.2, 0.2, 0.23, 0.0)
    ctx.set_source(g)
    ellipse(ctx, cx, cy, 50, 64)
    ctx.fill()


def draw_front(ctx, f, m, hips=0.0, breath=0.0, seated=False, arm_r=None, arm_l=None,
               hold_r=None):
    """Front-view mannequin. Units: 1000 tall, origin at feet center, y up negative.
    f: fat 0..1 (moderate belly at 1), m: muscle 0..1.
    arm_r / arm_l: optional hand targets (x, y) overriding pose.
    """
    d = front_dims(f, m)
    sh, nw, lat, w, hw = d['sh'], d['nw'], d['lat'], d['w'], d['hw']
    by = -breath * 3  # upper-body breathing lift

    # ---------------- legs
    if not seated:
        for s in (-1, 1):
            hip = (s * 50, -470)
            knee = (s * 52, -265)
            ank = (s * 50, -48)
            capsule(ctx, hip, knee, 50 + 9 * m + 9 * f, 31 + 4 * m)
            # calf
            capsule(ctx, (s * 56, -230), (s * 52, -120), 30 + 6 * m, 20)
            capsule(ctx, knee, ank, 29 + 3 * m, 17)
            ellipse(ctx, s * 60, -22, 32, 19)
            ctx.set_source(skin_grad((s * 60 - 30, -40), (s * 60 + 30, 0)))
            ctx.fill()

    # ---------------- torso
    pts_r = [
        (nw, -842 + by),
        (sh - 18, -808 + by),
        (sh - 6, -770 + by),
        (lat, -700 + by),
        (lerp(lat, w, 0.55) + 8 * f, -630),
        (w, -565),
        (w + 6 * f, -525),
        (hw, -470),
    ]
    pts = pts_r + [(-x, y) for (x, y) in reversed(pts_r)]
    pts = pts + [(0, -455)]
    # reorder closed loop: right side down, bottom, left side up
    loop = pts_r + [(0, -450)] + [(-x, y) for (x, y) in reversed(pts_r)] + [(0, -850 + by)]
    smooth_closed(ctx, loop)
    g = cairo.LinearGradient(-sh, 0, sh, 0)
    g.add_color_stop_rgb(0.0, *SK_SH)
    g.add_color_stop_rgb(0.3, *SK_HI)
    g.add_color_stop_rgb(0.55, *SK_BASE)
    g.add_color_stop_rgb(1.0, *SK_DEEP)
    ctx.set_source(g)
    ctx.fill()

    # neck
    capsule(ctx, (0, -875 + by), (0, -820 + by), nw, nw + 2)

    # traps
    if m > 0.05:
        ctx.set_source_rgba(0.35, 0.36, 0.39, 0.25 * m)
        for s in (-1, 1):
            ctx.new_path()
            ctx.move_to(s * nw, -845 + by)
            ctx.curve_to(s * (nw + 25), -825 + by, s * (sh - 40), -815 + by, s * (sh - 15), -800 + by)
            ctx.set_line_width(3)
            ctx.stroke()

    # pecs
    pec_a = 0.12 + 0.38 * m
    ctx.set_line_width(3.5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for s in (-1, 1):
        ctx.new_path()
        ctx.move_to(s * 6, -765 + by)
        ctx.curve_to(s * 20, -705 + by + 6 * f, s * (sh - 50), -700 + by + 8 * f, s * (sh - 26), -752 + by)
        ctx.set_source_rgba(0.28, 0.29, 0.32, pec_a)
        ctx.stroke()
        # pec highlight
        ctx.set_source_rgba(1, 1, 1, 0.10 + 0.10 * m)
        ellipse(ctx, s * (30 + 20 * m) - 8, -770 + by, 34 + 12 * m, 20 + 6 * m)
        ctx.fill()
    # sternum
    ctx.new_path()
    ctx.move_to(0, -800 + by)
    ctx.line_to(0, -725 + by)
    ctx.set_source_rgba(0.28, 0.29, 0.32, 0.15 + 0.25 * m)
    ctx.stroke()

    # abs (visible only when lean + muscular)
    abs_a = clamp((m - 0.25) * 1.4) * clamp(1 - f * 1.6)
    if abs_a > 0.01:
        ctx.set_line_width(3)
        ctx.set_source_rgba(0.27, 0.28, 0.31, 0.55 * abs_a)
        ctx.new_path()
        ctx.move_to(0, -712)
        ctx.line_to(0, -520)
        ctx.stroke()
        for i, yy in enumerate((-672, -628, -584)):
            wd = 38 - i * 2
            for s in (-1, 1):
                ctx.new_path()
                ctx.move_to(s * 6, yy)
                ctx.curve_to(s * wd * 0.5, yy + 5, s * wd, yy + 2, s * (wd + 4), yy - 4)
                ctx.stroke()
        # obliques / v-line
        for s in (-1, 1):
            ctx.new_path()
            ctx.move_to(s * (w - 10), -600)
            ctx.curve_to(s * (w - 14), -540, s * 60, -505, s * 26, -470)
            ctx.stroke()

    # ---------------- shorts
    ctx.new_path()
    top = -505
    ctx.move_to(-hw - 6, top)
    ctx.curve_to(-hw / 2, top + 6, hw / 2, top + 6, hw + 6, top)
    ctx.line_to(hw + 14 + 6 * f, -350)
    ctx.line_to(12, -340)
    ctx.line_to(0, -392)
    ctx.line_to(-12, -340)
    ctx.line_to(-hw - 14 - 6 * f, -350)
    ctx.close_path()
    g = cairo.LinearGradient(-hw, 0, hw, 0)
    g.add_color_stop_rgb(0, *mul(SHORTS, 0.8))
    g.add_color_stop_rgb(0.35, *SHORTS_HI)
    g.add_color_stop_rgb(1, *mul(SHORTS, 0.7))
    ctx.set_source(g)
    ctx.fill()
    # waistband
    ctx.new_path()
    ctx.move_to(-hw - 6, top)
    ctx.curve_to(-hw / 2, top + 6, hw / 2, top + 6, hw + 6, top)
    ctx.set_source_rgba(0.35, 0.36, 0.40, 1)
    ctx.set_line_width(5)
    ctx.stroke()

    # ---------------- belly (fat)
    if f > 0.02:
        # soft protrusion highlight
        g = cairo.RadialGradient(-14, -585, 5, 0, -560, 60 + 60 * f)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.20 * f)
        g.add_color_stop_rgba(1, 1, 1, 1, 0.0)
        ctx.set_source(g)
        ellipse(ctx, 0, -560, w * 0.95, 70 + 30 * f)
        ctx.fill()
        # overhang over waistband
        ov = 24 * f
        ctx.new_path()
        ctx.move_to(-w * 0.85, top - 8)
        ctx.curve_to(-w * 0.5, top + ov + 8, w * 0.5, top + ov + 8, w * 0.85, top - 8)
        ctx.curve_to(w * 0.4, top - 4, -w * 0.4, top - 4, -w * 0.85, top - 8)
        ctx.close_path()
        ctx.set_source_rgb(*SK_BASE)
        ctx.fill()
        ctx.new_path()
        ctx.move_to(-w * 0.8, top - 6 + ov * 0.3)
        ctx.curve_to(-w * 0.45, top + ov + 6, w * 0.45, top + ov + 6, w * 0.8, top - 6 + ov * 0.3)
        ctx.set_source_rgba(0.2, 0.2, 0.23, 0.35 * f)
        ctx.set_line_width(4)
        ctx.stroke()
        # side curvature of the belly (reads as roundness)
        for sgn in (-1, 1):
            ctx.new_path()
            ctx.move_to(sgn * (w - 18), -620)
            ctx.curve_to(sgn * (w + 2), -575, sgn * (w + 2), -530, sgn * (w - 16), top - 4)
            ctx.set_source_rgba(0.22, 0.23, 0.26, 0.30 * f)
            ctx.set_line_width(10)
            ctx.stroke()
        # lower belly shade
        g = cairo.LinearGradient(0, -600, 0, top)
        g.add_color_stop_rgba(0, 0.2, 0.2, 0.23, 0.0)
        g.add_color_stop_rgba(1, 0.2, 0.2, 0.23, 0.22 * f)
        ctx.set_source(g)
        ellipse(ctx, 0, -545, w * 0.9, 55)
        ctx.fill()
    # navel
    ctx.set_source_rgba(0.22, 0.23, 0.26, 0.55)
    ellipse(ctx, 0, -552 + 6 * f, 4 + 2 * f, 7)
    ctx.fill()

    # ---------------- arms
    for s, override in ((1, arm_r), (-1, arm_l)):
        J = (s * (sh - 22), -776 + by)
        la, lb = 158, 150
        if override is not None:
            tgt = override
        else:
            relax = (s * (sh + 6 + 4 * f), -468)
            hip_t = (s * (w + 16), -548)
            tgt = (lerp(relax[0], hip_t[0], hips), lerp(relax[1], hip_t[1], hips))
        bend = -1 if s > 0 else 1  # elbows flare outward
        E, W = ik2(J, tgt, la, lb, bend)
        # make relaxed arms elbow outward a touch
        capsule(ctx, J, E, 26 + 15 * m + 3 * f, 20 + 8 * m)
        # biceps bulge
        if m > 0.1:
            mx, my = lerp(J[0], E[0], 0.5), lerp(J[1], E[1], 0.5)
            ctx.set_source_rgba(1, 1, 1, 0.10 * m)
            ellipse(ctx, mx - s * 4, my, 14 + 8 * m, 30 + 10 * m, math.atan2(E[1] - J[1], E[0] - J[0]) + math.pi / 2)
            ctx.fill()
        capsule(ctx, E, W, 21 + 9 * m, 14 + 3 * m)
        # hand
        ang = math.atan2(W[1] - E[1], W[0] - E[0])
        hx, hy = W[0] + math.cos(ang) * 20, W[1] + math.sin(ang) * 20
        ellipse(ctx, hx, hy, 23, 15, ang)
        ctx.set_source(skin_grad((hx - 20, hy - 20), (hx + 20, hy + 20)))
        ctx.fill()
        if s == 1 and hold_r is not None:
            hold_r(ctx, hx, hy)
        # deltoid cap
        ellipse(ctx, J[0] + s * 2, J[1] + 12, 24 + 20 * m, 32 + 16 * m, s * 0.25)
        g = cairo.RadialGradient(J[0] - 10, J[1] - 8, 4, J[0], J[1] + 10, 50 + 12 * m)
        g.add_color_stop_rgb(0, *SK_HI)
        g.add_color_stop_rgb(0.6, *SK_BASE)
        g.add_color_stop_rgb(1, *SK_SH)
        ctx.set_source(g)
        ctx.fill()

    draw_head_front(ctx, 0, -918 + by)


# ---------------------------------------------------------------- SIDE VIEW
L_THIGH, L_SHIN, L_TORSO, L_UA, L_FA = 205, 215, 300, 158, 150


def draw_side(ctx, f, m, H, u, K_far, A_far, K, A, E_far, W_far, E, W, front_sign=1, foot_dir=1,
              plate_far=None, plate_near=None):
    """Side-view mannequin. H hip, u unit torso axis (hip->neck), knees/ankles, elbows/wrists."""
    n = (-u[1] * front_sign, u[0] * front_sign)
    S = (H[0] + u[0] * L_TORSO, H[1] + u[1] * L_TORSO)
    Sj = (S[0] - u[0] * 28, S[1] - u[1] * 28)

    def P(t, s):
        return (H[0] + u[0] * t * L_TORSO + n[0] * s, H[1] + u[1] * t * L_TORSO + n[1] * s)

    if plate_far is not None:
        plate_far(ctx)
    # far arm
    capsule(ctx, Sj, E_far, 24 + 13 * m, 19 + 7 * m, dark=0.72)
    capsule(ctx, E_far, W_far, 20 + 8 * m, 14, dark=0.72)
    # far leg
    capsule(ctx, H, K_far, 50 + 8 * m + 8 * f, 30, dark=0.75)
    capsule(ctx, K_far, A_far, 29 + 5 * m, 17, dark=0.75)
    capsule(ctx, A_far, (A_far[0] + foot_dir * 55, A_far[1] + 10), 17, 13, dark=0.75)

    # neck + head
    capsule(ctx, S, (S[0] + u[0] * 45, S[1] + u[1] * 45), 22 + 7 * m, 22 + 6 * m)
    hc = (S[0] + u[0] * 100 + n[0] * 12, S[1] + u[1] * 100 + n[1] * 12)
    ellipse(ctx, hc[0], hc[1], 58, 50, math.atan2(u[1], u[0]))
    g = cairo.RadialGradient(hc[0] - 15, hc[1] - 20, 5, hc[0], hc[1], 70)
    g.add_color_stop_rgb(0, *SK_HI)
    g.add_color_stop_rgb(0.6, *SK_BASE)
    g.add_color_stop_rgb(1, *SK_SH)
    ctx.set_source(g)
    ctx.fill()

    # torso outline
    back = [P(1.0, -34), P(0.8, -44 - 6 * m), P(0.5, -42), P(0.2, -46), P(0.0, -50)]
    front = [P(0.0, 52 + 12 * f), P(0.22, 50 + 58 * f), P(0.42, 44 + 42 * f + 4 * m),
             P(0.66, 58 + 22 * m + 6 * f), P(0.85, 50 + 16 * m), P(1.0, 30)]
    smooth_closed(ctx, front + back)
    c0 = P(0.5, -60)
    c1 = P(0.5, 90)
    ctx.set_source(skin_grad(c0, c1) if front_sign * u[1] < 0 else skin_grad(c1, c0))
    ctx.fill()
    # belly underside shadow
    if f > 0.05:
        a, b = P(0.12, 48 + 40 * f), P(0.32, 50 + 55 * f)
        ctx.new_path()
        ctx.move_to(*P(0.05, 40))
        ctx.curve_to(a[0], a[1], b[0], b[1], *P(0.42, 40 + 30 * f))
        ctx.set_source_rgba(0.2, 0.2, 0.23, 0.35 * f)
        ctx.set_line_width(5)
        ctx.stroke()

    # shorts (hip block + top of near thigh)
    tv = (K[0] - H[0], K[1] - H[1])
    tl = math.hypot(*tv)
    mid = (H[0] + tv[0] / tl * 110, H[1] + tv[1] / tl * 110)
    capsule(ctx, H, mid, 62 + 8 * f, 54 + 6 * f, color=SHORTS)
    smooth_closed(ctx, [P(0.18, -54), P(0.18, 58 + 50 * f * 0.8), P(-0.05, 64 + 10 * f), P(-0.12, 0), P(-0.05, -62)])
    ctx.set_source_rgb(*SHORTS)
    ctx.fill()

    # near leg
    capsule(ctx, (H[0] + tv[0] / tl * 100, H[1] + tv[1] / tl * 100), K, 52 + 8 * m + 6 * f, 31 + 4 * m)
    capsule(ctx, K, A, 30 + 6 * m, 17)
    capsule(ctx, A, (A[0] + foot_dir * 58, A[1] + 10), 18, 13)

    # near arm
    capsule(ctx, Sj, E, 26 + 15 * m, 20 + 8 * m)
    capsule(ctx, E, W, 21 + 9 * m, 14 + 3 * m)
    ellipse(ctx, W[0], W[1], 20, 17)
    ctx.set_source(skin_grad((W[0] - 18, W[1] - 18), (W[0] + 18, W[1] + 18)))
    ctx.fill()
    # deltoid
    ellipse(ctx, Sj[0] + u[0] * 5, Sj[1] + u[1] * 5, 30 + 12 * m, 34 + 12 * m, math.atan2(u[1], u[0]))
    g = cairo.RadialGradient(Sj[0] - 10, Sj[1] - 12, 4, Sj[0], Sj[1], 48 + 12 * m)
    g.add_color_stop_rgb(0, *SK_HI)
    g.add_color_stop_rgb(0.6, *SK_BASE)
    g.add_color_stop_rgb(1, *SK_SH)
    ctx.set_source(g)
    ctx.fill()
    if plate_near is not None:
        plate_near(ctx)
    return S, Sj
