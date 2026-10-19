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






# ------------------------------------------------------------ barbell close-up (from episode 003)
def bar_plate(ctx, x, cy, w, h, shade=1.0):
    P.rrect(ctx, x - w / 2, cy - h / 2, w, h, min(14, w * 0.35))
    P.src(ctx, P.hgrad(x - w / 2, x + w / 2, [(0, tuple(v * shade for v in P.rgb('#0c0d0f'))),
                                             (0.35, tuple(v * shade for v in P.rgb('#3a3f46'))),
                                             (1, tuple(v * shade for v in P.rgb('#08090b')))]))
    ctx.fill()
    ctx.rectangle(x - w / 2 + 4, cy - h / 2 + 12, 3, h - 24)
    ctx.set_source_rgba(1, 1, 1, 0.08)
    ctx.fill()


def barbell_closeup(ctx, t, cy=1120):
    """Close-up of the bar sleeve: one more plate slides on next to the others."""
    ctx.rectangle(-300, cy - 16, 720, 32)
    P.src(ctx, P.vgrad(cy - 16, cy + 16, [(0, P.rgb('#9aa1aa')), (0.4, P.rgb('#d5d9de')), (1, P.rgb('#4b5058'))]))
    ctx.fill()
    P.rrect(ctx, 400, cy - 52, 46, 104, 10)
    P.src(ctx, P.vgrad(cy - 52, cy + 52, [(0, P.rgb('#7d848d')), (0.4, P.rgb('#c9ced4')), (1, P.rgb('#3c4047'))]))
    ctx.fill()
    ctx.rectangle(446, cy - 30, 900, 60)
    P.src(ctx, P.vgrad(cy - 30, cy + 30, [(0, P.rgb('#a3aab3')), (0.35, P.rgb('#e4e7ea')), (1, P.rgb('#50555d'))]))
    ctx.fill()
    bar_plate(ctx, 490, cy, 72, 600)
    bar_plate(ctx, 566, cy, 64, 600, 0.92)
    k = ease(clamp((t - 0.1) / 0.45))
    x = lerp(1250, 636, k)
    bar_plate(ctx, x, cy, 56, 470, 1.05)
    kc = ease(clamp((t - 0.6) / 0.3))
    cx2 = lerp(1300, 690, kc)
    P.rrect(ctx, cx2 - 18, cy - 44, 36, 88, 8)
    P.src(ctx, P.vgrad(cy - 44, cy + 44, [(0, P.rgb('#6b7179')), (0.4, P.rgb('#b8bec5')), (1, P.rgb('#2f3237'))]))
    ctx.fill()


# ------------------------------------------------------------ bathroom scale helpers (episode 005)
SCALE_NUM = "78.4"
LCD_FONT = "DejaVu Sans Mono"


