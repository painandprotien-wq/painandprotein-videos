import math
import random
import cairo
from figure import ellipse, capsule, lerp, clamp


def src(ctx, x):
    if isinstance(x, cairo.Pattern):
        ctx.set_source(x)
    elif len(x) == 4:
        ctx.set_source_rgba(*x)
    else:
        ctx.set_source_rgb(*x)


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def vgrad(y0, y1, stops):
    g = cairo.LinearGradient(0, y0, 0, y1)
    for o, c in stops:
        if len(c) == 4:
            g.add_color_stop_rgba(o, *c)
        else:
            g.add_color_stop_rgb(o, *c)
    return g


def hgrad(x0, x1, stops):
    g = cairo.LinearGradient(x0, 0, x1, 0)
    for o, c in stops:
        if len(c) == 4:
            g.add_color_stop_rgba(o, *c)
        else:
            g.add_color_stop_rgb(o, *c)
    return g


def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def soft_shadow(ctx, cx, cy, rx, ry, a=0.45):
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, 1)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(rx, ry)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
    g.add_color_stop_rgba(0, 0, 0, 0, a)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    src(ctx, g)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


# ------------------------------------------------------------------ GYM

def draw_gym(ctx, W, H, ox, oy):
    """Draw gym into a surface covering world rect starting at (ox, oy)."""
    ctx.save()
    ctx.translate(-ox, -oy)
    x0, y0, x1, y1 = ox, oy, ox + W, oy + H
    horizon = 1330
    # back wall
    ctx.rectangle(x0, y0, W, horizon - y0)
    src(ctx, vgrad(y0, horizon, [(0, rgb('#0d1116')), (0.45, rgb('#1b222b')), (1, rgb('#262d36'))]))
    ctx.fill()
    # wall slats
    for i, x in enumerate(range(int(x0), int(x1), 70)):
        ctx.rectangle(x, 560, 3, horizon - 560)
        ctx.set_source_rgba(0, 0, 0, 0.25)
        ctx.fill()
    # upper wall darker band + LED strips
    ctx.rectangle(x0, y0, W, 560 - y0)
    src(ctx, vgrad(y0, 560, [(0, rgb('#07090c')), (1, rgb('#12171d'))]))
    ctx.fill()
    for ly, a in ((560, 1.0), (300, 0.6)):
        g = vgrad(ly - 40, ly + 40, [(0, (0.55, 0.85, 1.0, 0)), (0.5, (0.75, 0.92, 1.0, 0.55 * a)), (1, (0.55, 0.85, 1.0, 0))])
        ctx.rectangle(x0, ly - 40, W, 80)
        src(ctx, g)
        ctx.fill()
        ctx.rectangle(x0, ly - 3, W, 6)
        ctx.set_source_rgba(0.9, 0.97, 1.0, 0.95 * a)
        ctx.fill()
    # ceiling spot glows
    for sx in (140, 540, 940, -260, 1340):
        g = cairo.RadialGradient(sx, 120, 0, sx, 120, 260)
        g.add_color_stop_rgba(0, 1, 0.95, 0.85, 0.35)
        g.add_color_stop_rgba(1, 1, 0.95, 0.85, 0)
        src(ctx, g)
        ctx.rectangle(sx - 300, y0, 600, 500)
        ctx.fill()
    # left: dumbbell rack
    rx0, rx1 = -300, 300
    for row, ry in enumerate((1090, 1200)):
        ctx.rectangle(rx0, ry + 38, rx1 - rx0, 14)
        src(ctx, rgb('#0a0c0f'))
        ctx.fill()
        for k, dx in enumerate(range(rx0 + 20, rx1 - 20, 62)):
            sz = 20 + (k % 4) * 3 + row * 4
            for side in (0, 1):
                cx = dx + side * 40
                rrect(ctx, cx - 9, ry + 30 - sz * 2, 18, sz * 2, 5)
                src(ctx, hgrad(cx - 9, cx + 9, [(0, rgb('#15181c')), (0.4, rgb('#3a4048')), (1, rgb('#0e1013'))]))
                ctx.fill()
            ctx.rectangle(dx + 9, ry + 30 - sz - 3, 22, 6)
            src(ctx, rgb('#5a616b'))
            ctx.fill()
    ctx.rectangle(rx0 + 10, 1100, 12, horizon - 1100)
    ctx.rectangle(rx1 - 22, 1100, 12, horizon - 1100)
    src(ctx, rgb('#08090b'))
    ctx.fill()
    # right: power rack
    for px in (820, 1090):
        ctx.rectangle(px, 620, 26, horizon - 620 + 20)
        src(ctx, hgrad(px, px + 26, [(0, rgb('#101216')), (0.4, rgb('#2c323a')), (1, rgb('#0b0c0e'))]))
        ctx.fill()
        for hy in range(660, horizon, 40):
            ctx.arc(px + 13, hy, 3, 0, 2 * math.pi)
            ctx.set_source_rgba(0, 0, 0, 0.8)
            ctx.fill()
    ctx.rectangle(820, 612, 296, 22)
    src(ctx, rgb('#15181c'))
    ctx.fill()
    # bar in rack
    ctx.rectangle(760, 900, 420, 10)
    src(ctx, rgb('#6d747e'))
    ctx.fill()
    for px in (790, 1130):
        rrect(ctx, px - 14, 830, 28, 150, 6)
        src(ctx, hgrad(px - 14, px + 14, [(0, rgb('#0c0d10')), (0.5, rgb('#262b31')), (1, rgb('#08090b'))]))
        ctx.fill()
    # plate tree far right
    for i, py in enumerate((1180, 1240, 1300)):
        ellipse(ctx, 1300, py, 70 - i * 8, 70 - i * 8)
        src(ctx, rgb('#0e1013'))
        ctx.fill()
    # floor
    ctx.rectangle(x0, horizon, W, y1 - horizon)
    src(ctx, vgrad(horizon, y1, [(0, rgb('#1d2228')), (0.5, rgb('#121519')), (1, rgb('#0a0c0e'))]))
    ctx.fill()
    ctx.rectangle(x0, horizon - 4, W, 8)
    ctx.set_source_rgba(0, 0, 0, 0.6)
    ctx.fill()
    # floor perspective seams
    vp = (540, 1000)
    ctx.set_line_width(2)
    for x in range(-2400, 3600, 180):
        ctx.new_path()
        t0 = (horizon - vp[1]) / (y1 - vp[1])
        ctx.move_to(lerp(vp[0], x, t0), horizon)
        ctx.line_to(x, y1)
        ctx.set_source_rgba(0, 0, 0, 0.35)
        ctx.stroke()
    for k in range(1, 12):
        yy = horizon + (y1 - horizon) * (k / 12) ** 1.6
        ctx.rectangle(x0, yy, W, 2)
        ctx.set_source_rgba(0, 0, 0, 0.25)
        ctx.fill()
    # floor reflection of LED
    g = vgrad(horizon, horizon + 260, [(0, (0.6, 0.85, 1, 0.10)), (1, (0.6, 0.85, 1, 0))])
    ctx.rectangle(x0, horizon, W, 260)
    src(ctx, g)
    ctx.fill()
    # speckle
    rnd = random.Random(3)
    for _ in range(5000):
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(horizon, y1)
        ctx.rectangle(x, y, 2, 2)
        c = rnd.uniform(0.15, 0.35)
        ctx.set_source_rgba(c, c, c + 0.02, 0.35)
        ctx.fill()
    ctx.restore()


