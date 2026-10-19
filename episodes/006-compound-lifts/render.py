import math
import random
import sys
import subprocess
import numpy as np
import cairo
from PIL import Image, ImageFilter
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'engine'))

from figure import (draw_front, draw_side, ik2, ellipse, lerp, clamp, ease, capsule, skin_grad, front_dims,
                    L_THIGH, L_SHIN, L_TORSO, L_UA, L_FA)
import props as P

W, H = 1080, 1920
FPS = 30
N = 600
LIME = P.rgb('#c6ff3d')

# head / text boxes recorded per frame (device coords) for the 'check' mode
HEADS = []
TEXTS = []

# ------------------------------------------------------------ background cache
BG_OX, BG_OY, BG_W, BG_H = -500, -300, 2080, 2600


def build_bg():
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, BG_W, BG_H)
    c = cairo.Context(s)
    P.draw_gym(c, BG_W, BG_H, BG_OX, BG_OY)
    s.flush()
    buf = np.ndarray((BG_H, BG_W, 4), np.uint8, s.get_data()).copy()
    img = Image.fromarray(buf[:, :, [2, 1, 0]])
    img = img.filter(ImageFilter.GaussianBlur(5))
    arr = np.array(img)
    out = np.zeros((BG_H, BG_W, 4), np.uint8)
    out[:, :, 0] = arr[:, :, 2]
    out[:, :, 1] = arr[:, :, 1]
    out[:, :, 2] = arr[:, :, 0]
    out[:, :, 3] = 255
    surf = cairo.ImageSurface.create_for_data(out, cairo.FORMAT_ARGB32, BG_W, BG_H)
    global _BG_KEEP
    _BG_KEEP = out
    return surf


BG = build_bg()


def paint_bg(ctx, dim=0.0):
    ctx.set_source_surface(BG, BG_OX, BG_OY)
    ctx.paint()
    if dim:
        ctx.set_source_rgba(0, 0, 0, dim)
        ctx.paint()


def camera(ctx, zoom, cx, cy, rot=0.0):
    ctx.translate(W / 2, H / 2)
    ctx.rotate(rot)
    ctx.scale(zoom, zoom)
    ctx.translate(-cx, -cy)


# ------------------------------------------------------------ text
FONT = "Poppins"


def text_block(ctx, lines, cy, t_in, t, box_line=None, size=132):
    """lines: list of str. box_line: index of line drawn black on lime box."""
    if t < t_in:
        return
    k = (t - t_in)
    pop = k * FPS
    ctx.save()
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    y = cy
    for i, line in enumerate(lines):
        li = pop - i * 5  # stagger lines
        if li < 0:
            continue
        a = clamp(li / 3)
        sc = 1 + 0.35 * math.exp(-li / 2.2) * math.cos(li / 2.0)
        fs = size
        ctx.set_font_size(fs)
        ext = ctx.text_extents(line)
        while ext.width > 940:
            fs -= 4
            ctx.set_font_size(fs)
            ext = ctx.text_extents(line)
        lh = fs * 1.18
        ctx.save()
        ctx.translate(W / 2, y + lh / 2)
        ctx.scale(sc, sc)
        tx = -ext.width / 2 - ext.x_bearing
        ty = -ext.height / 2 - ext.y_bearing
        if i == box_line:
            pad_x, pad_y = 30, 18
            P.rrect(ctx, -ext.width / 2 - pad_x, -ext.height / 2 - pad_y, ext.width + 2 * pad_x, ext.height + 2 * pad_y, 16)
            ctx.set_source_rgba(0, 0, 0, 0.35 * a)
            ctx.save()
            ctx.translate(6, 8)
            ctx.fill_preserve()
            ctx.restore()
            ctx.new_path()
            P.rrect(ctx, -ext.width / 2 - pad_x, -ext.height / 2 - pad_y, ext.width + 2 * pad_x, ext.height + 2 * pad_y, 16)
            ctx.set_source_rgba(*LIME, a)
            ctx.fill()
            ctx.move_to(tx, ty)
            ctx.text_path(line)
            ctx.set_source_rgba(0.05, 0.06, 0.07, a)
            ctx.fill()
        else:
            pad_x, pad_y = 10, 10
            # shadow
            ctx.move_to(tx + 5, ty + 7)
            ctx.text_path(line)
            ctx.set_source_rgba(0, 0, 0, 0.55 * a)
            ctx.fill()
            ctx.move_to(tx, ty)
            ctx.text_path(line)
            ctx.set_line_width(12)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.set_source_rgba(0.04, 0.05, 0.06, a)
            ctx.stroke_preserve()
            ctx.set_source_rgba(1, 1, 1, a)
            ctx.fill()
        ctx.restore()
        if a > 0:
            cyl = y + lh / 2
            TEXTS.append((W / 2 - ext.width / 2 - pad_x, cyl - ext.height / 2 - pad_y,
                          W / 2 + ext.width / 2 + pad_x, cyl + ext.height / 2 + pad_y + 8, line))
        y += lh + (26 if box_line is not None else 4)
    ctx.restore()


def vignette(ctx, a=0.55):
    g = cairo.RadialGradient(W / 2, H / 2, 380, W / 2, H / 2, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, a)
    P.src(ctx, g)
    ctx.paint()


def flash(ctx, a):
    if a > 0:
        ctx.set_source_rgba(1, 1, 1, a)
        ctx.paint()


