import math
import sys
import subprocess
import numpy as np
import cairo
from PIL import Image, ImageFilter
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'engine'))

from figure import (draw_front, draw_side, ik2, ellipse, lerp, clamp, ease, capsule,
                    L_THIGH, L_SHIN, L_TORSO, L_UA, L_FA)
import props as P

W, H = 1080, 1920
FPS = 30
N = 600
LIME = P.rgb('#c6ff3d')

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


# ------------------------------------------------------------ figure placement
FEET_Y = 1760


def figure_front(ctx, x, feet_y, k, **kw):
    ctx.save()
    ctx.translate(x, feet_y)
    ctx.scale(k, k)
    draw_front(ctx, **kw)
    ctx.restore()


# ------------------------------------------------------------ exercise helpers (from 001)
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
    S = (0, -740)
    Sj = (0, -712)
    hand = (lerp(40, 14, p), lerp(-745, -1008, p))
    E, Wr = ik_pick(Sj, hand, L_UA, L_FA, lambda j: j[0] + j[1])
    return dict(H=Hh, u=u, K=K, A=A2, K_far=Kf, A_far=Af2, E=E, W=Wr, E_far=(E[0] - 8, E[1] - 3),
                W_far=(Wr[0] - 8, Wr[1] - 3), front_sign=1, foot_dir=1), hand


EXS = [pose_bench, pose_row, pose_squat, pose_press]


def draw_exercise(ctx, idx, t, f, m):
    period = 1.05
    ph = (t / period) % 1.0
    p = 0.5 - 0.5 * math.cos(2 * math.pi * ph)
    if idx in (0,):
        p = p  # bench: start top, lower, press
    pose, bar = EXS[idx](p)
    # equipment behind
    if idx == 0:
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
    plate_far = (lambda c: plate_disk(c, bar[0] + 10, bar[1] - 6, 100, dark=0.6))
    plate_near = (lambda c: plate_disk(c, bar[0], bar[1], 105))
    draw_side(ctx, f, m, pose['H'], pose['u'], pose['K_far'], pose['A_far'], pose['K'], pose['A'],
              pose['E_far'], pose['W_far'], pose['E'], pose['W'], front_sign=pose['front_sign'],
              foot_dir=pose['foot_dir'], plate_far=plate_far, plate_near=plate_near)


# base physique (skinny-fat, same as episode 001)
F0, M0 = 1.0, 0.08
# end physique: moderate, believable recomp (a bit softer than 001's end)
F1, M1 = 0.28, 0.58


# ------------------------------------------------------------ gait helpers
def gait_foot(ph, A, lift, ground=-15):
    """Foot target relative to hip x. Stance (first half) moves back linearly, swing comes forward."""
    s = (ph / (2 * math.pi)) % 1.0
    if s < 0.5:
        k = s / 0.5
        return (A * (1 - 2 * k), ground)
    k = (s - 0.5) / 0.5
    return (-A + 2 * A * ease(k), ground - lift * math.sin(math.pi * k))


def gait_arm(Sj, u, ph, swing, bend):
    """Arm hanging from shoulder joint, swinging forward/back; bend = forearm angle (rad)."""
    lean = math.atan2(u[0], -u[1])
    th = swing * math.cos(ph) + lean * 0.5
    E = (Sj[0] + L_UA * math.sin(th), Sj[1] + L_UA * math.cos(th))
    th2 = th + bend
    Wr = (E[0] + L_FA * math.sin(th2), E[1] + L_FA * math.cos(th2))
    return E, Wr


