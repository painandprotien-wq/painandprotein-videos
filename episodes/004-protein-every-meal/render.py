import math
import random
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

# base physique (skinny-fat, same as episode 001)
F0, M0 = 1.0, 0.08
# end physique: moderate, believable (a few months of steady progress)
F1, M1 = 0.30, 0.55


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


def cobweb(ctx, x, y, r, a=0.5):
    """Thin dusty cobweb on a plate (slight humor: this weight has not moved in ages)."""
    ctx.save()
    ctx.set_line_width(2.2)
    ctx.set_source_rgba(0.92, 0.94, 0.96, a)
    angs = [math.radians(d) for d in (-150, -122, -95, -68, -40)]
    for an in angs:
        ctx.new_path()
        ctx.move_to(x + math.cos(an) * r * 0.24, y + math.sin(an) * r * 0.24)
        ctx.line_to(x + math.cos(an) * r * 1.12, y + math.sin(an) * r * 1.12)
        ctx.stroke()
    for k in range(1, 5):
        rr = r * (0.3 + 0.2 * k)
        ctx.new_path()
        for j, an in enumerate(angs):
            px, py = x + math.cos(an) * rr, y + math.sin(an) * rr
            if j == 0:
                ctx.move_to(px, py)
            else:
                pa = angs[j - 1]
                mid = (an + pa) / 2
                sag = rr * 0.86
                ctx.curve_to(x + math.cos(mid) * sag, y + math.sin(mid) * sag,
                             x + math.cos(mid) * sag, y + math.sin(mid) * sag, px, py)
        ctx.stroke()
    ctx.restore()


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


EXS = {'bench': pose_bench, 'row': pose_row, 'squat': pose_squat}


def draw_exercise(ctx, name, t, f, m, pr=100, web=0.0, period=1.05):
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

    def plate_near(c):
        plate_disk(c, bar[0], bar[1], pr)
        if web > 0:
            cobweb(c, bar[0], bar[1], pr, web)
    draw_side(ctx, f, m, pose['H'], pose['u'], pose['K_far'], pose['A_far'], pose['K'], pose['A'],
              pose['E_far'], pose['W_far'], pose['E'], pose['W'], front_sign=pose['front_sign'],
              foot_dir=pose['foot_dir'], plate_far=plate_far, plate_near=plate_near)


CONF = {
    'bench': dict(z=1.3, cx=540, cy=1390, fx=540, k=1.12),
    'row': dict(z=1.3, cx=560, cy=1340, fx=500, k=1.15),
    'squat': dict(z=1.25, cx=560, cy=1320, fx=580, k=1.05),
}


def lift_shot(ctx, name, tt, dur, f, m, pr, web=0.0, rot=0.0, punch_on=True, zmul=1.0, period=1.05, cyoff=0.0):
    c = CONF[name]
    punch = 1 + 0.14 * math.exp(-tt * 9) if punch_on else 1.0
    drift = tt / dur
    camera(ctx, c['z'] * zmul * punch * (1 + 0.03 * drift), c['cx'] + 20 * drift, c['cy'] - cyoff, rot=rot * (1 - drift * 0.5))
    paint_bg(ctx)
    P.light_cone(ctx, c['fx'], 200, 1800, 120, 560, 0.08)
    P.floor_spot(ctx, c['fx'], FEET_Y - 10, 460, 100)
    P.soft_shadow(ctx, c['fx'], FEET_Y - 8, 260, 30, 0.6)
    ctx.save()
    ctx.translate(c['fx'], FEET_Y)
    ctx.scale(c['k'], c['k'])
    draw_exercise(ctx, name, tt, f, m, pr=pr, web=web, period=period)
    ctx.restore()




