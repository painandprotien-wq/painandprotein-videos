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


# ------------------------------------------------------------ SCENE 1 (0-3s) hook: same weight forever
def scene1(ctx, t):
    # slow, bored reps with the same small plates (cobweb on them)
    lift_shot(ctx, 'bench', t, 3.0, F0, M0, pr=78, web=0.55, punch_on=False, period=1.5)
    ctx.identity_matrix()
    vignette(ctx)
    text_block(ctx, ["SAME WEIGHT", "FOR MONTHS?"], 170, 0.0, t, box_line=1, size=140)


# ------------------------------------------------------------ SCENE 2 (3-7s) weeks pass, nothing changes
def wall_calendar(ctx, cx, cy, w, h, week, flip):
    """Wall calendar showing WEEK n. flip 0..1 = previous page tearing up and away."""
    P.soft_shadow(ctx, cx + 16, cy + 24, w * 0.62, h * 0.6, 0.5)

    def page(label, sy=1.0, a=1.0):
        top = cy - h / 2
        ctx.save()
        ctx.translate(cx, top)
        ctx.scale(1, sy)
        P.rrect(ctx, -w / 2, 0, w, h, 18)
        P.src(ctx, P.vgrad(0, h, [(0, P.rgb('#f6f6f3')), (1, P.rgb('#d8dbde'))]))
        ctx.fill()
        P.rrect(ctx, -w / 2, 0, w, h * 0.24, 18)
        P.src(ctx, LIME)
        ctx.fill()
        ctx.rectangle(-w / 2, h * 0.16, w, h * 0.08)
        P.src(ctx, LIME)
        ctx.fill()
        ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(h * 0.13)
        e = ctx.text_extents('WEEK')
        ctx.move_to(-e.width / 2 - e.x_bearing, h * 0.12 - e.height / 2 - e.y_bearing)
        ctx.set_source_rgb(0.05, 0.06, 0.07)
        ctx.show_text('WEEK')
        ctx.set_font_size(h * 0.48)
        e = ctx.text_extents(label)
        ctx.move_to(-e.width / 2 - e.x_bearing, h * 0.62 - e.height / 2 - e.y_bearing)
        ctx.set_source_rgb(0.08, 0.09, 0.1)
        ctx.show_text(label)
        if sy < 1.0:
            ctx.set_source_rgba(0, 0, 0, 0.25 * (1 - sy))
            P.rrect(ctx, -w / 2, 0, w, h, 18)
            ctx.fill()
        ctx.restore()
    page(str(week))
    if flip > 0:
        page(str(week - 1), sy=max(0.02, 1 - flip))
    # rings
    for k in (-1, 0, 1):
        x = cx + k * w * 0.3
        P.rrect(ctx, x - 9, cy - h / 2 - 34, 18, 60, 9)
        P.src(ctx, P.rgb('#8a9099'))
        ctx.fill()


def scene2(ctx, t):
    if t < 1.3:
        # calendar flipping: weeks fly by
        tt = t
        z = lerp(1.0, 1.1, ease(tt / 1.3))
        camera(ctx, z, 540, 1000, rot=lerp(0.025, 0.0, tt / 1.3))
        paint_bg(ctx, dim=0.25)
        rate = 8.0
        pos = tt * rate
        week = min(12, 2 + int(pos))
        flip = 0.0 if week >= 12 else (pos % 1.0)
        wall_calendar(ctx, 540, 1040, 700, 760, week, ease(flip))
    elif t < 2.6:
        # squat, same tiny plates, same cobweb
        tt = t - 1.3
        lift_shot(ctx, 'squat', tt, 1.3, F0, M0, pr=78, web=0.55, rot=-0.015, period=1.3)
    else:
        # same body: standing, arms down, small shrug
        tt = t - 2.6
        z = lerp(1.12, 1.22, ease(tt / 1.4))
        camera(ctx, z, 540, lerp(1150, 1180, tt / 1.4))
        paint_bg(ctx)
        P.light_cone(ctx, 540, 200, 1800, 120, 520, 0.07)
        P.floor_spot(ctx, 540, FEET_Y - 10)
        P.soft_shadow(ctx, 540, FEET_Y - 8, 170, 26, 0.6)
        shrug = math.sin(clamp((tt - 0.3) / 0.6) * math.pi)
        figure_front(ctx, 540, FEET_Y, 1.0, f=F0, m=M0, hips=0.0, breath=math.sin(tt * 3) * 0.5 + shrug * 4.0)
    ctx.identity_matrix()
    vignette(ctx)
    for cut in (1.3, 2.6):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 3 (7-12s) add a little every week
S3 = [
    # name, plate r, f, m, line1, line2
    ('bench', 80, 1.00, 0.08, "WEEK 1", "LOG IT"),
    ('squat', 82, 0.96, 0.11, "WEEK 2", "+1 REP"),
    ('row', 85, 0.92, 0.14, "WEEK 3", "+1 REP"),
    ('bench', 94, 0.88, 0.17, "WEEK 4", "+ A LITTLE WEIGHT"),
]


