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




# ------------------------------------------------------------ exercise helpers (from 001 / 006)
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


def draw_exercise(ctx, name, t, f, m, pr=100, period=1.05):
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
    return pose


CONF = {
    'bench': dict(z=1.3, cx=540, cy=1390, fx=540, k=1.12),
    'row': dict(z=1.15, cx=560, cy=1200, fx=500, k=1.15),
    'squat': dict(z=1.12, cx=560, cy=1130, fx=580, k=1.05),
    'deadlift': dict(z=1.12, cx=560, cy=1140, fx=540, k=1.08),
    'press': dict(z=1.05, cx=540, cy=1080, fx=530, k=0.98),
}


def lift_shot(ctx, name, tt, dur, f, m, pr, rot=0.0, punch_on=True, period=1.05, conf=None):
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
    draw_exercise(ctx, name, tt, f, m, pr=pr, period=period)
    ctx.restore()


# ------------------------------------------------------------ food helpers (from episode 001)
def eat_arm(t, period):
    """Right-hand target oscillating between table food and mouth (units)."""
    p = 0.5 - 0.5 * math.cos(2 * math.pi * t / period)
    p = ease(p)
    food = (205, -470)
    mouth = (22, -872)
    return (lerp(food[0], mouth[0], p), lerp(food[1], mouth[1], p)), p


def bite(ctx, x, y):
    ellipse(ctx, x, y - 6, 26, 16)
    P.src(ctx, P.rgb('#c77a31'))
    ctx.fill()
    ctx.rectangle(x - 26, y - 2, 52, 10)
    P.src(ctx, P.rgb('#4a2616'))
    ctx.fill()


def table_scene(ctx, t, zoom, cx, cy, plates, belly_extra=0.0, period=0.9, rot=0.0):
    camera(ctx, zoom, cx, cy, rot=rot)
    paint_bg(ctx, dim=0.15)
    ty = 1400
    feet = ty + 440
    tgt, p = eat_arm(t, period)
    figure_front(ctx, 540, feet, 1.0, f=F0 + belly_extra, m=M0, breath=math.sin(t * 2.5) * 0.5,
                 arm_r=tgt, arm_l=(-190, -455), hold_r=bite)
    P.table(ctx, -200, 1280, ty, depth=110, front=600)
    P.burger(ctx, 175, ty - 30, s=0.95, layers=3)
    P.fries(ctx, 900, ty - 20, s=1.0)
    if plates:
        P.plate_stack(ctx, 690, ty - 40, plates, s=0.9)
    P.soft_shadow(ctx, 430, ty - 30, 90, 16, 0.5)
    P.donut(ctx, 430, ty - 60, 70, seed=3)


def junk_closeup(ctx, tt, dur):
    """Pizza with cheese pull, shake and fries (001 scene 2 close-up)."""
    z = lerp(1.7, 1.85, tt / dur)
    camera(ctx, z, 540, 1320, rot=0.015)
    paint_bg(ctx, dim=0.25)
    P.table(ctx, -400, 1480, 1560, depth=520, front=400)
    P.pizza(ctx, 540, 1380, 330, lift=ease(tt / 0.7))
    P.milkshake(ctx, 900, 1300, s=0.8)
    P.fries(ctx, 170, 1330, s=0.9)


def donut_tower(ctx, tt, dur):
    z = lerp(1.6, 1.9, ease(tt / dur))
    camera(ctx, z, 560, 1330, rot=-0.015)
    paint_bg(ctx, dim=0.25)
    P.table(ctx, -400, 1480, 1560, depth=520, front=400)
    n = min(7, 3 + int(tt / 0.18))
    for i in range(n):
        P.donut(ctx, 380 + (i % 2) * 14, 1480 - i * 58, 120,
                icing=[P.rgb('#e98bb0'), P.rgb('#5a3320'), P.rgb('#f4efe6')][i % 3], seed=i)
    P.burger(ctx, 790, 1500, s=1.0, layers=4)
    P.milkshake(ctx, 120, 1520, s=0.9)


def meal_plate(ctx, cx, cy, s=1.0):
    P.plate(ctx, cx, cy, 230 * s)
    P.rice(ctx, cx - 70 * s, cy + 10 * s, s * 0.9)
    P.chicken(ctx, cx + 60 * s, cy - 10 * s, s * 0.9)
    P.broccoli(ctx, cx - 10 * s, cy + 50 * s, s * 0.85, seed=1)
    P.broccoli(ctx, cx + 110 * s, cy + 45 * s, s * 0.75, seed=2)


def standing(ctx, tt, dur, f, m, z0=1.08, z1=1.15, cy=1115):
    z = lerp(z0, z1, ease(tt / dur)) * (1 + 0.06 * math.exp(-tt * 9))
    camera(ctx, z, lerp(555, 540, tt / dur), cy)
    paint_bg(ctx)
    P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
    P.floor_spot(ctx, 540, FEET_Y - 10)
    P.soft_shadow(ctx, 540, FEET_Y - 8, 170, 26, 0.6)
    figure_front(ctx, 540, FEET_Y, 1.0, f=f, m=m, breath=math.sin(tt * 2.6) * 0.8)


def lean_meal_shot(ctx, tt, dur, f, m):
    """Mannequin at a counter, a normal plate slides in (a bit bigger than usual)."""
    camera(ctx, lerp(1.08, 1.13, ease(tt / dur)) * (1 + 0.06 * math.exp(-tt * 9)), lerp(560, 590, tt / dur), 1120)
    paint_bg(ctx)
    P.light_cone(ctx, 330, 200, 1800, 110, 420, 0.07)
    P.soft_shadow(ctx, 330, FEET_Y - 8, 150, 24, 0.6)
    figure_front(ctx, 330, FEET_Y, 0.95, f=f, m=m, breath=math.sin(tt * 3))
    P.table(ctx, 560, 1400, 1440, depth=90, front=400)
    slide = 1 - ease(tt / 0.35)
    meal_plate(ctx, 820 + 300 * slide, 1400, 1.05)
    # a second scoop of rice: a small surplus, not a feast
    drop = ease(clamp((tt - 0.45) / 0.3))
    if tt > 0.45:
        P.rice(ctx, 760, lerp(1250, 1395, drop), 0.55)