# ------------------------------------------------------------ head tracking (keeps text off the head)
def record_head(ctx, cx, cy, rx, ry):
    xs, ys = [], []
    for i in range(12):
        an = i * math.pi / 6
        dx, dy = ctx.user_to_device(cx + math.cos(an) * rx, cy + math.sin(an) * ry)
        xs.append(dx)
        ys.append(dy)
    HEADS.append((min(xs), min(ys), max(xs), max(ys)))


def side_head(ctx, H_, u, front_sign=1):
    n = (-u[1] * front_sign, u[0] * front_sign)
    S = (H_[0] + u[0] * L_TORSO, H_[1] + u[1] * L_TORSO)
    hc = (S[0] + u[0] * 100 + n[0] * 12, S[1] + u[1] * 100 + n[1] * 12)
    record_head(ctx, hc[0], hc[1], 60, 60)


# ------------------------------------------------------------ figure placement
FEET_Y = 1760


def figure_front(ctx, x, feet_y, k, post=None, **kw):
    ctx.save()
    ctx.translate(x, feet_y)
    ctx.scale(k, k)
    draw_front(ctx, **kw)
    record_head(ctx, 0, -918, 52, 66)
    if post is not None:
        post(ctx)
    ctx.restore()


# base physique (skinny-fat, same as episode 001)
F0, M0 = 1.0, 0.08
# end physique: moderate, believable (a few months of steady progress)
F1, M1 = 0.30, 0.55


# ------------------------------------------------------------ exercise helpers (from 001 / 005)
def ik_pick(root, target, l1, l2, score):
    best = None
    for b in (1, -1):
        j, e = ik2(root, target, l1, l2, b)
        sc = score(j)
        if best is None or sc > best[0]:
            best = (sc, j, e)
    return best[1], best[2]


def plate_disk(ctx, x, y, r=95, dark=1.0):
    ctx.arc(x, y, r, 0, 2 * math.pi)
    g = cairo.RadialGradient(x - r * 0.3, y - r * 0.3, 2, x, y, r)
    g.add_color_stop_rgb(0, *(v * dark for v in P.rgb('#3a3f46')))
    g.add_color_stop_rgb(1, *(v * dark for v in P.rgb('#0c0d0f')))
    P.src(ctx, g)
    ctx.fill()
    ctx.set_line_width(4)
    ctx.arc(x, y, r * 0.8, 0, 2 * math.pi)
    ctx.set_source_rgba(0, 0, 0, 0.5)
    ctx.stroke()
    ctx.arc(x, y, r * 0.22, 0, 2 * math.pi)
    P.src(ctx, P.rgb('#8a9099'))
    ctx.fill()
    ctx.arc(x, y, r * 0.1, 0, 2 * math.pi)
    P.src(ctx, P.rgb('#2a2d31'))
    ctx.fill()


def unit(a):
    return (math.sin(a), -math.cos(a))


def pose_bench(p):
    Hh = (-90, -275)
    u = (1.0, 0.0)
    A = (-360, -15)
    K, A2 = ik_pick(Hh, A, L_THIGH, L_SHIN, lambda j: -j[1])
    Af = (-330, -15)
    Kf, Af2 = ik_pick(Hh, Af, L_THIGH, L_SHIN, lambda j: -j[1])
    S = (Hh[0] + L_TORSO, Hh[1])
    Sj = (S[0] - 28, S[1])
    bar = (150, lerp(-615, -440, p))
    E, Wr = ik_pick(Sj, bar, L_UA, L_FA, lambda j: j[1] - 0.3 * j[0])
    return dict(H=Hh, u=u, K=K, A=A2, K_far=Kf, A_far=Af2, E=E, W=Wr, E_far=(E[0] + 6, E[1] - 4),
                W_far=(Wr[0] + 6, Wr[1] - 4), front_sign=-1, foot_dir=1), bar


def pose_row(p):
    Hh = (-60, -400)
    a = math.radians(57)
    u = unit(a)
    A = (40, -15)
    K, A2 = ik_pick(Hh, A, L_THIGH, L_SHIN, lambda j: j[0])
    Kf, Af2 = ik_pick(Hh, (30, -15), L_THIGH, L_SHIN, lambda j: j[0])
    S = (Hh[0] + u[0] * L_TORSO, Hh[1] + u[1] * L_TORSO)
    Sj = (S[0] - u[0] * 28, S[1] - u[1] * 28)
    n = (-u[1], u[0])
    top = (Hh[0] + u[0] * 125 + n[0] * 70, Hh[1] + u[1] * 125 + n[1] * 70)
    bot = (Sj[0] + 5, Sj[1] + 295)
    hand = (lerp(bot[0], top[0], p), lerp(bot[1], top[1], p))
    E, Wr = ik_pick(Sj, hand, L_UA, L_FA, lambda j: -j[1] - 0.5 * j[0])
    return dict(H=Hh, u=u, K=K, A=A2, K_far=Kf, A_far=Af2, E=E, W=Wr, E_far=(E[0] - 6, E[1] - 6),
                W_far=(Wr[0] - 6, Wr[1] - 4), front_sign=1, foot_dir=1), hand