def floor_spot(ctx, cx, cy, rx=380, ry=90):
    g = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(rx, ry)
    g.add_color_stop_rgba(0, 1, 0.97, 0.92, 0.18)
    g.add_color_stop_rgba(1, 1, 0.97, 0.92, 0)
    src(ctx, g)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def light_cone(ctx, cx, top, bottom, w_top, w_bot, a=0.10):
    ctx.new_path()
    ctx.move_to(cx - w_top, top)
    ctx.line_to(cx + w_top, top)
    ctx.line_to(cx + w_bot, bottom)
    ctx.line_to(cx - w_bot, bottom)
    ctx.close_path()
    src(ctx, vgrad(top, bottom, [(0, (1, 0.97, 0.9, a)), (1, (1, 0.97, 0.9, 0))]))
    ctx.fill()


# ------------------------------------------------------------------ FURNITURE

def table(ctx, x0, x1, y, depth=70, front=260):
    # top surface
    ctx.new_path()
    ctx.move_to(x0 + 30, y - depth)
    ctx.line_to(x1 - 30, y - depth)
    ctx.line_to(x1, y)
    ctx.line_to(x0, y)
    ctx.close_path()
    src(ctx, vgrad(y - depth, y, [(0, rgb('#3a2a1f')), (1, rgb('#5a4130'))]))
    ctx.fill()
    # grain
    rnd = random.Random(7)
    ctx.set_line_width(1.5)
    for i in range(18):
        yy = y - depth + rnd.uniform(4, depth - 4)
        ctx.new_path()
        ctx.move_to(x0 + 20, yy)
        ctx.curve_to(x0 + (x1 - x0) * 0.3, yy + rnd.uniform(-4, 4), x0 + (x1 - x0) * 0.7, yy + rnd.uniform(-4, 4), x1 - 20, yy)
        ctx.set_source_rgba(0.12, 0.08, 0.05, 0.25)
        ctx.stroke()
    # front edge
    ctx.rectangle(x0, y, x1 - x0, 26)
    src(ctx, vgrad(y, y + 26, [(0, rgb('#6b4d38')), (1, rgb('#2a1d14'))]))
    ctx.fill()
    ctx.rectangle(x0, y + 26, x1 - x0, front)
    src(ctx, vgrad(y + 26, y + 26 + front, [(0, rgb('#1a120c')), (1, rgb('#0b0806'))]))
    ctx.fill()