def real_food_closeup(ctx, tt, dur):
    """Normal food on a wooden table, pizza included (no diet-ad look)."""
    z = lerp(1.42, 1.52, ease(tt / dur)) * (1 + 0.06 * math.exp(-tt * 9))
    camera(ctx, z, lerp(540, 555, tt / dur), 1330, rot=0.012)
    paint_bg(ctx, dim=0.22)
    P.table(ctx, -400, 1480, 1600, depth=560, front=400)
    P.pizza(ctx, 330, 1170, 150)
    P.yogurt_bowl(ctx, 790, 1200, 125)
    P.egg_whole(ctx, 640, 1200, 0.85)
    P.egg_whole(ctx, 700, 1235, 0.85, brown=True)
    meal_plate(ctx, 560, 1440, 1.18)


# base physique (skinny-fat, same as episode 001) and a moderate lean-bulk end state
F0, M0 = 1.0, 0.08
F1, M1 = 0.42, 0.58


# ------------------------------------------------------------ SCENE 1 (0-3s) hook: eating everything
def scene1(ctx, t):
    if t < 1.5:
        tt = t
        table_scene(ctx, tt, lerp(1.15, 1.22, tt / 1.5), 540, 1100, plates=3, period=0.75)
    else:
        tt = t - 1.5
        junk_closeup(ctx, tt, 1.5)
    ctx.identity_matrix()
    vignette(ctx)
    if t >= 1.5:
        flash(ctx, 0.6 * math.exp(-(t - 1.5) * 20))
    text_block(ctx, ["BULKING?", "DON'T EAT LIKE THIS"], 170, -0.3, t, box_line=1, size=130)


# ------------------------------------------------------------ SCENE 2 (3-7s) the dirty bulk
def scene2(ctx, t):
    if t < 1.3:
        tt = t
        donut_tower(ctx, tt, 1.3)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["DIRTY BULK", "EAT EVERYTHING"], 190, 0.05, tt, box_line=1, size=130)
    elif t < 2.6:
        tt = t - 1.3
        n = 4 + int(tt / 0.14)
        table_scene(ctx, tt, lerp(1.25, 1.32, tt / 1.3), 560, 1060, plates=min(n, 11), belly_extra=0.06,
                    period=0.55, rot=0.012)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["PLATE 11", "STILL GOING"], 190, 0.0, tt, box_line=1, size=130)
    else:
        tt = t - 2.6
        standing(ctx, tt, 1.4, 1.14, 0.12)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["SOME MUSCLE", "LOTS OF FAT"], 190, 0.0, tt, box_line=1, size=128)
    ctx.identity_matrix()
    for cut in (1.3, 2.6):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 3 (7-12s) the lean bulk
S3_SEG = 5.0 / 4


def scene3(ctx, t):
    i = min(3, int(t / S3_SEG))
    tt = t - i * S3_SEG
    if i == 0:
        lean_meal_shot(ctx, tt, S3_SEG, 0.97, 0.10)
        lines = ["LEAN BULK", "SMALL SURPLUS"]
    elif i == 1:
        real_food_closeup(ctx, tt, S3_SEG)
        lines = ["MOSTLY REAL FOOD", "PIZZA SOMETIMES"]
    elif i == 2:
        lift_shot(ctx, 'bench', tt, S3_SEG, 0.94, 0.16, pr=98, rot=-0.02)
        lines = ["LIFT HARD", "EVERY WEEK"]
    else:
        lift_shot(ctx, 'squat', tt, S3_SEG, 0.9, 0.22, pr=102, rot=0.02)
        lines = ["ADD WEIGHT", "TO THE BAR"]
    ctx.identity_matrix()
    vignette(ctx)
    flash(ctx, 0.7 * math.exp(-tt * 22))
    text_block(ctx, lines, 190, 0.0, tt, box_line=1, size=128)


# ------------------------------------------------------------ SCENE 4 (12-16s) slow gain, mostly muscle
def scene4(ctx, t):
    if t < 1.4:
        tt = t
        lift_shot(ctx, 'deadlift', tt, 1.4, 0.82, 0.3, pr=104, rot=0.015, period=1.2)
        lines = ["SLOWER GAINS", "MORE MUSCLE"]
    elif t < 2.7:
        tt = t - 1.4
        lift_shot(ctx, 'row', tt, 1.3, 0.76, 0.36, pr=100, rot=-0.02)
        lines = ["STRENGTH UP", "EVERY MONTH"]
    else:
        tt = t - 2.7
        standing(ctx, tt, 1.3, 0.62, 0.44, z0=1.12, z1=1.06, cy=1112)
        lines = ["WAY LESS", "FAT GAIN"]
    ctx.identity_matrix()
    vignette(ctx)
    text_block(ctx, lines, 190, 0.0, tt, box_line=1, size=128)
    for cut in (1.4, 2.7):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 5 (16-20s) payoff
def scene5(ctx, t):
    k = ease((t - 0.15) / 2.75)
    f = lerp(0.62, F1, k)
    m = lerp(0.44, M1, k)
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
    text_block(ctx, ["LEAN BULK", "WINS."], 170, 2.3, t, box_line=1, size=150)


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