def pose_gait(t, period, run=True):
    w = 2 * math.pi * t / period
    if run:
        A, lift, lean_deg, hy, bob = 120, 150, 11, -418, 9
        swing, bend = math.radians(38), math.radians(88)
    else:
        A, lift, lean_deg, hy, bob = 105, 45, 3, -440, 5
        swing, bend = math.radians(20), math.radians(18)
    Hh = (0, hy - bob * math.cos(2 * w))
    a = math.radians(lean_deg)
    u = unit(a)
    fn = gait_foot(w, A, lift)
    ff = gait_foot(w + math.pi, A, lift)
    A_n = (Hh[0] + fn[0], fn[1])
    A_f = (Hh[0] + ff[0], ff[1])
    K, A2 = ik_pick(Hh, A_n, L_THIGH, L_SHIN, lambda j: j[0])
    Kf, Af2 = ik_pick(Hh, A_f, L_THIGH, L_SHIN, lambda j: j[0])
    S = (Hh[0] + u[0] * L_TORSO, Hh[1] + u[1] * L_TORSO)
    Sj = (S[0] - u[0] * 28, S[1] - u[1] * 28)
    # arms opposite to same-side leg
    E, Wr = gait_arm(Sj, u, w + math.pi, swing, bend)
    Ef, Wf = gait_arm(Sj, u, w, swing, bend)
    return dict(H=Hh, u=u, K=K, A=A2, K_far=Kf, A_far=Af2, E=E, W=Wr,
                E_far=(Ef[0] - 6, Ef[1] - 4), W_far=(Wf[0] - 6, Wf[1] - 4), front_sign=1, foot_dir=1)


def draw_gait(ctx, pose, f, m):
    draw_side(ctx, f, m, pose['H'], pose['u'], pose['K_far'], pose['A_far'], pose['K'], pose['A'],
              pose['E_far'], pose['W_far'], pose['E'], pose['W'], front_sign=1, foot_dir=1)


def head_pos(pose):
    u = pose['u']
    Hh = pose['H']
    S = (Hh[0] + u[0] * L_TORSO, Hh[1] + u[1] * L_TORSO)
    n = (-u[1], u[0])
    return (S[0] + u[0] * 100 + n[0] * 12, S[1] + u[1] * 100 + n[1] * 12)


# ------------------------------------------------------------ treadmill (figure units, feet at y=0)
TM_SPEED = 4 * 120 / 0.62  # belt speed matches running stance (units/s)


def treadmill_back(ctx, t):
    # upright post + console in front of the runner (runner faces +x)
    ctx.new_path()
    ctx.move_to(300, 40)
    ctx.line_to(330, 40)
    ctx.line_to(420, -700)
    ctx.line_to(390, -700)
    ctx.close_path()
    P.src(ctx, P.hgrad(300, 420, [(0, P.rgb('#0c0e11')), (0.5, P.rgb('#2b3037')), (1, P.rgb('#0a0b0d'))]))
    ctx.fill()
    ctx.save()
    ctx.translate(400, -730)
    ctx.rotate(-0.35)
    P.rrect(ctx, -110, -40, 220, 70, 14)
    P.src(ctx, P.vgrad(-40, 30, [(0, P.rgb('#2a2f36')), (1, P.rgb('#0d0f12'))]))
    ctx.fill()
    P.rrect(ctx, -80, -26, 160, 34, 6)
    ctx.set_source_rgba(0.45, 0.85, 1.0, 0.55 + 0.15 * math.sin(t * 9))
    ctx.fill()
    ctx.restore()
    # side handrail (behind runner)
    ctx.set_line_width(16)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    ctx.move_to(395, -690)
    ctx.line_to(60, -640)
    P.src(ctx, P.rgb('#1b1f24'))
    ctx.stroke()


def treadmill_deck(ctx, t):
    P.soft_shadow(ctx, 0, 70, 430, 40, 0.6)
    P.rrect(ctx, -380, 8, 760, 58, 22)
    P.src(ctx, P.vgrad(8, 66, [(0, P.rgb('#2e333a')), (0.25, P.rgb('#16191d')), (1, P.rgb('#08090b'))]))
    ctx.fill()
    # belt surface + moving seams
    ctx.rectangle(-350, 8, 640, 12)
    P.src(ctx, P.rgb('#0b0c0e'))
    ctx.fill()
    off = (t * TM_SPEED) % 160
    for k in range(-1, 6):
        x = 290 - k * 160 - off
        if -350 < x < 290:
            ctx.rectangle(x, 9, 34, 9)
            ctx.set_source_rgba(1, 1, 1, 0.10)
            ctx.fill()
    # front motor hood
    P.rrect(ctx, 260, -6, 140, 70, 20)
    P.src(ctx, P.vgrad(-6, 64, [(0, P.rgb('#3a4048')), (1, P.rgb('#0e1013'))]))
    ctx.fill()