def gym_bench(ctx, x0, x1, y, h=40):
    rrect(ctx, x0, y - h, x1 - x0, h, 14)
    src(ctx, vgrad(y - h, y, [(0, rgb('#2d3238')), (0.3, rgb('#1a1d21')), (1, rgb('#0c0d0f'))]))
    ctx.fill()


def plate(ctx, cx, cy, rx, ry=None):
    ry = ry or rx * 0.42
    soft_shadow(ctx, cx + 8, cy + ry * 0.35, rx * 1.05, ry * 0.9, 0.5)
    ellipse(ctx, cx, cy, rx, ry)
    src(ctx, vgrad(cy - ry, cy + ry, [(0, rgb('#f4f4f2')), (1, rgb('#c9ccd0'))]))
    ctx.fill()
    ellipse(ctx, cx, cy + ry * 0.04, rx * 0.72, ry * 0.68)
    src(ctx, vgrad(cy - ry, cy + ry, [(0, rgb('#dcdedf')), (1, rgb('#f7f7f5'))]))
    ctx.fill()


def bowl(ctx, cx, cy, r, color=rgb('#5d6b78'), fill=None):
    ry = r * 0.38
    soft_shadow(ctx, cx + 8, cy + r * 0.62, r * 1.05, ry * 0.8, 0.5)
    ctx.new_path()
    ctx.move_to(cx - r, cy)
    ctx.curve_to(cx - r, cy + r * 0.7, cx + r, cy + r * 0.7, cx + r, cy)
    ctx.close_path()
    src(ctx, hgrad(cx - r, cx + r, [(0, tuple(c * 0.6 for c in color)), (0.35, tuple(min(1, c * 1.3) for c in color)), (1, tuple(c * 0.5 for c in color))]))
    ctx.fill()
    ellipse(ctx, cx, cy, r, ry)
    src(ctx, tuple(c * 0.8 for c in color))
    ctx.fill()
    if fill:
        ellipse(ctx, cx, cy + 3, r * 0.9, ry * 0.82)
        src(ctx, fill)
        ctx.fill()


# ------------------------------------------------------------------ JUNK FOOD