def lcd_text(ctx, cx, cy, txt, size, a=1.0):
    ctx.save()
    ctx.select_font_face(LCD_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    ext = ctx.text_extents(txt)
    tx = cx - ext.width / 2 - ext.x_bearing
    ty = cy - ext.height / 2 - ext.y_bearing
    # glow
    for r, al in ((6, 0.10), (3, 0.18)):
        ctx.move_to(tx, ty)
        ctx.text_path(txt)
        ctx.set_line_width(r * 2)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(0.55, 0.9, 1.0, al * a)
        ctx.stroke()
    ctx.move_to(tx, ty)
    ctx.text_path(txt)
    ctx.set_source_rgba(0.82, 0.97, 1.0, a)
    ctx.fill()
    ctx.restore()


def flicker_num(t, settle=0.55, seed=0):
    """Digits roll for a moment, then land on the same number as always."""
    if t >= settle:
        return SCALE_NUM
    rnd = random.Random(int(t * 30) + seed * 100)
    return "%d.%d" % (rnd.randint(70, 86), rnd.randint(0, 9))


def scale_front(ctx, x, top_y, k=1.0, num=SCALE_NUM):
    """Small floor scale seen from the front (world coords). top_y = standing surface."""
    w = 360 * k
    P.soft_shadow(ctx, x, top_y + 30 * k, w * 0.6, 22 * k, 0.6)
    # front edge
    P.rrect(ctx, x - w / 2, top_y - 4 * k, w, 30 * k, 12 * k)
    P.src(ctx, P.vgrad(top_y, top_y + 26 * k, [(0, P.rgb('#3a4048')), (1, P.rgb('#0d0f12'))]))
    ctx.fill()
    # top glass
    P.rrect(ctx, x - w / 2, top_y - 30 * k, w, 34 * k, 14 * k)
    P.src(ctx, P.hgrad(x - w / 2, x + w / 2, [(0, P.rgb('#1a1e23')), (0.4, P.rgb('#4b535d')), (1, P.rgb('#15181c'))]))
    ctx.fill()
    ctx.rectangle(x - w / 2 + 10 * k, top_y - 27 * k, w - 20 * k, 2 * k)
    ctx.set_source_rgba(1, 1, 1, 0.22)
    ctx.fill()
    # tiny display between the feet
    P.rrect(ctx, x - 26 * k, top_y - 25 * k, 52 * k, 18 * k, 4 * k)
    P.src(ctx, P.rgb('#08161b'))
    ctx.fill()
    lcd_text(ctx, x, top_y - 16 * k, num, 13 * k, 0.9)


def figure_on_scale(ctx, x, floor_y, k, num=SCALE_NUM, **kw):
    lift = 26 * k
    scale_front(ctx, x, floor_y - lift + 4 * k, k, num)
    figure_front(ctx, x, floor_y - lift, k, **kw)


def mannequin_foot(ctx, cx, cy, s, ang=0.0):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(ang)
    ctx.scale(s, s)
    # lower leg rising toward the camera top
    capsule(ctx, (0, -60), (s * 0 + 18, -900), 66, 92)
    # foot (smooth mannequin foot, no toes)
    ctx.new_path()
    ctx.move_to(-52, -70)
    ctx.curve_to(-78, 10, -82, 120, -60, 170)
    ctx.curve_to(-40, 215, 40, 215, 60, 170)
    ctx.curve_to(82, 120, 78, 10, 52, -70)
    ctx.close_path()
    ctx.set_source(skin_grad((-80, 0), (80, 0)))
    ctx.fill()
    # contact shadow on glass
    ctx.restore()


def scale_closeup(ctx, t, num, cx=540, cy=1380, dim=0.3, feet=True):
    """Top-front view of the scale on the gym floor, feet on it, display in front."""
    paint_bg(ctx, dim=dim)
    w, h = 880, 980
    P.soft_shadow(ctx, cx + 10, cy + h / 2 - 10, w * 0.55, 40, 0.7)
    # body / rim
    P.rrect(ctx, cx - w / 2, cy - h / 2, w, h, 90)
    P.src(ctx, P.vgrad(cy - h / 2, cy + h / 2, [(0, P.rgb('#5c646e')), (1, P.rgb('#22262c'))]))
    ctx.fill()
    # glass top
    P.rrect(ctx, cx - w / 2 + 16, cy - h / 2 + 16, w - 32, h - 40, 78)
    P.src(ctx, P.vgrad(cy - h / 2, cy + h / 2, [(0, P.rgb('#1b2027')), (0.6, P.rgb('#11141a')), (1, P.rgb('#0a0c10'))]))
    ctx.fill()
    # glass reflections
    ctx.save()
    P.rrect(ctx, cx - w / 2 + 16, cy - h / 2 + 16, w - 32, h - 40, 78)
    ctx.clip()
    for off, wd, a in ((-180, 90, 0.07), (-40, 36, 0.05)):
        ctx.new_path()
        ctx.move_to(cx + off - 300, cy + h)
        ctx.line_to(cx + off - 300 + wd, cy + h)
        ctx.line_to(cx + off + 300 + wd, cy - h)
        ctx.line_to(cx + off + 300, cy - h)
        ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, a)
        ctx.fill()
    ctx.restore()
    # display (front)
    dy = cy + h / 2 - 230
    P.rrect(ctx, cx - 190, dy - 75, 380, 150, 22)
    P.src(ctx, P.rgb('#061115'))
    ctx.fill()
    P.rrect(ctx, cx - 190, dy - 75, 380, 150, 22)
    ctx.set_line_width(3)
    ctx.set_source_rgba(0.6, 0.9, 1.0, 0.25)
    ctx.stroke()
    lcd_text(ctx, cx, dy, num, 112)
    if feet:
        for s in (-1, 1):
            P.soft_shadow(ctx, cx + s * 160, cy - 20, 100, 160, 0.45)
            mannequin_foot(ctx, cx + s * 160, cy - 130, 1.05, ang=s * 0.06)