def sweat(ctx, hx, hy, t, n=10, seed=1, spread=1.0):
    """Little sweat drops flicking off the head (world units of current transform)."""
    for i in range(n):
        life = 0.55
        t0 = (i * 0.137 * 7 + seed * 0.31) % life
        age = (t + t0) % life
        cyc = int((t + t0) / life)
        rnd = (math.sin((i + 1) * 12.9898 + cyc * 78.233 + seed) * 43758.5453) % 1.0
        ang = math.radians(-160 + 140 * rnd)
        sp = 380 * spread
        x = hx + math.cos(ang) * 75 - 150 * age + math.cos(ang) * sp * age * 0.4
        y = hy + math.sin(ang) * 70 + math.sin(ang) * sp * age * 0.6 + 900 * age * age
        a = clamp(1 - age / life) * 0.85 * clamp((age - 0.04) / 0.06)
        if a <= 0:
            continue
        ctx.save()
        ctx.translate(x, y)
        ellipse(ctx, 0, 0, 6, 9)
        ctx.set_source_rgba(0.80, 0.92, 1.0, a)
        ctx.fill()
        ellipse(ctx, -2, -3, 2.5, 4)
        ctx.set_source_rgba(1, 1, 1, a)
        ctx.fill()
        ctx.restore()


TM_FEET = FEET_Y - 70   # feet height when standing on the deck
RUN_PERIOD = 0.62


def runner(ctx, t, x, k, f=F0, m=M0, sweat_n=0):
    ctx.save()
    ctx.translate(x, TM_FEET)
    ctx.scale(k, k)
    treadmill_back(ctx, t)
    pose = pose_gait(t, RUN_PERIOD, run=True)
    draw_gait(ctx, pose, f, m)
    treadmill_deck(ctx, t)
    if sweat_n:
        hx, hy = head_pos(pose)
        sweat(ctx, hx, hy, t, n=sweat_n)
    ctx.restore()


# ------------------------------------------------------------ SCENE 1 (0-3s) hook: endless treadmill
def scene1(ctx, t):
    z = lerp(1.04, 1.16, ease(t / 3.0))
    camera(ctx, z, 540, lerp(1060, 1110, t / 3))
    paint_bg(ctx)
    P.light_cone(ctx, 520, 200, 1800, 120, 520, 0.07)
    P.floor_spot(ctx, 520, FEET_Y, 460, 100)
    runner(ctx, t, 500, 1.0, sweat_n=4)
    ctx.identity_matrix()
    vignette(ctx)
    text_block(ctx, ["ENDLESS CARDIO?", "STILL SKINNY-FAT?"], 170, 0.0, t, box_line=1, size=132)


# ------------------------------------------------------------ SCENE 2 (3-7s) hours pass, same body
def wall_clock(ctx, cx, cy, r, t):
    P.soft_shadow(ctx, cx + 14, cy + 20, r * 1.08, r * 1.08, 0.55)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    P.src(ctx, P.rgb('#15181c'))
    ctx.fill()
    ctx.arc(cx, cy, r * 0.9, 0, 2 * math.pi)
    g = cairo.RadialGradient(cx - r * 0.3, cy - r * 0.3, 5, cx, cy, r)
    g.add_color_stop_rgb(0, *P.rgb('#f4f5f3'))
    g.add_color_stop_rgb(1, *P.rgb('#c9cdd2'))
    P.src(ctx, g)
    ctx.fill()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(12):
        a = i * math.pi / 6
        r0 = r * (0.70 if i % 3 == 0 else 0.76)
        ctx.new_path()
        ctx.move_to(cx + math.sin(a) * r0, cy - math.cos(a) * r0)
        ctx.line_to(cx + math.sin(a) * r * 0.83, cy - math.cos(a) * r * 0.83)
        ctx.set_line_width(14 if i % 3 == 0 else 7)
        P.src(ctx, P.rgb('#1b1f24'))
        ctx.stroke()
    # hands spin: hours fly by
    am = t * 2 * math.pi * 2.6
    ah = 0.6 + am / 12 * 3
    for ang, L, wd in ((ah, 0.45, 20), (am, 0.68, 12)):
        ctx.new_path()
        ctx.move_to(cx - math.sin(ang) * r * 0.1, cy + math.cos(ang) * r * 0.1)
        ctx.line_to(cx + math.sin(ang) * r * L, cy - math.cos(ang) * r * L)
        ctx.set_line_width(wd)
        P.src(ctx, P.rgb('#111317'))
        ctx.stroke()
    ctx.arc(cx, cy, 16, 0, 2 * math.pi)
    P.src(ctx, P.rgb('#7fae1f'))
    ctx.fill()
    # glass glare
    ctx.save()
    ctx.arc(cx, cy, r * 0.9, 0, 2 * math.pi)
    ctx.clip()
    g = cairo.LinearGradient(cx - r, cy - r, cx + r, cy + r)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(0.35, 1, 1, 1, 0.22)
    g.add_color_stop_rgba(0.5, 1, 1, 1, 0.0)
    P.src(ctx, g)
    ctx.paint()
    ctx.restore()