def burger(ctx, cx, by, s=1.0, layers=4):
    w = 150 * s
    soft_shadow(ctx, cx + 10, by + 6, w * 1.1, 26 * s, 0.55)
    y = by
    # bottom bun
    rrect(ctx, cx - w, y - 40 * s, 2 * w, 40 * s, 18 * s)
    src(ctx, vgrad(y - 40 * s, y, [(0, rgb('#d99a4e')), (1, rgb('#8a5424'))]))
    ctx.fill()
    y -= 36 * s
    for i in range(layers):
        # lettuce
        ctx.new_path()
        ctx.move_to(cx - w * 1.05, y)
        for k in range(13):
            xx = cx - w * 1.05 + k * (2.1 * w / 12)
            ctx.line_to(xx, y + (10 if k % 2 else -4) * s)
        ctx.line_to(cx + w * 1.05, y - 12 * s)
        ctx.line_to(cx - w * 1.05, y - 12 * s)
        ctx.close_path()
        src(ctx, rgb('#5fa33a'))
        ctx.fill()
        y -= 10 * s
        # patty
        rrect(ctx, cx - w * 1.02, y - 42 * s, 2.04 * w, 42 * s, 16 * s)
        src(ctx, vgrad(y - 42 * s, y, [(0, rgb('#6b3b22')), (0.5, rgb('#4a2616')), (1, rgb('#2e170d'))]))
        ctx.fill()
        rnd = random.Random(i)
        for _ in range(26):
            ctx.arc(cx + rnd.uniform(-w, w), y - rnd.uniform(6, 36) * s, rnd.uniform(2, 5) * s, 0, 2 * math.pi)
            ctx.set_source_rgba(0.12, 0.05, 0.02, 0.5)
            ctx.fill()
        y -= 38 * s
        # cheese with drips
        ctx.new_path()
        ctx.move_to(cx - w * 1.08, y + 4 * s)
        ctx.line_to(cx - w * 0.8, y + 30 * s)
        ctx.line_to(cx - w * 0.6, y + 6 * s)
        ctx.line_to(cx + w * 0.3, y + 6 * s)
        ctx.line_to(cx + w * 0.5, y + 34 * s)
        ctx.line_to(cx + w * 0.7, y + 6 * s)
        ctx.line_to(cx + w * 1.08, y + 4 * s)
        ctx.line_to(cx + w * 1.05, y - 8 * s)
        ctx.line_to(cx - w * 1.05, y - 8 * s)
        ctx.close_path()
        src(ctx, vgrad(y - 8 * s, y + 34 * s, [(0, rgb('#ffd24a')), (1, rgb('#f0a818'))]))
        ctx.fill()
        y -= 8 * s
    # tomato
    rrect(ctx, cx - w * 0.95, y - 14 * s, 1.9 * w, 14 * s, 7 * s)
    src(ctx, rgb('#d63b2c'))
    ctx.fill()
    y -= 12 * s
    # top bun
    ctx.new_path()
    ctx.move_to(cx - w * 1.04, y)
    ctx.curve_to(cx - w * 1.04, y - 130 * s, cx + w * 1.04, y - 130 * s, cx + w * 1.04, y)
    ctx.close_path()
    g = cairo.RadialGradient(cx - w * 0.3, y - 80 * s, 5, cx, y - 30 * s, w * 1.3)
    g.add_color_stop_rgb(0, *rgb('#f2b96a'))
    g.add_color_stop_rgb(0.6, *rgb('#c77a31'))
    g.add_color_stop_rgb(1, *rgb('#7d4518'))
    src(ctx, g)
    ctx.fill()
    rnd = random.Random(9)
    for _ in range(22):
        a = rnd.uniform(-0.85, 0.85)
        sx = cx + math.sin(a) * w * 0.85
        sy = y - math.cos(a) * 85 * s + rnd.uniform(0, 20) * s
        ellipse(ctx, sx, sy, 5 * s, 2.5 * s, rnd.uniform(0, 3))
        src(ctx, rgb('#fbf0d4'))
        ctx.fill()
    return y - 98 * s


def fries(ctx, cx, by, s=1.0, n=38):
    rnd = random.Random(4)
    w = 110 * s
    soft_shadow(ctx, cx + 8, by + 4, w * 1.2, 22 * s, 0.55)
    for i in range(n):
        x = cx + rnd.uniform(-w * 0.8, w * 0.8)
        ang = rnd.uniform(-0.35, 0.35)
        L = rnd.uniform(150, 230) * s
        top = by - 200 * s - rnd.uniform(0, 70) * s
        ctx.save()
        ctx.translate(x, top)
        ctx.rotate(ang)
        rrect(ctx, -9 * s, 0, 18 * s, L, 4 * s)
        src(ctx, hgrad(-9 * s, 9 * s, [(0, rgb('#d99a2b')), (0.4, rgb('#ffd36b')), (1, rgb('#c07d1c'))]))
        ctx.fill()
        ctx.rectangle(-9 * s, 0, 18 * s, 8 * s)
        ctx.set_source_rgba(0.55, 0.3, 0.05, 0.6)
        ctx.fill()
        ctx.restore()
    # paper bucket (plain, no branding)
    ctx.new_path()
    ctx.move_to(cx - w, by - 230 * s)
    ctx.line_to(cx + w, by - 230 * s)
    ctx.line_to(cx + w * 0.78, by)
    ctx.line_to(cx - w * 0.78, by)
    ctx.close_path()
    src(ctx, hgrad(cx - w, cx + w, [(0, rgb('#8f1d1d')), (0.35, rgb('#d23a32')), (1, rgb('#6e1414'))]))
    ctx.fill()
    ctx.rectangle(cx - w, by - 236 * s, 2 * w, 14 * s)
    src(ctx, rgb('#f2ede6'))
    ctx.fill()