def scale_shot(ctx, t, dur, num, z0=1.0, z1=1.08, rot=0.0, cy=1380, dim=0.3, feet=True):
    camera(ctx, lerp(z0, z1, ease(t / dur)), 540 + 10 * t / dur, cy - 40, rot=rot * (1 - t / dur))
    scale_closeup(ctx, t, num, cy=cy, dim=dim, feet=feet)


# ------------------------------------------------------------ SCENE 1 (0-3s) hook: scale not moving?
def scene1(ctx, t):
    if t < 1.4:
        tt = t
        z = lerp(1.04, 1.14, ease(tt / 1.4))
        camera(ctx, z, 540, lerp(1080, 1120, tt / 1.4))
        paint_bg(ctx)
        P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
        P.floor_spot(ctx, 540, FEET_Y - 10)
        figure_on_scale(ctx, 540, FEET_Y, 1.0, f=F0, m=M0, breath=math.sin(tt * 3.2))
    else:
        tt = t - 1.4
        scale_shot(ctx, tt, 1.6, flicker_num(tt, 0.6), 1.0, 1.1, rot=0.02)
    ctx.identity_matrix()
    vignette(ctx)
    if t >= 1.4:
        flash(ctx, 0.6 * math.exp(-(t - 1.4) * 20))
    text_block(ctx, ["SCALE NOT", "MOVING?"], 170, 0.0, t, box_line=1, size=150)


# ------------------------------------------------------------ SCENE 2 (3-7s) same number every week
def scene2(ctx, t):
    if t < 1.3:
        tt = t
        scale_shot(ctx, tt, 1.3, flicker_num(tt, 0.35, 1), 1.06, 1.12, rot=-0.02)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["WEEK 1", SCALE_NUM], 190, 0.05, tt, box_line=1, size=130)
    elif t < 2.6:
        tt = t - 1.3
        scale_shot(ctx, tt, 1.3, flicker_num(tt, 0.35, 2), 1.1, 1.16, rot=0.02)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["WEEK 6", "STILL " + SCALE_NUM], 190, 0.0, tt, box_line=1, size=130)
    else:
        tt = t - 2.6
        z = lerp(1.1, 1.18, ease(tt / 1.4))
        camera(ctx, z, lerp(560, 540, tt / 1.4), 1120)
        paint_bg(ctx)
        P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
        P.floor_spot(ctx, 540, FEET_Y - 10)
        figure_on_scale(ctx, 540, FEET_Y, 1.0, f=0.97, m=0.1, hips=ease(clamp(tt / 0.4)),
                        breath=math.sin(tt * 3.0))
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["IT CAN'T TELL", "FAT FROM MUSCLE"], 190, 0.0, tt, box_line=1, size=124)
    ctx.identity_matrix()
    for cut in (1.3, 2.6):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 3 (7-12s) check the mirror, lifts, waist