def pose_squat(p):
    Hh = (lerp(-15, -150, p), lerp(-425, -272, p))
    a = math.radians(lerp(8, 40, p))
    u = unit(a)
    A = (0, -15)
    K, A2 = ik_pick(Hh, A, L_THIGH, L_SHIN, lambda j: j[0])
    Kf, Af2 = ik_pick(Hh, (-10, -15), L_THIGH, L_SHIN, lambda j: j[0])
    S = (Hh[0] + u[0] * L_TORSO, Hh[1] + u[1] * L_TORSO)
    Sj = (S[0] - u[0] * 28, S[1] - u[1] * 28)
    n = (-u[1], u[0])
    bar = (S[0] - n[0] * 50 - u[0] * 8, S[1] - n[1] * 50 - u[1] * 8)
    hand = (bar[0] + n[0] * 8, bar[1] + n[1] * 8 + 6)
    E, Wr = ik_pick(Sj, hand, L_UA, L_FA, lambda j: j[1] - j[0])
    return dict(H=Hh, u=u, K=K, A=A2, K_far=Kf, A_far=Af2, E=E, W=Wr, E_far=(E[0] - 6, E[1] - 4),
                W_far=(Wr[0] - 4, Wr[1] - 4), front_sign=1, foot_dir=1), bar


def pose_press(p):
    Hh = (0, -440)
    u = (0.0, -1.0)
    K, A2 = ik_pick(Hh, (0, -15), L_THIGH, L_SHIN, lambda j: j[0])
    Kf, Af2 = ik_pick(Hh, (-12, -15), L_THIGH, L_SHIN, lambda j: j[0])
    Sj = (0, -712)
    hand = (lerp(40, 14, p), lerp(-745, -1008, p))
    E, Wr = ik_pick(Sj, hand, L_UA, L_FA, lambda j: j[0] + j[1])
    return dict(H=Hh, u=u, K=K, A=A2, K_far=Kf, A_far=Af2, E=E, W=Wr, E_far=(E[0] - 8, E[1] - 3),
                W_far=(Wr[0] - 8, Wr[1] - 3), front_sign=1, foot_dir=1), hand


def pose_deadlift(p):
    """p=0: bar on the floor, hips back, flat back. p=1: standing lockout."""
    barx = 38
    bary = lerp(-97, -415, p)
    a = math.radians(lerp(58, 3, ease(p)))
    u = unit(a)
    sj_t = (barx - 4, bary - 296)
    Hh = (sj_t[0] - u[0] * 272, sj_t[1] - u[1] * 272)
    K, A2 = ik_pick(Hh, (0, -15), L_THIGH, L_SHIN, lambda j: j[0])
    Kf, Af2 = ik_pick(Hh, (-10, -15), L_THIGH, L_SHIN, lambda j: j[0])
    Sj = (Hh[0] + u[0] * 272, Hh[1] + u[1] * 272)
    bar = (barx, bary)
    E, Wr = ik_pick(Sj, bar, L_UA, L_FA, lambda j: -j[0])
    return dict(H=Hh, u=u, K=K, A=A2, K_far=Kf, A_far=Af2, E=E, W=Wr, E_far=(E[0] - 6, E[1] - 4),
                W_far=(Wr[0] - 4, Wr[1] - 4), front_sign=1, foot_dir=1), bar


EXS = {'bench': pose_bench, 'row': pose_row, 'squat': pose_squat, 'press': pose_press, 'deadlift': pose_deadlift}