def pizza(ctx, cx, cy, r, lift=0.0):
    ry = r * 0.45
    soft_shadow(ctx, cx + 12, cy + 18, r * 1.05, ry * 1.0, 0.55)
    ellipse(ctx, cx, cy, r, ry)
    src(ctx, vgrad(cy - ry, cy + ry, [(0, rgb('#d9964a')), (1, rgb('#9c5a22'))]))
    ctx.fill()
    ellipse(ctx, cx, cy, r * 0.9, ry * 0.88)
    src(ctx, rgb('#c7432a'))
    ctx.fill()
    rnd = random.Random(11)
    for _ in range(40):
        a = rnd.uniform(0, 2 * math.pi)
        d = math.sqrt(rnd.uniform(0, 1)) * 0.82
        ellipse(ctx, cx + math.cos(a) * r * d, cy + math.sin(a) * ry * d, rnd.uniform(18, 34), rnd.uniform(8, 15), rnd.uniform(0, 3))
        ctx.set_source_rgba(1.0, 0.86, 0.45, 0.9)
        ctx.fill()
    for _ in range(18):
        a = rnd.uniform(0, 2 * math.pi)
        d = math.sqrt(rnd.uniform(0.05, 1)) * 0.78
        px, py = cx + math.cos(a) * r * d, cy + math.sin(a) * ry * d
        ellipse(ctx, px, py, 22, 10)
        src(ctx, rgb('#8e1f18'))
        ctx.fill()
        ellipse(ctx, px - 4, py - 2, 12, 4)
        ctx.set_source_rgba(1, 0.6, 0.5, 0.35)
        ctx.fill()
    ctx.set_line_width(3)
    for k in range(8):
        a = k * math.pi / 4
        ctx.new_path()
        ctx.move_to(cx, cy)
        ctx.line_to(cx + math.cos(a) * r * 0.95, cy + math.sin(a) * ry * 0.95)
        ctx.set_source_rgba(0.35, 0.1, 0.05, 0.45)
        ctx.stroke()
    if lift > 0:
        # lifted slice with cheese pull
        tipx, tipy = cx + r * 0.1, cy + ry * 0.1
        hx, hy = cx + r * 0.55, cy - ry * 0.3 - lift * 260
        for k in range(6):
            ctx.new_path()
            ctx.move_to(tipx + k * 10 - 25, tipy)
            ctx.curve_to(tipx + k * 12, tipy - lift * 80, hx - 60 + k * 10, hy + 90, hx - 40 + k * 12, hy + 40)
            ctx.set_line_width(5)
            ctx.set_source_rgba(1.0, 0.88, 0.5, 0.9)
            ctx.stroke()
        ctx.save()
        ctx.translate(hx, hy)
        ctx.rotate(-0.5)
        ctx.new_path()
        ctx.move_to(-110, 30)
        ctx.line_to(90, -60)
        ctx.curve_to(120, -20, 120, 20, 100, 60)
        ctx.close_path()
        src(ctx, rgb('#c7432a'))
        ctx.fill()
        ctx.new_path()
        ctx.move_to(90, -60)
        ctx.curve_to(125, -20, 125, 20, 100, 60)
        ctx.set_line_width(26)
        src(ctx, rgb('#c9853e'))
        ctx.stroke()
        for (px, py) in ((0, 0), (50, -10), (40, 30)):
            ellipse(ctx, px, py, 18, 10)
            src(ctx, rgb('#8e1f18'))
            ctx.fill()
        ctx.restore()