def mirror_shot(ctx, tt, dur):
    k = ease(clamp((tt - 0.15) / (dur - 0.4)))
    f = lerp(0.95, 0.72, k)
    m = lerp(0.12, 0.30, k)
    z = lerp(1.04, 1.1, ease(tt / dur))
    camera(ctx, z, 540, 1110)
    paint_bg(ctx, dim=0.55)
    mx0, mx1, my0, my1 = 150, 930, 560, 2000
    # mirror frame
    P.rrect(ctx, mx0 - 26, my0 - 26, mx1 - mx0 + 52, my1 - my0 + 52, 18)
    P.src(ctx, P.hgrad(mx0 - 26, mx1 + 26, [(0, P.rgb('#3a4047')), (0.3, P.rgb('#9aa2ac')), (0.7, P.rgb('#5d656e')), (1, P.rgb('#2a2e33'))]))
    ctx.fill()
    P.rrect(ctx, mx0 - 6, my0 - 6, mx1 - mx0 + 12, my1 - my0 + 12, 8)
    P.src(ctx, P.rgb('#0b0d10'))
    ctx.fill()
    ctx.save()
    ctx.rectangle(mx0, my0, mx1 - mx0, my1 - my0)
    ctx.clip()
    paint_bg(ctx, dim=0.05)
    ctx.set_source_rgba(0.55, 0.75, 0.85, 0.06)
    ctx.paint()
    P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.08)
    P.floor_spot(ctx, 540, FEET_Y - 10)
    P.soft_shadow(ctx, 540, FEET_Y - 8, 170, 26, 0.6)
    figure_front(ctx, 540, FEET_Y, 1.0, f=f, m=m, breath=math.sin(tt * 3.0) * 0.6)
    # light sweep showing the change
    sw = (tt - 0.1) / (dur - 0.2)
    if 0 <= sw <= 1:
        x = lerp(mx0 - 200, mx1 + 200, sw)
        g = cairo.LinearGradient(x - 140, 0, x + 140, 0)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 0.85, 1, 0.8, 0.12)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        P.src(ctx, g)
        ctx.paint()
    # glass streaks
    for off, wd, a in ((-260, 110, 0.06), (-90, 40, 0.05), (300, 70, 0.04)):
        ctx.new_path()
        ctx.move_to(540 + off - 500, 2000)
        ctx.line_to(540 + off - 500 + wd, 2000)
        ctx.line_to(540 + off + 300 + wd, 500)
        ctx.line_to(540 + off + 300, 500)
        ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, a)
        ctx.fill()
    ctx.restore()