# ------------------------------------------------------------ food helpers (episode 004)
def toast(ctx, cx, cy, s=1.0, rot=0.0):
    """Plain slice of toast, seen from above at an angle."""
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(rot)
    ctx.scale(s, s * 0.62)
    P.soft_shadow(ctx, 8, 70, 95, 22, 0.45)
    ctx.new_path()
    ctx.move_to(-80, 80)
    ctx.line_to(-82, -20)
    ctx.curve_to(-120, -60, -90, -120, -40, -110)
    ctx.curve_to(-10, -140, 10, -140, 40, -110)
    ctx.curve_to(90, -120, 120, -60, 82, -20)
    ctx.line_to(80, 80)
    ctx.close_path()
    P.src(ctx, P.vgrad(-140, 80, [(0, P.rgb('#b9783a')), (1, P.rgb('#8a5222'))]))
    ctx.fill_preserve()
    ctx.restore()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(rot)
    ctx.scale(s * 0.84, s * 0.62 * 0.84)
    ctx.new_path()
    ctx.move_to(-80, 80)
    ctx.line_to(-82, -20)
    ctx.curve_to(-120, -60, -90, -120, -40, -110)
    ctx.curve_to(-10, -140, 10, -140, 40, -110)
    ctx.curve_to(90, -120, 120, -60, 82, -20)
    ctx.line_to(80, 80)
    ctx.close_path()
    P.src(ctx, P.vgrad(-140, 80, [(0, P.rgb('#e8c48a')), (1, P.rgb('#d29b55'))]))
    ctx.fill()
    ctx.restore()


def mug(ctx, cx, by, s=1.0, steam_t=0.0):
    """Plain gray coffee mug, no print."""
    w, h = 120 * s, 150 * s
    P.soft_shadow(ctx, cx + 8, by, w * 0.62, 14 * s, 0.5)
    # handle
    ctx.set_line_width(18 * s)
    ctx.new_path()
    ctx.arc(cx + w * 0.5, by - h * 0.52, 34 * s, -math.pi / 2, math.pi / 2)
    P.src(ctx, P.rgb('#59616b'))
    ctx.stroke()
    P.rrect(ctx, cx - w / 2, by - h, w, h, 18 * s)
    P.src(ctx, P.hgrad(cx - w / 2, cx + w / 2, [(0, P.rgb('#4a525c')), (0.35, P.rgb('#8b949e')), (1, P.rgb('#363c43'))]))
    ctx.fill()
    ellipse(ctx, cx, by - h, w / 2, 16 * s)
    P.src(ctx, P.rgb('#3b2416'))
    ctx.fill()
    # steam
    ctx.set_line_width(7 * s)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in (-1, 1):
        ctx.new_path()
        x0 = cx + k * 22 * s
        for j in range(12):
            yy = by - h - 20 * s - j * 9 * s
            xx = x0 + 10 * s * math.sin(j * 0.7 + steam_t * 5 + k)
            ctx.line_to(xx, yy) if j else ctx.move_to(xx, yy)
        ctx.set_source_rgba(1, 1, 1, 0.22)
        ctx.stroke()


def chips_bowl(ctx, cx, cy, r):
    P.bowl(ctx, cx, cy, r, color=P.rgb('#6b5a4a'), fill=P.rgb('#e2b44c'))
    rnd = random.Random(11)
    for _ in range(26):
        x = cx + rnd.uniform(-0.75, 0.75) * r
        y = cy + rnd.uniform(-0.55, 0.12) * r
        ellipse(ctx, x, y, rnd.uniform(18, 26) * r / 100, rnd.uniform(9, 14) * r / 100, rnd.uniform(-1, 1))
        P.src(ctx, rnd.choice([P.rgb('#f2c75c'), P.rgb('#e0a93a'), P.rgb('#f7d77a')]))
        ctx.fill()