def donut(ctx, cx, cy, r, icing=rgb('#e98bb0'), seed=0):
    ry = r * 0.55
    ellipse(ctx, cx, cy + 10, r, ry)
    src(ctx, vgrad(cy - ry, cy + ry + 10, [(0, rgb('#e0a55a')), (1, rgb('#8c5220'))]))
    ctx.fill()
    ctx.new_path()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(r * 0.92, ry * 0.85)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    src(ctx, icing)
    ctx.fill()
    rnd = random.Random(seed)
    cols = [rgb('#ffffff'), rgb('#ffd23f'), rgb('#3fc1ff'), rgb('#7ee07e')]
    for _ in range(26):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(0.45, 0.85)
        ellipse(ctx, cx + math.cos(a) * r * d, cy + math.sin(a) * ry * d * 0.9, 6, 2.2, rnd.uniform(0, 3))
        src(ctx, rnd.choice(cols))
        ctx.fill()
    ellipse(ctx, cx, cy + 2, r * 0.28, ry * 0.26)
    src(ctx, rgb('#3a2012'))
    ctx.fill()


def milkshake(ctx, cx, by, s=1.0):
    w0, w1, h = 90 * s, 62 * s, 320 * s
    soft_shadow(ctx, cx + 8, by + 4, w1 * 1.4, 18 * s, 0.5)
    # straw
    ctx.save()
    ctx.translate(cx + 20 * s, by - h - 60 * s)
    ctx.rotate(0.25)
    ctx.rectangle(-8 * s, -170 * s, 16 * s, 220 * s)
    src(ctx, rgb('#f4f4f4'))
    ctx.fill()
    for k in range(6):
        ctx.rectangle(-8 * s, -170 * s + k * 36 * s, 16 * s, 12 * s)
        src(ctx, rgb('#e04a5a'))
        ctx.fill()
    ctx.restore()
    ctx.new_path()
    ctx.move_to(cx - w0, by - h)
    ctx.line_to(cx + w0, by - h)
    ctx.line_to(cx + w1, by)
    ctx.line_to(cx - w1, by)
    ctx.close_path()
    src(ctx, hgrad(cx - w0, cx + w0, [(0, rgb('#c98aa0')), (0.35, rgb('#f7c6d6')), (1, rgb('#b27087'))]))
    ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.25)
    ctx.rectangle(cx - w0 * 0.7, by - h + 10, 10 * s, h - 20)
    ctx.fill()
    # whipped cream
    for k, (dx, dy, rr) in enumerate(((-50, 0, 48), (0, -10, 55), (50, 0, 48), (-20, -60, 42), (25, -58, 40), (0, -100, 34))):
        ctx.arc(cx + dx * s, by - h + dy * s, rr * s, 0, 2 * math.pi)
        src(ctx, vgrad(by - h - 140 * s, by - h + 40 * s, [(0, rgb('#ffffff')), (1, rgb('#e2dcd6'))]))
        ctx.fill()
    ctx.arc(cx + 5 * s, by - h - 145 * s, 22 * s, 0, 2 * math.pi)
    src(ctx, rgb('#c4102a'))
    ctx.fill()


def plate_stack(ctx, cx, by, n, s=1.0):
    for i in range(n):
        y = by - i * 14 * s
        ellipse(ctx, cx, y, 120 * s, 32 * s)
        src(ctx, vgrad(y - 32 * s, y + 32 * s, [(0, rgb('#f3f3f1')), (1, rgb('#b9bcc0'))]))
        ctx.fill()
        ctx.set_line_width(2)
        ellipse(ctx, cx, y, 120 * s, 32 * s)
        ctx.set_source_rgba(0, 0, 0, 0.15)
        ctx.stroke()
    y = by - (n - 1) * 14 * s
    rnd = random.Random(n)
    for _ in range(8):
        ctx.arc(cx + rnd.uniform(-60, 60) * s, y + rnd.uniform(-12, 12) * s, 3 * s, 0, 2 * math.pi)
        ctx.set_source_rgba(0.5, 0.3, 0.1, 0.7)
        ctx.fill()


# ------------------------------------------------------------------ HEALTHY FOOD