def glow_spot(ctx, x, y, r, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *LIME, a)
    g.add_color_stop_rgba(1, *LIME, 0)
    P.src(ctx, g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def draw_exercise(ctx, name, t, f, m, pr=100, period=1.05, glow=0.0):
    ph = (t / period) % 1.0
    p = 0.5 - 0.5 * math.cos(2 * math.pi * ph)
    pose, bar = EXS[name](p)
    if name == 'bench':
        for x in (110, 170):
            ctx.rectangle(x - 8, -760, 16, 760)
            P.src(ctx, P.rgb('#15181c'))
            ctx.fill()
        P.rrect(ctx, -230, -250, 480, 38, 16)
        P.src(ctx, P.vgrad(-300, -258, [(0, P.rgb('#2b3036')), (1, P.rgb('#0e1013'))]))
        ctx.fill()
        for x in (-200, 190):
            ctx.rectangle(x, -215, 22, 205)
            P.src(ctx, P.rgb('#0c0d0f'))
            ctx.fill()
    plate_far = (lambda c: plate_disk(c, bar[0] + 10, bar[1] - 6, pr * 0.95, dark=0.6))
    plate_near = (lambda c: plate_disk(c, bar[0], bar[1], pr))
    draw_side(ctx, f, m, pose['H'], pose['u'], pose['K_far'], pose['A_far'], pose['K'], pose['A'],
              pose['E_far'], pose['W_far'], pose['E'], pose['W'], front_sign=pose['front_sign'],
              foot_dir=pose['foot_dir'], plate_far=plate_far, plate_near=plate_near)
    side_head(ctx, pose['H'], pose['u'], pose['front_sign'])
    if glow > 0:
        # many muscles working at once: shoulders, arms, core, legs light up together
        Hh, u = pose['H'], pose['u']
        Sj = (Hh[0] + u[0] * 272, Hh[1] + u[1] * 272)
        E = pose['E']
        pulse = glow * (0.75 + 0.25 * math.sin(t * 9))
        for (x, y, r) in ((Sj[0], Sj[1] + 10, 85), ((Sj[0] + E[0]) / 2, (Sj[1] + E[1]) / 2, 70),
                          (Hh[0] + u[0] * 120 + 25, Hh[1] + u[1] * 120, 95),
                          ((Hh[0] + pose['K'][0]) / 2, (Hh[1] + pose['K'][1]) / 2, 90)):
            glow_spot(ctx, x, y, r * 0.8, 0.22 * pulse)
    return pose


CONF = {
    'bench': dict(z=1.3, cx=540, cy=1390, fx=540, k=1.12),
    'row': dict(z=1.15, cx=560, cy=1200, fx=500, k=1.15),
    'squat': dict(z=1.12, cx=560, cy=1130, fx=580, k=1.05),
    'deadlift': dict(z=1.12, cx=560, cy=1140, fx=540, k=1.08),
    'press': dict(z=1.05, cx=540, cy=1080, fx=530, k=0.98),
}


def lift_shot(ctx, name, tt, dur, f, m, pr, rot=0.0, punch_on=True, period=1.05, glow=0.0, conf=None):
    c = dict(CONF[name])
    if conf:
        c.update(conf)
    punch = 1 + 0.10 * math.exp(-tt * 9) if punch_on else 1.0
    drift = tt / dur
    camera(ctx, c['z'] * punch * (1 + 0.03 * drift), c['cx'] + 20 * drift, c['cy'], rot=rot * (1 - drift * 0.5))
    paint_bg(ctx)
    P.light_cone(ctx, c['fx'], 200, 1800, 120, 560, 0.08)
    P.floor_spot(ctx, c['fx'], FEET_Y - 10, 460, 100)
    P.soft_shadow(ctx, c['fx'], FEET_Y - 8, 260, 30, 0.6)
    ctx.save()
    ctx.translate(c['fx'], FEET_Y)
    ctx.scale(c['k'], c['k'])
    draw_exercise(ctx, name, tt, f, m, pr=pr, period=period, glow=glow)
    ctx.restore()


# ------------------------------------------------------------ tiny dumbbells (episode 006)
def tiny_db(ctx, x, y, ang, s=1.0):
    """A very light dumbbell (figure units)."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    ctx.rectangle(-22, -4, 44, 8)
    P.src(ctx, P.vgrad(-4, 4, [(0, P.rgb('#c9ced4')), (1, P.rgb('#5b6068'))]))
    ctx.fill()
    for sx in (-1, 1):
        P.rrect(ctx, sx * 24 - 8, -15, 16, 30, 5)
        P.src(ctx, P.vgrad(-15, 15, [(0, P.rgb('#9aa1aa')), (0.4, P.rgb('#5b6068')), (1, P.rgb('#2a2e34'))]))
        ctx.fill()
    ctx.restore()


def front_hand(f, m, s, tgt):
    d = front_dims(f, m)
    J = (s * (d['sh'] - 22), -776)
    E, Wr = ik2(J, tgt, 158, 150, -1 if s > 0 else 1)
    ang = math.atan2(Wr[1] - E[1], Wr[0] - E[0])
    return (Wr[0] + math.cos(ang) * 20, Wr[1] + math.sin(ang) * 20), ang


def raise_targets(f, m, th):
    """Lateral raise hand targets for both arms, th = raise angle (rad)."""
    d = front_dims(f, m)
    out = {}
    for s in (1, -1):
        J = (s * (d['sh'] - 22), -776)
        relax = (s * (d['sh'] + 6 + 4 * f), -468)
        vx, vy = relax[0] - J[0], relax[1] - J[1]
        L = math.hypot(vx, vy)
        vx, vy = vx / L * 300, vy / L * 300
        ph = s * th
        nx = vx * math.cos(ph) + vy * math.sin(ph)
        ny = -vx * math.sin(ph) + vy * math.cos(ph)
        out[s] = (J[0] + nx, J[1] + ny)
    return out


def raise_figure(ctx, x, feet_y, k, t, f, m, amp=0.30, period=0.62):
    th = 0.08 + amp * (0.5 - 0.5 * math.cos(2 * math.pi * t / period))
    tg = raise_targets(f, m, th)

    def post(c):
        for s in (1, -1):
            hp, ang = front_hand(f, m, s, tg[s])
            tiny_db(c, hp[0], hp[1], ang + math.pi / 2, 0.9)
    figure_front(ctx, x, feet_y, k, f=f, m=m, arm_r=tg[1], arm_l=tg[-1], post=post,
                 breath=math.sin(t * 3.2))


def hold_figure(ctx, x, feet_y, k, t, f, m):
    """Standing, arms down, a tiny dumbbell in each hand."""
    d = front_dims(f, m)
    tg = {s: (s * (d['sh'] + 6 + 4 * f), -468) for s in (1, -1)}

    def post(c):
        for s in (1, -1):
            hp, ang = front_hand(f, m, s, tg[s])
            tiny_db(c, hp[0], hp[1], ang + math.pi / 2, 0.9)
    figure_front(ctx, x, feet_y, k, f=f, m=m, arm_r=tg[1], arm_l=tg[-1], post=post,
                 breath=math.sin(t * 2.4) * 1.4)


# ------------------------------------------------------------ cable kickback (side view)
def kickback_shot(ctx, tt, dur, f, m, rot=0.0):
    z = 1.12 * (1 + 0.10 * math.exp(-tt * 9)) * (1 + 0.03 * tt / dur)
    camera(ctx, z, 600 + 20 * tt / dur, 1180, rot=rot * (1 - 0.5 * tt / dur))
    paint_bg(ctx)
    fx, k = 470, 1.12
    P.light_cone(ctx, fx, 200, 1800, 120, 560, 0.08)
    P.floor_spot(ctx, fx, FEET_Y - 10, 460, 100)
    P.soft_shadow(ctx, fx + 40, FEET_Y - 8, 300, 30, 0.6)
    ctx.save()
    ctx.translate(fx, FEET_Y)
    ctx.scale(k, k)
    # cable tower in front of him
    ctx.rectangle(350, -1250, 70, 1250)
    P.src(ctx, P.hgrad(350, 420, [(0, P.rgb('#22262b')), (0.4, P.rgb('#3a4048')), (1, P.rgb('#121417'))]))
    ctx.fill()
    for i in range(9):
        P.rrect(ctx, 428, -260 - i * 34, 90, 30, 4)
        P.src(ctx, P.rgb('#1a1d21') if i else P.rgb('#2d3238'))
        ctx.fill()
    pul = (340, -130)
    ctx.arc(pul[0], pul[1], 20, 0, 2 * math.pi)
    P.src(ctx, P.rgb('#8a9099'))
    ctx.fill()
    ctx.arc(pul[0], pul[1], 8, 0, 2 * math.pi)
    P.src(ctx, P.rgb('#2a2d31'))
    ctx.fill()
    # pose: hinged over, elbow pinned back, only the forearm moves (a tiny range)
    Hh = (-60, -405)
    u = unit(math.radians(60))
    n = (-u[1], u[0])
    K, A2 = ik_pick(Hh, (40, -15), L_THIGH, L_SHIN, lambda j: j[0])
    Kf, Af2 = ik_pick(Hh, (10, -15), L_THIGH, L_SHIN, lambda j: j[0])
    Sj = (Hh[0] + u[0] * 272, Hh[1] + u[1] * 272)
    E = (Sj[0] - u[0] * 150 + n[0] * 22, Sj[1] - u[1] * 150 + n[1] * 22)
    ph = (tt / 0.55) % 1.0
    p = 0.5 - 0.5 * math.cos(2 * math.pi * ph)
    a0 = math.pi / 2
    a1 = math.atan2(-u[1], -u[0])
    an = lerp(a0, a1, 0.15 + 0.85 * p)
    Wr = (E[0] + math.cos(an) * 150, E[1] + math.sin(an) * 150)
    Ef, Wf = ik_pick(Sj, (Kf[0] + 30, Kf[1] - 40), L_UA, L_FA, lambda j: -j[0])
    draw_side(ctx, f, m, Hh, u, Kf, Af2, K, A2, Ef, Wf, E, Wr, front_sign=1, foot_dir=1)
    side_head(ctx, Hh, u, 1)
    # cable from the pulley to the handle
    ctx.new_path()
    ctx.move_to(*pul)
    ctx.line_to(Wr[0], Wr[1])
    ctx.set_line_width(4)
    ctx.set_source_rgba(0.75, 0.78, 0.82, 0.9)
    ctx.stroke()
    capsule(ctx, (Wr[0] - 4, Wr[1] - 14), (Wr[0] + 4, Wr[1] + 14), 7, 7, color=P.rgb('#2a2d31'))
    ctx.restore()


# ------------------------------------------------------------ wrist curl close-up
def wrist_curl_closeup(ctx, tt, dur):
    z = lerp(1.5, 1.6, ease(tt / dur)) * (1 + 0.08 * math.exp(-tt * 9))
    camera(ctx, z, 540, 1250, rot=0.025 * (1 - tt / dur))
    paint_bg(ctx, dim=0.35)
    P.light_cone(ctx, 640, 200, 1800, 140, 600, 0.12)
    # bench pad (forearm resting on it, wrist over the edge)
    P.soft_shadow(ctx, 300, 1440, 620, 60, 0.6)
    P.rrect(ctx, -300, 1290, 920, 90, 26)
    P.src(ctx, P.vgrad(1290, 1380, [(0, P.rgb('#30353c')), (0.25, P.rgb('#1b1e22')), (1, P.rgb('#0b0c0e'))]))
    ctx.fill()
    ctx.rectangle(-300, 1380, 920, 40)
    P.src(ctx, P.rgb('#08090a'))
    ctx.fill()
    # upper arm (shoulder off frame, left), elbow resting on the pad, forearm palm up
    wr = (610, 1236)
    el = (350, 1228)
    capsule(ctx, (60, 960), el, 50, 46)
    ellipse(ctx, el[0], el[1], 48, 46)
    ctx.set_source(skin_grad((el[0] - 48, el[1] - 48), (el[0] + 48, el[1] + 48)))
    ctx.fill()
    capsule(ctx, el, wr, 44, 30)
    # tiny range of motion
    ph = (tt / 0.5) % 1.0
    p = 0.5 - 0.5 * math.cos(2 * math.pi * ph)
    an = lerp(0.65, -0.3, p)
    d = (math.cos(an), math.sin(an))
    up = (d[1], -d[0])
    hc = (wr[0] + d[0] * 66, wr[1] + d[1] * 66)
    ellipse(ctx, hc[0], hc[1], 64, 44, an)
    ctx.set_source(skin_grad((hc[0] - 50, hc[1] - 50), (hc[0] + 50, hc[1] + 50)))
    ctx.fill()
    # dumbbell seen end-on, resting in the palm
    dc = (hc[0] + d[0] * 18 + up[0] * 52, hc[1] + d[1] * 18 + up[1] * 52)
    ctx.arc(dc[0], dc[1], 50, 0, 2 * math.pi)
    P.src(ctx, P.vgrad(dc[1] - 50, dc[1] + 50, [(0, P.rgb('#6a7078')), (0.5, P.rgb('#3a3f46')), (1, P.rgb('#15181c'))]))
    ctx.fill()
    ctx.set_line_width(3)
    ctx.arc(dc[0], dc[1], 40, 0, 2 * math.pi)
    ctx.set_source_rgba(0, 0, 0, 0.4)
    ctx.stroke()
    ctx.arc(dc[0], dc[1], 13, 0, 2 * math.pi)
    P.src(ctx, P.rgb('#b8bec5'))
    ctx.fill()
    # fingers curled over the handle
    fc = (hc[0] + d[0] * 50 + up[0] * 26, hc[1] + d[1] * 50 + up[1] * 26)
    ellipse(ctx, fc[0], fc[1], 22, 38, an + 0.3)
    ctx.set_source(skin_grad((fc[0] - 25, fc[1] - 25), (fc[0] + 25, fc[1] + 25)))
    ctx.fill()


# ------------------------------------------------------------ dumbbell rack close-up
def rack_db(ctx, cx, by, h):
    w = 26 + h * 0.16
    hl = 62 + h * 0.15
    ctx.rectangle(cx - hl / 2, by - h / 2 - 9, hl, 18)
    P.src(ctx, P.vgrad(by - h / 2 - 9, by - h / 2 + 9, [(0, P.rgb('#d5d9de')), (1, P.rgb('#5b6068'))]))
    ctx.fill()
    for sx in (-1, 1):
        x = cx + sx * (hl / 2 + w / 2)
        P.rrect(ctx, x - w / 2, by - h, w, h, 10)
        P.src(ctx, P.hgrad(x - w / 2, x + w / 2, [(0, P.rgb('#0c0d0f')), (0.35, P.rgb('#3a3f46')), (1, P.rgb('#08090b'))]))
        ctx.fill()


def rack_closeup(ctx, tt, dur):
    z = lerp(1.45, 1.52, ease(tt / dur)) * (1 + 0.08 * math.exp(-tt * 9))
    camera(ctx, z, lerp(560, 585, tt / dur), 1190, rot=-0.02 * (1 - tt / dur))
    paint_bg(ctx, dim=0.3)
    P.light_cone(ctx, 400, 200, 1800, 140, 600, 0.10)
    shelf = 1330
    ctx.rectangle(-300, shelf, 1700, 30)
    P.src(ctx, P.vgrad(shelf, shelf + 30, [(0, P.rgb('#4b5058')), (1, P.rgb('#15181c'))]))
    ctx.fill()
    ctx.rectangle(-300, shelf + 30, 1700, 500)
    P.src(ctx, P.vgrad(shelf + 30, shelf + 400, [(0, P.rgb('#121417')), (1, P.rgb('#060708'))]))
    ctx.fill()
    for cx, h in ((545, 150), (760, 185), (990, 215), (1250, 240)):
        rack_db(ctx, cx, shelf, h)
    # lower tier: the heavy ones
    shelf2 = 1700
    ctx.rectangle(-300, shelf2, 1700, 30)
    P.src(ctx, P.vgrad(shelf2, shelf2 + 30, [(0, P.rgb('#4b5058')), (1, P.rgb('#15181c'))]))
    ctx.fill()
    for cx, h in ((200, 260), (520, 280), (850, 300)):
        rack_db(ctx, cx, shelf2, h)
    # the tiny one goes back on the rack
    k = ease(clamp(tt / 0.4))
    up = ease(clamp((tt - 0.55) / 0.35))
    by = lerp(1080, shelf, k)
    rack_db(ctx, 365, by, 82)
    # mannequin arm: elbow at the left frame edge, forearm down to a hand gripping the handle;
    # after the set-down the arm slides out to the left
    ox, oy = -330 * up, -50 * up
    hx, hy = 365 + ox, by - 41 + oy
    wr = (hx - 10, hy - 26)
    el = (wr[0] - 95, wr[1] - 150)
    capsule(ctx, (el[0] - 230, el[1] - 70), el, 34, 31)
    ellipse(ctx, el[0], el[1], 32, 31)
    ctx.set_source(skin_grad((el[0] - 32, el[1] - 32), (el[0] + 32, el[1] + 32)))
    ctx.fill()
    capsule(ctx, el, wr, 30, 21)
    ellipse(ctx, hx, hy - 6, 34, 25, 0.5)
    ctx.set_source(skin_grad((hx - 40, hy - 40), (hx + 40, hy + 30)))
    ctx.fill()
    ellipse(ctx, hx + 4, hy + 13, 28, 11, 0.1)
    ctx.set_source(skin_grad((hx - 30, hy), (hx + 30, hy + 26)))
    ctx.fill()


# ------------------------------------------------------------ front-view barbell (deadlift lockout)
def front_barbell(c, f, m):
    y = -470
    c.rectangle(-460, y - 9, 920, 18)
    P.src(c, P.vgrad(y - 9, y + 9, [(0, P.rgb('#d5d9de')), (1, P.rgb('#5b6068'))]))
    c.fill()
    for s in (-1, 1):
        for i, (off, w, h) in enumerate(((330, 40, 400), (374, 36, 400), (414, 22, 300))):
            x = s * off
            P.rrect(c, x - w / 2, y - h / 2, w, h, 10)
            P.src(c, P.hgrad(x - w / 2, x + w / 2, [(0, P.rgb('#0c0d0f')), (0.35, P.rgb('#3a3f46')), (1, P.rgb('#08090b'))]))
            c.fill()
    for s in (-1, 1):
        ellipse(c, s * (front_dims(f, m)['sh'] - 2), y, 24, 17)
        c.set_source(skin_grad((s * 110 - 20, y - 20), (s * 110 + 20, y + 20)))
        c.fill()


def lockout_front(ctx, tt, dur, f, m):
    z = lerp(1.06, 1.12, ease(tt / dur)) * (1 + 0.08 * math.exp(-tt * 9))
    camera(ctx, z, lerp(530, 550, tt / dur), 1125)
    paint_bg(ctx)
    P.light_cone(ctx, 540, 200, 1800, 130, 560, 0.09)
    P.floor_spot(ctx, 540, FEET_Y - 10, 520, 100)
    P.soft_shadow(ctx, 540, FEET_Y - 8, 300, 28, 0.6)
    sh = front_dims(f, m)['sh']
    figure_front(ctx, 540, FEET_Y, 1.0, f=f, m=m, arm_r=(sh - 2, -470), arm_l=(-(sh - 2), -470),
                 breath=math.sin(tt * 3.0) * 0.6, post=lambda c: front_barbell(c, f, m))


# ------------------------------------------------------------ SCENE 1 (0-3s) hook: tiny moves
def scene1(ctx, t):
    if t < 1.5:
        tt = t
        z = lerp(1.04, 1.12, ease(tt / 1.5))
        camera(ctx, z, 540, lerp(1090, 1110, tt / 1.5))
        paint_bg(ctx)
        P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
        P.floor_spot(ctx, 540, FEET_Y - 10)
        P.soft_shadow(ctx, 540, FEET_Y - 8, 170, 26, 0.6)
        raise_figure(ctx, 540, FEET_Y, 1.0, tt, F0, M0)
    else:
        tt = t - 1.5
        # punch in on the tiny dumbbell
        z = lerp(2.5, 2.65, ease(tt / 1.5))
        camera(ctx, z, lerp(735, 725, tt / 1.5), 1300, rot=0.02)
        paint_bg(ctx)
        P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
        raise_figure(ctx, 540, FEET_Y, 1.0, t, F0, M0)
    ctx.identity_matrix()
    vignette(ctx)
    if t >= 1.5:
        flash(ctx, 0.6 * math.exp(-(t - 1.5) * 20))
    text_block(ctx, ["NEW TO LIFTING?", "STOP DOING THIS"], 170, -0.3, t, box_line=1, size=126)


# ------------------------------------------------------------ SCENE 2 (3-7s) endless isolation, same body
def scene2(ctx, t):
    if t < 1.3:
        tt = t
        kickback_shot(ctx, tt, 1.3, 0.99, 0.09, rot=-0.02)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["KICKBACKS", "SET 19"], 190, 0.05, tt, box_line=1, size=130)
    elif t < 2.6:
        tt = t - 1.3
        wrist_curl_closeup(ctx, tt, 1.3)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["WRIST CURLS", "SET 31"], 190, 0.0, tt, box_line=1, size=130)
    else:
        tt = t - 2.6
        z = lerp(1.08, 1.15, ease(tt / 1.4))
        camera(ctx, z, lerp(555, 540, tt / 1.4), 1115)
        paint_bg(ctx)
        P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
        P.floor_spot(ctx, 540, FEET_Y - 10)
        P.soft_shadow(ctx, 540, FEET_Y - 8, 170, 26, 0.6)
        hold_figure(ctx, 540, FEET_Y, 1.0, tt, 0.98, 0.09)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["MONTHS LATER", "SAME BODY"], 190, 0.0, tt, box_line=1, size=128)
    ctx.identity_matrix()
    for cut in (1.3, 2.6):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 3 (7-12s) the big lifts
S3 = [
    ('squat', ["SQUAT", "LEGS + CORE"], 0.95, 0.11, 98, -0.015),
    ('deadlift', ["DEADLIFT", "BACK + LEGS"], 0.9, 0.14, 98, 0.02),
    ('bench', ["BENCH", "CHEST + ARMS"], 0.86, 0.17, 100, -0.02),
    ('row', ["ROW", "BACK + ARMS"], 0.82, 0.2, 96, 0.02),
]
S3_SEG = 5.0 / 4


def scene3(ctx, t):
    i = min(3, int(t / S3_SEG))
    tt = t - i * S3_SEG
    name, lines, f, m, pr, rot = S3[i]
    lift_shot(ctx, name, tt, S3_SEG, f, m, pr=pr, rot=rot, period=1.0 if name != 'deadlift' else 1.2)
    ctx.identity_matrix()
    vignette(ctx)
    flash(ctx, 0.7 * math.exp(-tt * 22))
    text_block(ctx, lines, 190, 0.0, tt, box_line=1, size=128)


# ------------------------------------------------------------ SCENE 4 (12-16s) one lift, many muscles; small stuff last
def scene4(ctx, t):
    if t < 1.4:
        tt = t
        lift_shot(ctx, 'press', tt, 1.4, 0.78, 0.26, pr=92, rot=0.015, period=1.1,
                  glow=0.0)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["ONE LIFT", "MANY MUSCLES"], 190, 0.0, tt, box_line=1, size=128)
    elif t < 2.7:
        tt = t - 1.4
        rack_closeup(ctx, tt, 1.3)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["SMALL STUFF?", "DO IT LAST"], 190, 0.0, tt, box_line=1, size=128)
    else:
        tt = t - 2.7
        lockout_front(ctx, tt, 1.3, 0.68, 0.34)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["BIG LIFTS", "COME FIRST"], 190, 0.0, tt, box_line=1, size=128)
    ctx.identity_matrix()
    for cut in (1.4, 2.7):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 5 (16-20s) payoff
def scene5(ctx, t):
    k = ease((t - 0.15) / 2.75)
    f = lerp(0.68, F1, k)
    m = lerp(0.34, M1, k)
    hips = ease((t - 2.0) / 0.8)
    z = lerp(1.14, 1.06, ease(t / 3.2))
    camera(ctx, z, lerp(560, 545, t / 4), lerp(1100, 1112, ease(t / 3.2)))
    paint_bg(ctx)
    P.light_cone(ctx, 540, 200, 1800, 130, 560, 0.09)
    P.floor_spot(ctx, 540, FEET_Y - 10, 420, 95)
    P.soft_shadow(ctx, 540, FEET_Y - 8, 180, 26, 0.6)
    figure_front(ctx, 540, FEET_Y, 1.0, f=f, m=m, hips=hips, breath=math.sin(t * 2.6) * 0.6)
    sw = (t - 0.3) / 2.6
    if 0 <= sw <= 1:
        x = lerp(-200, 1300, sw)
        g = cairo.LinearGradient(x - 160, 0, x + 160, 0)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 0.85, 1, 0.8, 0.10)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        P.src(ctx, g)
        ctx.rectangle(-500, 0, 2200, 2000)
        ctx.fill()
    ctx.identity_matrix()
    vignette(ctx)
    text_block(ctx, ["COMPOUNDS", "FIRST."], 170, 2.3, t, box_line=1, size=150)


# ------------------------------------------------------------ frame dispatch
SCENES = [(0, 3, scene1), (3, 7, scene2), (7, 12, scene3), (12, 16, scene4), (16, 20.001, scene5)]


def render_scene_at(tg):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()
    for a, b, fn in SCENES:
        if a <= tg < b:
            ctx.save()
            fn(ctx, tg - a)
            ctx.restore()
            break
    surf.flush()
    arr = np.ndarray((H, W, 4), np.uint8, surf.get_data()).copy()
    return arr


def hblur(arr, r):
    if r < 1:
        return arr
    r = int(r)
    a = arr.astype(np.float32)
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r), (0, 0)), mode='edge'), axis=1)
    out = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
    return out[:, :W].astype(np.uint8)


def shift(arr, dx):
    dx = int(dx)
    out = np.roll(arr, dx, axis=1)
    return out


WHIPS = [3.0, 7.0]
WHIP_HALF = 0.2


def frame(i):
    tg = i / FPS
    arr = render_scene_at(tg)
    for wt in WHIPS:
        d = tg - wt
        if -WHIP_HALF <= d < WHIP_HALF:
            k = 1 - abs(d) / WHIP_HALF  # 0..1 strength
            k = k ** 1.5
            dx = (-1 if d < 0 else 1) * k * 700
            arr = hblur(shift(arr, dx), 6 + k * 90)
    # flash cut at 12s is inside scene4 (punch-in); crossfade into scene 5
    if 16.0 <= tg < 16.3:
        a = (tg - 16.0) / 0.3
        prev = render_scene_at(15.99)
        arr = (arr.astype(np.float32) * a + prev.astype(np.float32) * (1 - a)).astype(np.uint8)
    return arr


def overlaps(h, r, margin=12):
    if h[2] < 0 or h[0] > W or h[3] < 0 or h[1] > H:
        return False
    return not (h[2] < r[0] - margin or h[0] > r[2] + margin or h[3] < r[1] - margin or h[1] > r[3] + margin)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'video'
    if mode == 'stills':
        for tg in [float(x) for x in sys.argv[2:]]:
            arr = frame(int(round(tg * FPS)))
            Image.fromarray(arr[:, :, [2, 1, 0]]).save(f'still_{tg:05.2f}.png')
        return
    if mode == 'check':
        # every frame: does any text box come near any head (incl. both sides of the dissolve)?
        bad = 0
        min_gap = 1e9
        for i in range(N):
            HEADS.clear()
            TEXTS.clear()
            frame(i)
            for h in HEADS:
                for r in TEXTS:
                    if h[3] >= 0 and h[1] <= H and h[2] >= 0 and h[0] <= W and h[2] > r[0] and h[0] < r[2]:
                        min_gap = min(min_gap, h[1] - r[3])
                    if overlaps(h, r):
                        bad += 1
                        print('OVERLAP t=%.2f head=%s text=%s' % (i / FPS, [int(v) for v in h], r[4]), flush=True)
        print('check done, overlaps:', bad, 'min vertical gap head-top to text-bottom: %.0f px' % min_gap)
        return
    out = sys.argv[2] if len(sys.argv) > 2 else 'silent.mp4'
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra',
                          '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium',
                          '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for i in range(N):
        p.stdin.write(frame(i).tobytes())
        if i % 60 == 0:
            print('frame', i, flush=True)
    p.stdin.close()
    p.wait()


if __name__ == '__main__':
    main()