def scene2(ctx, t):
    if t < 1.3:
        # tight on the sweaty runner, handheld wobble
        tt = t
        z = lerp(1.75, 1.9, tt / 1.3)
        camera(ctx, z, 560 + 6 * math.sin(tt * 23), lerp(1010, 1030, tt / 1.3), rot=0.02 * math.sin(tt * 5))
        paint_bg(ctx, dim=0.1)
        P.light_cone(ctx, 520, 200, 1800, 120, 520, 0.07)
        runner(ctx, tt + 3.0, 500, 1.0, sweat_n=12)
    elif t < 2.3:
        # wall clock spinning: hours fly by
        tt = t - 1.3
        z = lerp(1.0, 1.12, ease(tt / 1.0))
        camera(ctx, z, 540, 900, rot=lerp(0.03, 0.0, tt))
        paint_bg(ctx, dim=0.2)
        wall_clock(ctx, 540, 880, 300, tt)
        flash(ctx, 0.0)
    else:
        # still the same body: standing, out of breath
        tt = t - 2.3
        z = lerp(1.12, 1.24, ease(tt / 1.7))
        camera(ctx, z, 540, lerp(1150, 1190, tt / 1.7))
        paint_bg(ctx)
        P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
        P.floor_spot(ctx, 540, FEET_Y - 10)
        P.soft_shadow(ctx, 540, FEET_Y - 8, 170, 26, 0.6)
        # small sweat puddle (slight humor)
        P.soft_shadow(ctx, 600, FEET_Y + 10, 120 * clamp(0.5 + tt / 2), 16, 0.35)
        ellipse(ctx, 610, FEET_Y + 6, 90 * clamp(0.4 + tt / 2), 10)
        ctx.set_source_rgba(0.75, 0.88, 1.0, 0.16)
        ctx.fill()
        pant = math.sin(tt * 11)
        figure_front(ctx, 540, FEET_Y, 1.0, f=F0, m=M0, hips=0.0, breath=pant * 1.6)
        ctx.save()
        ctx.translate(540, FEET_Y)
        sweat(ctx, 0, -930, tt, n=5, seed=4, spread=0.6)
        ctx.restore()
    ctx.identity_matrix()
    vignette(ctx)
    if t >= 1.3:
        flash(ctx, 0.6 * math.exp(-(t - 1.3) * 20))
    if t >= 2.3:
        flash(ctx, 0.6 * math.exp(-(t - 2.3) * 20))


# ------------------------------------------------------------ SCENE 3 (7-12s) lift heavy instead
EX_ORDER = [2, 0, 1, 3]  # squat, bench, row, press


def scene3(ctx, t):
    seg = 5.0 / 4
    i = min(3, int(t / seg))
    idx = EX_ORDER[i]
    tt = t - i * seg
    punch = 1 + 0.14 * math.exp(-tt * 9)
    configs = {
        2: dict(z=1.25, cx=560, cy=1400, fx=580, k=1.05, rot=-0.015),
        0: dict(z=1.3, cx=540, cy=1480, fx=540, k=1.12, rot=0.02),
        1: dict(z=1.3, cx=560, cy=1440, fx=500, k=1.15, rot=-0.02),
        3: dict(z=1.12, cx=540, cy=1300, fx=530, k=0.98, rot=0.015),
    }
    c = configs[idx]
    drift = tt / seg
    camera(ctx, c['z'] * punch * (1 + 0.03 * drift), c['cx'] + 20 * drift, c['cy'], rot=c['rot'] * (1 - drift * 0.5))
    paint_bg(ctx)
    P.light_cone(ctx, c['fx'], 200, 1800, 120, 560, 0.08)
    P.floor_spot(ctx, c['fx'], FEET_Y - 10, 460, 100)
    P.soft_shadow(ctx, c['fx'], FEET_Y - 8, 260, 30, 0.6)
    ctx.save()
    ctx.translate(c['fx'], FEET_Y)
    ctx.scale(c['k'], c['k'])
    draw_exercise(ctx, idx, tt, F0 - 0.02 * i, M0 + 0.025 * i)
    ctx.restore()
    ctx.identity_matrix()
    vignette(ctx)
    flash(ctx, 0.75 * math.exp(-tt * 22))