def chicken(ctx, cx, cy, s=1.0):
    for k in range(4):
        x = cx + (k - 1.5) * 44 * s
        ctx.save()
        ctx.translate(x, cy - k * 4 * s)
        ctx.rotate(-0.25)
        rrect(ctx, -26 * s, -44 * s, 52 * s, 88 * s, 20 * s)
        src(ctx, vgrad(-44 * s, 44 * s, [(0, rgb('#e9c38f')), (0.5, rgb('#c98f4f')), (1, rgb('#8f5a2a'))]))
        ctx.fill()
        rrect(ctx, -18 * s, -36 * s, 16 * s, 72 * s, 6 * s)
        ctx.set_source_rgba(1, 0.97, 0.9, 0.55)
        ctx.fill()
        ctx.set_line_width(5 * s)
        for gm in (-20, 4, 26):
            ctx.new_path()
            ctx.move_to(-26 * s, gm * s)
            ctx.line_to(26 * s, gm * s - 16 * s)
            ctx.set_source_rgba(0.25, 0.12, 0.05, 0.55)
            ctx.stroke()
        ctx.restore()


def rice(ctx, cx, cy, s=1.0):
    ctx.new_path()
    ctx.move_to(cx - 95 * s, cy + 18 * s)
    ctx.curve_to(cx - 90 * s, cy - 70 * s, cx + 90 * s, cy - 70 * s, cx + 95 * s, cy + 18 * s)
    ctx.close_path()
    src(ctx, vgrad(cy - 60 * s, cy + 18 * s, [(0, rgb('#ffffff')), (1, rgb('#d9d6cf'))]))
    ctx.fill()
    rnd = random.Random(5)
    for _ in range(90):
        x = cx + rnd.uniform(-80, 80) * s
        y = cy + rnd.uniform(-45, 12) * s
        ellipse(ctx, x, y, 5 * s, 2.2 * s, rnd.uniform(0, 3))
        ctx.set_source_rgba(0.75, 0.73, 0.68, 0.6)
        ctx.fill()


def broccoli(ctx, cx, cy, s=1.0, seed=1):
    rnd = random.Random(seed)
    ctx.set_line_width(14 * s)
    ctx.new_path()
    ctx.move_to(cx, cy + 20 * s)
    ctx.line_to(cx + 4 * s, cy - 20 * s)
    src(ctx, rgb('#8fbf5a'))
    ctx.stroke()
    for _ in range(12):
        x = cx + rnd.uniform(-34, 34) * s
        y = cy - 30 * s + rnd.uniform(-22, 14) * s
        r = rnd.uniform(13, 20) * s
        ctx.arc(x, y, r, 0, 2 * math.pi)
        g = cairo.RadialGradient(x - r * 0.3, y - r * 0.3, 1, x, y, r)
        g.add_color_stop_rgb(0, *rgb('#5ea83a'))
        g.add_color_stop_rgb(1, *rgb('#1f5a1b'))
        src(ctx, g)
        ctx.fill()


def egg_whole(ctx, cx, cy, s=1.0, brown=False):
    soft_shadow(ctx, cx + 6, cy + 42 * s, 42 * s, 12 * s, 0.5)
    ellipse(ctx, cx, cy, 36 * s, 48 * s)
    g = cairo.RadialGradient(cx - 12 * s, cy - 18 * s, 2, cx, cy, 55 * s)
    if brown:
        g.add_color_stop_rgb(0, *rgb('#f0d2b0'))
        g.add_color_stop_rgb(1, *rgb('#a87550'))
    else:
        g.add_color_stop_rgb(0, *rgb('#ffffff'))
        g.add_color_stop_rgb(1, *rgb('#c9c4bb'))
    src(ctx, g)
    ctx.fill()


def egg_half(ctx, cx, cy, s=1.0):
    soft_shadow(ctx, cx + 6, cy + 18 * s, 50 * s, 14 * s, 0.45)
    ellipse(ctx, cx, cy, 48 * s, 30 * s)
    src(ctx, vgrad(cy - 30 * s, cy + 30 * s, [(0, rgb('#ffffff')), (1, rgb('#dcd8d0'))]))
    ctx.fill()
    ellipse(ctx, cx + 2 * s, cy - 2 * s, 22 * s, 16 * s)
    g = cairo.RadialGradient(cx - 5 * s, cy - 6 * s, 1, cx, cy, 24 * s)
    g.add_color_stop_rgb(0, *rgb('#ffd35a'))
    g.add_color_stop_rgb(1, *rgb('#e89a12'))
    src(ctx, g)
    ctx.fill()