def cottage_bowl(ctx, cx, cy, r):
    P.bowl(ctx, cx, cy, r, color=P.rgb('#7a8a76'), fill=P.rgb('#f4f1ea'))
    rnd = random.Random(4)
    for _ in range(80):
        x = cx + rnd.uniform(-0.8, 0.8) * r
        y = cy + rnd.uniform(-0.3, 0.3) * r
        if ((x - cx) / r) ** 2 + ((y - cy) / (r * 0.34)) ** 2 > 0.8:
            continue
        rr = rnd.uniform(7, 12) * r / 100
        ctx.arc(x, y, rr, 0, 2 * math.pi)
        g = cairo.RadialGradient(x - rr * 0.3, y - rr * 0.4, 1, x, y, rr)
        g.add_color_stop_rgb(0, 1, 1, 0.99)
        g.add_color_stop_rgb(1, *P.rgb('#d6d1c6'))
        P.src(ctx, g)
        ctx.fill()


def berries(ctx, cx, cy, n=5, seed=3):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = cx + rnd.uniform(-40, 40), cy + rnd.uniform(-14, 14)
        ctx.arc(x, y, 12, 0, 2 * math.pi)
        g = cairo.RadialGradient(x - 3, y - 3, 1, x, y, 12)
        g.add_color_stop_rgb(0, *P.rgb('#6c7fd6'))
        g.add_color_stop_rgb(1, *P.rgb('#24285e'))
        P.src(ctx, g)
        ctx.fill()


def toast_bite(ctx, x, y):
    P.rrect(ctx, x - 24, y - 20, 48, 34, 8)
    P.src(ctx, P.rgb('#d29b55'))
    ctx.fill()
    ctx.set_line_width(5)
    P.rrect(ctx, x - 24, y - 20, 48, 34, 8)
    P.src(ctx, P.rgb('#8a5222'))
    ctx.stroke()


def chicken_bite(ctx, x, y):
    P.rrect(ctx, x - 22, y - 16, 44, 30, 12)
    P.src(ctx, P.vgrad(y - 16, y + 14, [(0, P.rgb('#e9c38f')), (1, P.rgb('#a8692f'))]))
    ctx.fill()


def eat_arm(t, period):
    """Right-hand target oscillating between table food and mouth (units)."""
    p = 0.5 - 0.5 * math.cos(2 * math.pi * t / period)
    p = ease(p)
    food = (205, -470)
    mouth = (22, -872)
    return (lerp(food[0], mouth[0], p), lerp(food[1], mouth[1], p))


def eating_shot(ctx, t, zoom, cx, cy, food, hold, f=F0, m=M0, period=1.1, dim=0.15):
    camera(ctx, zoom, cx, cy)
    paint_bg(ctx, dim=dim)
    ty = 1400
    feet = ty + 440
    P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.06)
    figure_front(ctx, 540, feet, 1.0, f=f, m=m, breath=math.sin(t * 2.5) * 0.5,
                 arm_r=eat_arm(t, period), arm_l=(-190, -455), hold_r=hold)
    P.table(ctx, -200, 1280, ty, depth=110, front=600)
    food(ctx, ty)


def food_closeup(ctx, t, dur, draw, z0=1.55, z1=1.68, cx=540, cy=1330, rot=0.0):
    camera(ctx, lerp(z0, z1, ease(t / dur)), cx + 15 * t / dur, cy, rot=rot * (1 - t / dur))
    paint_bg(ctx, dim=0.25)
    P.table(ctx, -400, 1480, 1580, depth=560, front=400)
    draw(ctx, t)


# ------------------------------------------------------------ SCENE 1 (0-3s) hook: protein only at dinner?
def breakfast_small(ctx, ty):
    P.plate(ctx, 780, ty - 30, 130)
    toast(ctx, 780, ty - 40, 0.8, rot=0.1)
    mug(ctx, 300, ty - 10, 0.9)