def scene3(ctx, t):
    seg = 5.0 / 4
    i = min(3, int(t / seg))
    tt = t - i * seg
    name, pr, f, m, l1, l2 = S3[i]
    # squat stands tallest: frame it lower and wider so the text never covers the head
    sq = name == 'squat'
    lift_shot(ctx, name, tt, seg, f, m, pr=pr, rot=(-0.02, 0.02, -0.015, 0.015)[i],
              zmul=0.9 if sq else 1.0, cyoff=210.0 if sq else 0.0)
    ctx.identity_matrix()
    vignette(ctx)
    flash(ctx, 0.75 * math.exp(-tt * 22))
    text_block(ctx, [l1, l2], 190, 0.0, tt, box_line=1, size=118)


# ------------------------------------------------------------ SCENE 4 (12-16s) small jumps, write it down
def bar_plate(ctx, x, cy, w, h, shade=1.0):
    P.rrect(ctx, x - w / 2, cy - h / 2, w, h, min(14, w * 0.35))
    P.src(ctx, P.hgrad(x - w / 2, x + w / 2, [(0, tuple(v * shade for v in P.rgb('#0c0d0f'))),
                                             (0.35, tuple(v * shade for v in P.rgb('#3a3f46'))),
                                             (1, tuple(v * shade for v in P.rgb('#08090b')))]))
    ctx.fill()
    ctx.rectangle(x - w / 2 + 4, cy - h / 2 + 12, 3, h - 24)
    ctx.set_source_rgba(1, 1, 1, 0.08)
    ctx.fill()


def barbell_closeup(ctx, t):
    """Close-up of the bar sleeve: a small plate slides on next to the others."""
    cy = 1020
    # shaft
    ctx.rectangle(-300, cy - 16, 720, 32)
    P.src(ctx, P.vgrad(cy - 16, cy + 16, [(0, P.rgb('#9aa1aa')), (0.4, P.rgb('#d5d9de')), (1, P.rgb('#4b5058'))]))
    ctx.fill()
    # inner collar
    P.rrect(ctx, 400, cy - 52, 46, 104, 10)
    P.src(ctx, P.vgrad(cy - 52, cy + 52, [(0, P.rgb('#7d848d')), (0.4, P.rgb('#c9ced4')), (1, P.rgb('#3c4047'))]))
    ctx.fill()
    # sleeve
    ctx.rectangle(446, cy - 30, 900, 60)
    P.src(ctx, P.vgrad(cy - 30, cy + 30, [(0, P.rgb('#a3aab3')), (0.35, P.rgb('#e4e7ea')), (1, P.rgb('#50555d'))]))
    ctx.fill()
    # plates already on
    bar_plate(ctx, 490, cy, 72, 640)
    bar_plate(ctx, 566, cy, 64, 640, 0.92)
    # new small plate slides on
    k = ease(clamp((t - 0.15) / 0.55))
    x = lerp(1250, 624, k)
    bar_plate(ctx, x, cy, 40, 330, 1.05)
    # spring collar follows
    kc = ease(clamp((t - 0.75) / 0.35))
    cx2 = lerp(1300, 668, kc)
    P.rrect(ctx, cx2 - 18, cy - 44, 36, 88, 8)
    P.src(ctx, P.vgrad(cy - 44, cy + 44, [(0, P.rgb('#6b7179')), (0.4, P.rgb('#b8bec5')), (1, P.rgb('#2f3237'))]))
    ctx.fill()
    return k