def yogurt_bowl(ctx, cx, cy, r):
    bowl(ctx, cx, cy, r, color=rgb('#6f8196'), fill=rgb('#f6f4ef'))
    ctx.set_line_width(4)
    ctx.new_path()
    for k in range(60):
        a = k / 60 * 4 * math.pi
        rr = r * 0.6 * (1 - k / 70)
        x, y = cx + math.cos(a) * rr, cy + 3 + math.sin(a) * rr * 0.34
        ctx.line_to(x, y) if k else ctx.move_to(x, y)
    ctx.set_source_rgba(0.8, 0.78, 0.74, 0.8)
    ctx.stroke()
    rnd = random.Random(2)
    for _ in range(9):
        x = cx + rnd.uniform(-0.45, 0.55) * r
        y = cy + rnd.uniform(-0.18, 0.12) * r
        ctx.arc(x, y, 11, 0, 2 * math.pi)
        g = cairo.RadialGradient(x - 3, y - 3, 1, x, y, 11)
        g.add_color_stop_rgb(0, *rgb('#6c7fd6'))
        g.add_color_stop_rgb(1, *rgb('#24285e'))
        src(ctx, g)
        ctx.fill()


def salmon(ctx, cx, cy, s=1.0):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(-0.12)
    rrect(ctx, -130 * s, -50 * s, 260 * s, 100 * s, 36 * s)
    src(ctx, vgrad(-50 * s, 50 * s, [(0, rgb('#f7a06f')), (0.55, rgb('#e56f45')), (1, rgb('#b0482a'))]))
    ctx.fill()
    ctx.set_line_width(4 * s)
    for k in range(-4, 5):
        ctx.new_path()
        ctx.move_to(k * 28 * s - 10 * s, -46 * s)
        ctx.curve_to(k * 28 * s + 12 * s, -10 * s, k * 28 * s - 12 * s, 10 * s, k * 28 * s + 10 * s, 46 * s)
        ctx.set_source_rgba(1, 0.9, 0.85, 0.5)
        ctx.stroke()
    rrect(ctx, -130 * s, -50 * s, 260 * s, 26 * s, 18 * s)
    ctx.set_source_rgba(0.45, 0.2, 0.08, 0.35)
    ctx.fill()
    ctx.restore()


def beans_bowl(ctx, cx, cy, r):
    bowl(ctx, cx, cy, r, color=rgb('#8a7a66'), fill=rgb('#4a1d17'))
    rnd = random.Random(8)
    for _ in range(70):
        x = cx + rnd.uniform(-0.8, 0.8) * r
        y = cy + rnd.uniform(-0.25, 0.25) * r
        if ((x - cx) / r) ** 2 + ((y - cy) / (r * 0.32)) ** 2 > 0.8:
            continue
        ellipse(ctx, x, y, 12, 7, rnd.uniform(0, 3))
        src(ctx, rnd.choice([rgb('#7a2a22'), rgb('#5a1a15'), rgb('#9b3a2c')]))
        ctx.fill()
        ellipse(ctx, x - 3, y - 2, 5, 2)
        ctx.set_source_rgba(1, 1, 1, 0.3)
        ctx.fill()


def tomatoes(ctx, cx, cy, s=1.0):
    for (dx, dy) in ((-30, 0), (10, 8), (40, -6)):
        x, y = cx + dx * s, cy + dy * s
        ctx.arc(x, y, 20 * s, 0, 2 * math.pi)
        g = cairo.RadialGradient(x - 6 * s, y - 6 * s, 1, x, y, 21 * s)
        g.add_color_stop_rgb(0, *rgb('#ff7a5c'))
        g.add_color_stop_rgb(1, *rgb('#a3180c'))
        src(ctx, g)
        ctx.fill()


def spinach(ctx, cx, cy, s=1.0):
    rnd = random.Random(6)
    for _ in range(7):
        ctx.save()
        ctx.translate(cx + rnd.uniform(-50, 50) * s, cy + rnd.uniform(-14, 14) * s)
        ctx.rotate(rnd.uniform(-1, 1))
        ellipse(ctx, 0, 0, 38 * s, 18 * s)
        src(ctx, vgrad(-18 * s, 18 * s, [(0, rgb('#4f9a3a')), (1, rgb('#1e4d1a'))]))
        ctx.fill()
        ctx.restore()