def tape_measure(ctx, f, m, phase):
    """Soft tailor's tape around the waist, figure units (feet at y=0)."""
    d = front_dims(f, m)
    ww = d['w'] + 3 * f + 3
    y = -542
    th = 20
    ctx.save()
    # band (front of the waist, slight downward curve)
    ctx.new_path()
    ctx.move_to(-ww, y - th / 2)
    ctx.curve_to(-ww * 0.5, y - th / 2 + 12, ww * 0.5, y - th / 2 + 12, ww, y - th / 2)
    ctx.line_to(ww, y + th / 2)
    ctx.curve_to(ww * 0.5, y + th / 2 + 12, -ww * 0.5, y + th / 2 + 12, -ww, y + th / 2)
    ctx.close_path()
    P.src(ctx, P.vgrad(y - th / 2, y + th / 2 + 12, [(0, P.rgb('#f1e6b0')), (0.5, P.rgb('#e6d58c')), (1, P.rgb('#b9a660'))]))
    ctx.fill()
    # tick marks scroll as the tape is pulled tighter
    ctx.set_line_width(1.6)
    ctx.set_source_rgba(0.12, 0.12, 0.12, 0.85)
    step = 7.0
    x = -ww + (phase % step)
    i = int(phase // step)
    while x < ww:
        u = x / ww
        yc = y - th / 2 + 12 * (1 - u * u) * 0.75
        ln = 9 if (i % 5 == 0) else 5
        ctx.new_path()
        ctx.move_to(x, yc)
        ctx.line_to(x, yc + ln)
        ctx.stroke()
        x += step
        i -= 1
    # free end hanging down from the hands
    ctx.new_path()
    ctx.move_to(-6, y + th / 2 + 6)
    ctx.curve_to(-14, y + 60, 12, y + 120, 2, y + 175)
    ctx.line_to(22, y + 175)
    ctx.curve_to(32, y + 120, 6, y + 60, 14, y + th / 2 + 6)
    ctx.close_path()
    P.src(ctx, P.hgrad(-10, 30, [(0, P.rgb('#c9b870')), (0.5, P.rgb('#efe2a6')), (1, P.rgb('#b9a660'))]))
    ctx.fill()
    # hands pinching the tape at the front
    for s, hx in ((1, 24), (-1, -20)):
        ellipse(ctx, hx, y + 2, 24, 17, s * 0.4)
        ctx.set_source(skin_grad((hx - 20, y - 18), (hx + 20, y + 20)))
        ctx.fill()
    ctx.restore()


def waist_shot(ctx, tt, dur):
    k = ease(clamp((tt - 0.1) / (dur - 0.3)))
    f = lerp(0.9, 0.68, k)
    m = lerp(0.18, 0.32, k)
    z = 1.8 * (1 + 0.04 * tt / dur)
    camera(ctx, z, 540 + 6 * tt / dur, 925)
    paint_bg(ctx)
    P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
    hands = ((24, -545), (-20, -545))
    figure_front(ctx, 540, FEET_Y, 1.0, f=f, m=m, arm_r=hands[0], arm_l=hands[1], breath=0.0)
    ctx.save()
    ctx.translate(540, FEET_Y)
    tape_measure(ctx, f, m, phase=(0.9 - f) * 260)
    ctx.restore()


S3_SEG = 5.0 / 3


def scene3(ctx, t):
    i = min(2, int(t / S3_SEG))
    tt = t - i * S3_SEG
    if i == 0:
        mirror_shot(ctx, tt, S3_SEG)
        lines = ["MIRROR", "MORE DEFINITION"]
    elif i == 1:
        punch = 1 + 0.08 * math.exp(-tt * 9)
        camera(ctx, 1.0 * punch * (1 + 0.04 * tt / S3_SEG), 600 + 20 * tt / S3_SEG, 1060, rot=-0.03)
        paint_bg(ctx, dim=0.2)
        P.light_cone(ctx, 700, 200, 1800, 140, 600, 0.10)
        P.floor_spot(ctx, 700, 1500, 520, 120)
        barbell_closeup(ctx, tt, cy=1180)
        lines = ["LIFTS", "GOING UP"]
    else:
        waist_shot(ctx, tt, S3_SEG)
        lines = ["WAIST", "SHRINKING"]
    ctx.identity_matrix()
    vignette(ctx)
    flash(ctx, 0.7 * math.exp(-tt * 22))
    text_block(ctx, lines, 190, 0.0, tt, box_line=1, size=128)


# ------------------------------------------------------------ SCENE 4 (12-16s) same weight, better body
def scene4(ctx, t):
    if t < 1.4:
        tt = t
        lift_shot(ctx, 'squat', tt, 1.4, 0.7, 0.32, pr=96, rot=-0.015, zmul=0.9, cyoff=210.0)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["SAME WEIGHT", "LESS FAT"], 190, 0.0, tt, box_line=1, size=124)
    elif t < 2.7:
        tt = t - 1.4
        lift_shot(ctx, 'row', tt, 1.3, 0.68, 0.34, pr=96, rot=0.02, period=1.0)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["SAME WEIGHT", "MORE MUSCLE"], 190, 0.0, tt, box_line=1, size=124)
    else:
        tt = t - 2.7
        z = lerp(1.08, 1.16, ease(tt / 1.3))
        camera(ctx, z, lerp(530, 545, tt / 1.3), 1110)
        paint_bg(ctx)
        P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.08)
        P.floor_spot(ctx, 540, FEET_Y - 10)
        figure_on_scale(ctx, 540, FEET_Y, 1.0, f=0.64, m=0.36, hips=1.0, breath=math.sin(tt * 2.8) * 0.6)
        ctx.identity_matrix()
        vignette(ctx)
        text_block(ctx, ["THAT'S A", "RECOMP"], 190, 0.0, tt, box_line=1, size=140)
    ctx.identity_matrix()
    for cut in (1.4, 2.7):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 5 (16-20s) payoff
def scene5(ctx, t):
    k = ease((t - 0.15) / 2.75)
    f = lerp(0.64, F1, k)
    m = lerp(0.36, M1, k)
    z = lerp(1.2, 1.06, ease(t / 3.2))
    camera(ctx, z, lerp(600, 580, t / 4), lerp(1090, 1110, ease(t / 3.2)))
    paint_bg(ctx)
    P.light_cone(ctx, 500, 200, 1800, 130, 560, 0.09)
    P.floor_spot(ctx, 500, FEET_Y - 10, 420, 95)
    # he stepped off: the scale sits on the floor beside him
    scale_front(ctx, 860, FEET_Y - 6, 0.9)
    P.soft_shadow(ctx, 500, FEET_Y - 8, 180, 26, 0.6)
    figure_front(ctx, 500, FEET_Y, 1.0, f=f, m=m, hips=0.0, breath=math.sin(t * 2.6) * 0.6)
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
    text_block(ctx, ["NOT JUST", "THE SCALE"], 170, 2.3, t, box_line=1, size=150)


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