# ------------------------------------------------------------ SCENE 4 (12-16s) walk daily + protein
WALK_PERIOD = 1.0
WALK_V = 4 * 105 / WALK_PERIOD


def meal_plate(ctx, cx, cy, s=1.0):
    P.plate(ctx, cx, cy, 230 * s)
    P.rice(ctx, cx - 70 * s, cy + 10 * s, s * 0.9)
    P.chicken(ctx, cx + 60 * s, cy - 10 * s, s * 0.9)
    P.broccoli(ctx, cx - 10 * s, cy + 50 * s, s * 0.85, seed=1)
    P.broccoli(ctx, cx + 110 * s, cy + 45 * s, s * 0.75, seed=2)


def scene4(ctx, t):
    F, M = 0.9, 0.2
    if t < 2.1:
        # tracking shot: easy daily walk across the gym floor
        tt = t
        k = 0.95
        fx = 260 + WALK_V * k * tt
        camera(ctx, 1.22, fx + 60, 1330, rot=0.0)
        paint_bg(ctx)
        P.floor_spot(ctx, fx, FEET_Y - 10, 380, 90)
        P.soft_shadow(ctx, fx, FEET_Y - 4, 200, 26, 0.6)
        ctx.save()
        ctx.translate(fx, FEET_Y)
        ctx.scale(k, k)
        draw_gait(ctx, pose_gait(tt, WALK_PERIOD, run=False), F, M)
        ctx.restore()
    else:
        # protein plate, slow push-in
        tt = t - 2.1
        camera(ctx, lerp(1.6, 1.78, tt / 1.9), lerp(560, 590, tt / 1.9), 1340, rot=lerp(-0.02, 0.0, tt / 1.9))
        paint_bg(ctx, dim=0.2)
        P.table(ctx, -400, 1480, 1580, depth=560, front=400)
        for i, (x, y) in enumerate(((700, 1150), (800, 1175))):
            P.egg_whole(ctx, x, y, 1.0, brown=(i == 1))
        slide = 1 - ease(tt / 0.3)
        meal_plate(ctx, 560 + 400 * slide, 1390, 1.0)
        P.egg_half(ctx, 340, 1540, 1.1)
        P.egg_half(ctx, 460, 1565, 1.1)
    ctx.identity_matrix()
    vignette(ctx)
    if t >= 2.1:
        flash(ctx, 0.6 * math.exp(-(t - 2.1) * 20))


# ------------------------------------------------------------ SCENE 5 (16-20s) payoff
def scene5(ctx, t):
    k = ease((t - 0.15) / 2.75)
    f = lerp(0.9, F1, k)
    m = lerp(0.2, M1, k)
    hips = ease((t - 2.2) / 0.8)
    z = lerp(1.22, 1.08, ease(t / 3.2))
    camera(ctx, z, lerp(560, 540, t / 4), lerp(1300, 1110, ease(t / 3.2)))
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
    text_block(ctx, ["LIFT FIRST.", "CARDIO SECOND."], 170, 2.3, t, box_line=1, size=140)


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


WHIPS = [3.0, 12.0]
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
            arr = hblur(shift(arr, dx if d >= 0 else dx), 6 + k * 90)
    # crossfade into scene 5
    if 16.0 <= tg < 16.3:
        a = (tg - 16.0) / 0.3
        prev = render_scene_at(15.99)
        arr = (arr.astype(np.float32) * a + prev.astype(np.float32) * (1 - a)).astype(np.uint8)
    # impact flash at the 7s hard cut is in scene3
    return arr


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'video'
    if mode == 'stills':
        for tg in [float(x) for x in sys.argv[2:]]:
            arr = frame(int(round(tg * FPS)))
            Image.fromarray(arr[:, :, [2, 1, 0]]).save(f'still_{tg:05.2f}.png')
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