def scene1(ctx, t):
    if t < 1.6:
        tt = t
        eating_shot(ctx, tt, lerp(1.12, 1.2, ease(tt / 1.6)), 540, 1150, breakfast_small, toast_bite, period=1.2)
    else:
        tt = t - 1.6

        def d(c, tt):
            P.plate(c, 470, 1420, 260)
            toast(c, 450, 1400, 1.25, rot=0.08)
            mug(c, 860, 1440, 1.05, steam_t=tt)
        food_closeup(ctx, tt, 1.4, d, 1.5, 1.62, 600, 1300, rot=0.02)
    ctx.identity_matrix()
    vignette(ctx)
    flash(ctx, 0.6 * math.exp(-(t - 1.6) * 20) if t >= 1.6 else 0.0)
    text_block(ctx, ["PROTEIN ONLY", "AT DINNER?"], 170, 0.0, t, box_line=1, size=140)


# ------------------------------------------------------------ SCENE 2 (3-7s) snacks all day, then one giant dinner
def chicken_mountain(ctx, cx, by, n, s=1.0):
    """A comically tall pile of chicken on one plate (slight humor)."""
    P.plate(ctx, cx, by, 300 * s)
    rnd = random.Random(7)
    rows = [3, 3, 2, 2, 1, 1]
    i = 0
    for r, cnt in enumerate(rows):
        for j in range(cnt):
            if i >= n:
                return
            x = cx + ((j - (cnt - 1) / 2) * 120 + rnd.uniform(-14, 14)) * s
            y = by - (10 + r * 58) * s
            P.chicken(ctx, x, y, (0.72 - r * 0.03) * s)
            i += 1


def scene2(ctx, t):
    if t < 1.3:
        tt = t

        def d(c, tt):
            chips_bowl(c, 420, 1380, 230)
            mug(c, 860, 1470, 0.95, steam_t=tt)
        food_closeup(ctx, tt, 1.3, d, 1.5, 1.62, 560, 1300, rot=-0.02)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["LUNCH?", "CHIPS."], 200, 0.05, tt, box_line=1, size=130)
    elif t < 2.7:
        tt = t - 1.3
        n = min(12, 3 + int(tt / 0.08))

        def d(c, tt):
            chicken_mountain(c, 540, 1500, n)
        food_closeup(ctx, tt, 1.4, d, 1.32, 1.42, 540, 1280, rot=0.02)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["DINNER?", "ALL OF IT."], 200, 0.05, tt, box_line=1, size=130)
    else:
        tt = t - 2.7

        def food(c, ty):
            chicken_mountain(c, 800, ty - 30, 12, s=0.62)
        eating_shot(ctx, tt, lerp(1.2, 1.27, tt / 1.3), 560, 1170, food, chicken_bite, period=0.7)
        ctx.identity_matrix()
        vignette(ctx)
    ctx.identity_matrix()
    for cut in (1.3, 2.7):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 3 (7-12s) protein at every meal, simple examples
def s3_breakfast(c, tt):
    P.plate(c, 380, 1420, 240)
    P.egg_half(c, 300, 1410, 1.3)
    P.egg_half(c, 440, 1430, 1.3)
    P.spinach(c, 380, 1480, 0.9)
    toast(c, 470, 1360, 0.7, rot=-0.2)
    P.yogurt_bowl(c, 820, 1380, 170)


def s3_lunch(c, tt):
    P.plate(c, 540, 1420, 300)
    P.rice(c, 430, 1430, 1.1)
    P.chicken(c, 600, 1400, 1.05)
    P.broccoli(c, 520, 1480, 1.0, seed=1)
    P.broccoli(c, 680, 1470, 0.9, seed=2)


def s3_snack(c, tt):
    cottage_bowl(c, 470, 1400, 220)
    berries(c, 470, 1360, 6, seed=5)
    P.egg_whole(c, 830, 1360, 1.0, brown=True)
    P.egg_whole(c, 900, 1420, 1.0)


def s3_dinner(c, tt):
    P.plate(c, 420, 1430, 260)
    P.salmon(c, 400, 1410, 1.0)
    P.tomatoes(c, 520, 1460, 1.0)
    P.beans_bowl(c, 830, 1400, 140)