def notebook(ctx, t):
    """Training log on a bench: scribbled rows, each gets a +1 and a check mark."""
    ctx.save()
    ctx.translate(540, 1080)
    ctx.rotate(-0.06)
    P.soft_shadow(ctx, 20, 30, 430, 470, 0.55)
    P.rrect(ctx, -380, -470, 760, 940, 18)
    P.src(ctx, P.vgrad(-470, 470, [(0, P.rgb('#f5f2ea')), (1, P.rgb('#dcd7cc'))]))
    ctx.fill()
    # spiral
    for k in range(9):
        ctx.arc(-340, -400 + k * 100, 14, 0, 2 * math.pi)
        P.src(ctx, P.rgb('#7d848d'))
        ctx.fill()
    # ruled lines
    ctx.set_line_width(2)
    for k in range(9):
        y = -340 + k * 90
        ctx.new_path()
        ctx.move_to(-300, y)
        ctx.line_to(350, y)
        ctx.set_source_rgba(0.45, 0.6, 0.8, 0.35)
        ctx.stroke()
    rows = 6
    per = 0.17
    ctx.select_font_face(FONT, cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_BOLD)
    for r in range(rows):
        y = -360 + r * 90 + 70
        k = clamp((t - r * per) / per)
        if k <= 0:
            continue
        # scribble "words" (not readable)
        ctx.set_line_width(5)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.new_path()
        x0, x1 = -280, -280 + 360 * k
        ctx.move_to(x0, y - 18)
        n = int(26 * k) + 1
        for j in range(1, n + 1):
            xx = lerp(x0, x1, j / n)
            ctx.line_to(xx, y - 18 - 14 * math.sin(j * 1.9 + r) * (1 if j % 5 else 0.2))
        ctx.set_source_rgba(0.16, 0.18, 0.22, 0.85)
        ctx.stroke()
        if k >= 1:
            ctx.set_font_size(58)
            ctx.move_to(130, y - 4)
            ctx.set_source_rgba(0.16, 0.18, 0.22, 0.9)
            ctx.show_text('+1')
            # check mark
            ctx.new_path()
            ctx.move_to(250, y - 30)
            ctx.line_to(272, y - 6)
            ctx.line_to(318, y - 58)
            ctx.set_line_width(12)
            P.src(ctx, P.rgb('#5f8f14'))
            ctx.stroke()
    ctx.restore()
    # pencil tip following the current row
    r = min(rows - 1, int(t / per))
    k = clamp((t - r * per) / per)
    px, py = 540 - 280 + 360 * k, 1080 - 360 + r * 90 + 50
    ctx.save()
    ctx.translate(px, py)
    ctx.rotate(-0.75)
    ctx.rectangle(0, -14, 360, 28)
    P.src(ctx, P.vgrad(-14, 14, [(0, P.rgb('#e7c34a')), (1, P.rgb('#a8841c'))]))
    ctx.fill()
    ctx.new_path()
    ctx.move_to(0, -14)
    ctx.line_to(-46, 0)
    ctx.line_to(0, 14)
    ctx.close_path()
    P.src(ctx, P.rgb('#e5c9a0'))
    ctx.fill()
    ctx.new_path()
    ctx.move_to(-30, -5)
    ctx.line_to(-46, 0)
    ctx.line_to(-30, 5)
    ctx.close_path()
    P.src(ctx, P.rgb('#2a2c30'))
    ctx.fill()
    ctx.restore()


def scene4(ctx, t):
    if t < 1.3:
        tt = t
        z = lerp(1.45, 1.6, ease(tt / 1.3))
        camera(ctx, z, lerp(600, 640, tt / 1.3), 1020, rot=lerp(-0.02, 0.0, tt / 1.3))
        paint_bg(ctx, dim=0.35)
        P.light_cone(ctx, 600, 200, 1800, 120, 520, 0.08)
        k = barbell_closeup(ctx, tt)
        ctx.identity_matrix()
        vignette(ctx)
        # tiny clink flash when the plate lands
        flash(ctx, 0.35 * math.exp(-max(0, tt - 0.7) * 25) if tt >= 0.7 else 0.0)
    elif t < 2.7:
        tt = t - 1.3
        z = lerp(1.2, 1.32, ease(tt / 1.4))
        camera(ctx, z, 560, lerp(1000, 1030, tt / 1.4), rot=lerp(0.02, 0.0, tt / 1.4))
        paint_bg(ctx, dim=0.3)
        P.table(ctx, -400, 1480, 1700, depth=900, front=400)
        notebook(ctx, tt)
        ctx.identity_matrix()
        vignette(ctx)
    else:
        # clean, controlled squat with slightly bigger plates (form first)
        tt = t - 2.7
        lift_shot(ctx, 'squat', tt, 1.3, 0.82, 0.22, pr=96, rot=0.015, period=1.25)
        ctx.identity_matrix()
        vignette(ctx)
    ctx.identity_matrix()
    for cut in (1.3, 2.7):
        if t >= cut:
            flash(ctx, 0.6 * math.exp(-(t - cut) * 20))


# ------------------------------------------------------------ SCENE 5 (16-20s) payoff
def scene5(ctx, t):
    k = ease((t - 0.15) / 2.75)
    f = lerp(0.82, F1, k)
    m = lerp(0.22, M1, k)
    hips = 0.0
    z = lerp(1.22, 1.08, ease(t / 3.2))
    camera(ctx, z, lerp(560, 540, t / 4), lerp(1300, 1110, ease(t / 3.2)))
    paint_bg(ctx)
    P.light_cone(ctx, 540, 200, 1800, 130, 560, 0.09)
    P.floor_spot(ctx, 540, FEET_Y - 10, 420, 95)
    P.soft_shadow(ctx, 540, FEET_Y - 8, 180, 26, 0.6)
    figure_front(ctx, 540, FEET_Y, 1.0, f=f, m=m, hips=hips, breath=math.sin(t * 2.6) * 0.6)
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
    text_block(ctx, ["A LITTLE MORE", "EVERY WEEK"], 170, 2.3, t, box_line=1, size=140)


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