S3 = [
    (s3_breakfast, "BREAKFAST", "EGGS OR YOGURT", 600, -0.02),
    (s3_lunch, "LUNCH", "CHICKEN OR FISH", 540, 0.02),
    (s3_snack, "SNACK", "COTTAGE CHEESE", 600, -0.015),
    (s3_dinner, "DINNER", "BEANS OR SALMON", 580, 0.015),
]


def scene3(ctx, t):
    seg = 5.0 / 4
    i = min(3, int(t / seg))
    tt = t - i * seg
    draw, l1, l2, cx, rot = S3[i]
    # food slides in from the side, slight punch-in
    slide = 1 - ease(clamp(tt / 0.3))
    punch = 1 + 0.1 * math.exp(-tt * 9)
    camera(ctx, 1.45 * punch * (1 + 0.04 * tt / seg), cx + 15 * tt / seg, 1310, rot=rot)
    paint_bg(ctx, dim=0.25)
    P.table(ctx, -400, 1480, 1580, depth=560, front=400)
    ctx.save()
    ctx.translate(((-1) ** i) * 420 * slide, 0)
    draw(ctx, tt)
    ctx.restore()
    ctx.identity_matrix()
    vignette(ctx)
    flash(ctx, 0.7 * math.exp(-tt * 22))
    text_block(ctx, [l1, l2], 190, 0.0, tt, box_line=1, size=124)


# ------------------------------------------------------------ SCENE 4 (12-16s) simple food, then lift
def lunch_plate(c, ty):
    P.plate(c, 790, ty - 30, 150)
    P.rice(c, 750, ty - 26, 0.6)
    P.chicken(c, 820, ty - 34, 0.6)
    P.broccoli(c, 790, ty - 6, 0.55, seed=1)
    P.yogurt_bowl(c, 290, ty - 20, 95)


def scene4(ctx, t):
    if t < 1.3:
        tt = t
        eating_shot(ctx, tt, lerp(1.15, 1.22, ease(tt / 1.3)), 540, 1150, lunch_plate, chicken_bite,
                    f=0.94, m=0.13, period=1.15, dim=0.1)
        ctx.identity_matrix()
        vignette(ctx)
    elif t < 2.7:
        tt = t - 1.3
        lift_shot(ctx, 'row', tt, 1.4, 0.9, 0.18, pr=92, rot=0.02, period=1.0)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["THEN", "LIFT HARD"], 190, 0.0, tt, box_line=1, size=124)
    else:
        tt = t - 2.7
        lift_shot(ctx, 'bench', tt, 1.3, 0.86, 0.22, pr=96, rot=-0.015, period=1.0, cyoff=115.0)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["THEN", "LIFT HARD"], 190, -10.0, tt, box_line=1, size=124)
    ctx.identity_matrix()
    for cut in (1.3, 2.7):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 5 (16-20s) payoff
def scene5(ctx, t):
    k = ease((t - 0.15) / 2.75)
    f = lerp(0.84, F1, k)
    m = lerp(0.2, M1, k)
    z = lerp(1.22, 1.08, ease(t / 3.2))
    camera(ctx, z, lerp(560, 540, t / 4), lerp(1300, 1110, ease(t / 3.2)))
    paint_bg(ctx)
    P.light_cone(ctx, 540, 200, 1800, 130, 560, 0.09)
    P.floor_spot(ctx, 540, FEET_Y - 10, 420, 95)
    P.soft_shadow(ctx, 540, FEET_Y - 8, 180, 26, 0.6)
    figure_front(ctx, 540, FEET_Y, 1.0, f=f, m=m, hips=0.0, breath=math.sin(t * 2.6) * 0.6)
    # light sweep while transforming
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
    text_block(ctx, ["PROTEIN", "EVERY MEAL"], 170, 2.3, t, box_line=1, size=140)


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
