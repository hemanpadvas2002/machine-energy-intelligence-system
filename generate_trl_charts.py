from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


months = [0, 6, 12, 18, 24, 30, 36]
trl_fc_hw = [4, 5, 5.5, 6, 6, 7, 7]
trl_fc_sw = [3, 4, 5, 5.5, 6, 7, 7]
trl_fc = [4, 5, 5.5, 6, 6, 7, 7]
trl_test_rig = [4, 5, 6, 6, 7, 7, 7]
trl_prognostics = [3, 4, 4, 5, 6, 7, 7]

NAVY = "#1B3A6B"
STEEL = "#2E6DA4"
TEAL = "#006B6B"
ORANGE = "#C7511F"
BG = "#F4F7FB"
GRID = "#D0D8E8"
WHITE = "#FFFFFF"
DARK = "#22304A"
FC_HW = "#1B3A6B"
FC_SW = "#2196F3"


def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


F_TITLE = font(28, True)
F_AXIS = font(20)
F_TICK = font(18)
F_SMALL = font(15, True)
F_LABEL = font(17, True)
F_LEGEND = font(18)


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def blend(fg, bg=WHITE, alpha=0.55):
    f = hex_to_rgb(fg) if isinstance(fg, str) else fg
    b = hex_to_rgb(bg) if isinstance(bg, str) else bg
    return tuple(round(f[i] * alpha + b[i] * (1 - alpha)) for i in range(3))


def text_size(draw, text, fnt):
    box = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=3)
    return box[2] - box[0], box[3] - box[1]


def dashed_line(draw, xy, fill, width=1, dash=9, gap=7):
    x1, y1, x2, y2 = xy
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if length == 0:
        return
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    pos = 0
    while pos < length:
        end = min(pos + dash, length)
        draw.line(
            (x1 + dx * pos, y1 + dy * pos, x1 + dx * end, y1 + dy * end),
            fill=fill,
            width=width,
        )
        pos += dash + gap


def diamond(draw, cx, cy, r, fill, outline=None, width=1):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw.polygon(pts, fill=fill, outline=outline)
    if outline and width > 1:
        for i in range(1, width):
            pts2 = [(cx, cy - r + i), (cx + r - i, cy), (cx, cy + r - i), (cx - r + i, cy)]
            draw.line(pts2 + [pts2[0]], fill=outline, width=1)


def marker(draw, x, y, color, kind="o", outer=True, alpha=False):
    color_rgb = hex_to_rgb(color)
    if alpha:
        color_rgb = blend(color, WHITE, 0.55)
    if kind == "D":
        if outer:
            diamond(draw, x, y, 12, WHITE, color_rgb, 4)
            diamond(draw, x, y, 6, color_rgb)
        else:
            diamond(draw, x, y, 9, color_rgb)
    elif kind == "s":
        if outer:
            draw.rounded_rectangle((x - 12, y - 12, x + 12, y + 12), radius=2, fill=WHITE, outline=color_rgb, width=4)
            draw.rectangle((x - 6, y - 6, x + 6, y + 6), fill=color_rgb)
        else:
            draw.rectangle((x - 9, y - 9, x + 9, y + 9), fill=color_rgb)
    elif kind == "^":
        tri = [(x, y - 12), (x + 13, y + 12), (x - 13, y + 12)]
        tri_inner = [(x, y - 6), (x + 7, y + 6), (x - 7, y + 6)]
        if outer:
            draw.polygon(tri, fill=WHITE, outline=color_rgb)
            draw.line(tri + [tri[0]], fill=color_rgb, width=4)
            draw.polygon(tri_inner, fill=color_rgb)
        else:
            draw.polygon(tri, fill=color_rgb)
    else:
        if outer:
            draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=WHITE, outline=color_rgb, width=4)
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color_rgb)
        else:
            draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=color_rgb)


class Chart:
    def __init__(self, width, height, title, xlim=(-1, 39), ylim=(0.5, 7.9)):
        self.width = width
        self.height = height
        self.title = title
        self.xlim = xlim
        self.ylim = ylim
        self.left = 125
        self.right = width - 55
        self.top = 88
        self.bottom = height - 95
        self.img = Image.new("RGB", (width, height), WHITE)
        self.draw = ImageDraw.Draw(self.img)

    def x(self, value):
        lo, hi = self.xlim
        return self.left + (value - lo) / (hi - lo) * (self.right - self.left)

    def y(self, value):
        lo, hi = self.ylim
        return self.bottom - (value - lo) / (hi - lo) * (self.bottom - self.top)

    def base(self):
        d = self.draw
        d.rectangle((self.left, self.top, self.right, self.bottom), fill=hex_to_rgb(BG))
        for lo, hi, col in [(1, 3, "#FFF8E1"), (3, 5, "#E8F5E9"), (5, 7, "#E3F2FD"), (7, 8, "#E0F7FA")]:
            d.rectangle((self.left, self.y(hi), self.right, self.y(lo)), fill=blend(col))
        for trl in range(1, 8):
            y = self.y(trl)
            d.line((self.left, y, self.right, y), fill=hex_to_rgb(GRID), width=2)
        for m in [6, 12, 18, 24, 30, 36]:
            x = self.x(m)
            dashed_line(d, (x, self.top, x, self.bottom), fill=blend(DARK, WHITE, 0.22), width=1, dash=8, gap=8)
            txt = f"M{m}"
            tw, th = text_size(d, txt, F_SMALL)
            d.text((x - tw / 2, self.bottom - 30), txt, font=F_SMALL, fill=hex_to_rgb(DARK))
        d.line((self.left, self.bottom, self.right, self.bottom), fill=hex_to_rgb(GRID), width=3)
        d.line((self.left, self.top, self.left, self.bottom), fill=hex_to_rgb(GRID), width=3)
        for m in [0, 6, 12, 18, 24, 30, 36]:
            x = self.x(m)
            label = f"M{m}"
            tw, _ = text_size(d, label, F_TICK)
            d.text((x - tw / 2, self.bottom + 18), label, font=F_TICK, fill=hex_to_rgb(DARK))
        yticks = [(1, "TRL 1"), (2, "TRL 2"), (3, "TRL 3"), (4, "TRL 4"), (5, "TRL 5"), (5.5, "TRL 5+"), (6, "TRL 6"), (7, "TRL 7")]
        for val, label in yticks:
            y = self.y(val)
            tw, th = text_size(d, label, F_TICK)
            d.text((self.left - tw - 15, y - th / 2), label, font=F_TICK, fill=hex_to_rgb(DARK))
        tw, th = text_size(d, self.title, F_TITLE)
        d.text(((self.width - tw) / 2, 28), self.title, font=F_TITLE, fill=hex_to_rgb(DARK))
        xlabel = "Programme Month"
        tw, _ = text_size(d, xlabel, F_AXIS)
        d.text(((self.width - tw) / 2, self.height - 45), xlabel, font=F_AXIS, fill=hex_to_rgb(DARK))
        ylabel = "Technology Readiness Level (TRL)"
        tmp = Image.new("RGBA", (420, 35), (255, 255, 255, 0))
        td = ImageDraw.Draw(tmp)
        td.text((0, 0), ylabel, font=F_AXIS, fill=hex_to_rgb(DARK))
        tmp = tmp.rotate(90, expand=True)
        self.img.paste(tmp, (22, int((self.height - tmp.height) / 2)), tmp)

    def line(self, xvals, yvals, color, kind="o", width=6, dashed=False, label_points=True, label_offset=28):
        pts = [(self.x(x), self.y(y)) for x, y in zip(xvals, yvals)]
        for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
            if dashed:
                dashed_line(self.draw, (x1, y1, x2, y2), fill=hex_to_rgb(color), width=width, dash=18, gap=12)
            else:
                self.draw.line((x1, y1, x2, y2), fill=hex_to_rgb(color), width=width)
        for i, (x, y) in enumerate(pts):
            marker(self.draw, x, y, color, kind, outer=i > 0, alpha=i == 0)
            if label_points and i > 0:
                yi = yvals[i]
                label = "TRL 5+" if yi == 5.5 else f"TRL {int(yi)}"
                tw, th = text_size(self.draw, label, F_LABEL)
                self.draw.text((x - tw / 2, y - th - label_offset if label_offset > 0 else y - label_offset), label, font=F_LABEL, fill=hex_to_rgb(color))

    def badge(self, xi, yi, text, color):
        x, y = self.x(xi), self.y(yi)
        tw, th = text_size(self.draw, text, F_SMALL)
        pad_x, pad_y = 12, 8
        box = (x - tw / 2 - pad_x, y - th / 2 - pad_y, x + tw / 2 + pad_x, y + th / 2 + pad_y)
        self.draw.rounded_rectangle(box, radius=9, fill=hex_to_rgb(color))
        self.draw.multiline_text((x - tw / 2, y - th / 2), text, font=F_SMALL, fill=hex_to_rgb(WHITE), align="center", spacing=3)

    def legend(self, entries):
        x0, y0 = self.left + 18, self.top + 18
        widths = [text_size(self.draw, text, F_LEGEND)[0] for _, text, _ in entries]
        box_w = max(widths) + 70
        box_h = len(entries) * 34 + 24
        self.draw.rounded_rectangle((x0, y0, x0 + box_w, y0 + box_h), radius=4, fill=WHITE, outline=hex_to_rgb(GRID), width=2)
        for idx, (color, text, kind) in enumerate(entries):
            y = y0 + 26 + idx * 34
            self.draw.rectangle((x0 + 16, y - 9, x0 + 36, y + 9), fill=hex_to_rgb(color))
            self.draw.text((x0 + 50, y - 11), text, font=F_LEGEND, fill=hex_to_rgb(DARK))

    def save(self, path):
        self.img.save(path)


def build():
    out = Path("outputs")
    out.mkdir(exist_ok=True)

    chart = Chart(1650, 975, "Flight Controller (FC) - TRL Progression  [ HW + SW ]", xlim=(-1.8, 39))
    chart.base()
    chart.line(months, trl_fc_hw, FC_HW, "o", dashed=False, label_offset=28)
    chart.line(months, trl_fc_sw, FC_SW, "D", dashed=True, label_offset=-28)
    chart.badge(0, trl_fc_hw[0] + 0.35, "HW\nTRL 4", FC_HW)
    chart.badge(0, trl_fc_sw[0] - 0.40, "SW\nTRL 3", FC_SW)
    chart.badge(36, 7.3, "Both -> TRL 7", DARK)
    chart.legend([(FC_HW, "Hardware (HW)  solid", "o"), (FC_SW, "Software (SW)  dashed", "D")])
    chart.save(out / "chart_fc.png")

    chart = Chart(1650, 900, "3-Axis Test Rig - TRL Progression  [ HW ]")
    chart.base()
    chart.line(months, trl_test_rig, TEAL)
    chart.badge(0, trl_test_rig[0], "Start\nTRL 4", TEAL)
    chart.badge(36, trl_test_rig[-1], "End\nTRL 7", DARK)
    chart.save(out / "chart_rig.png")

    chart = Chart(1650, 900, "Prognostics Software - TRL Progression  [ SW ]")
    chart.base()
    chart.line(months, trl_prognostics, ORANGE)
    chart.badge(0, trl_prognostics[0], "Start\nTRL 3", ORANGE)
    chart.badge(36, trl_prognostics[-1], "End\nTRL 7", DARK)
    chart.save(out / "chart_prog.png")

    chart = Chart(1950, 1050, "Combined TRL Progression - All Subsystems", xlim=(-1.5, 40), ylim=(0.5, 8.2))
    chart.base()
    chart.line(months, trl_fc, NAVY, "o", width=5, label_points=False)
    chart.line(months, trl_test_rig, TEAL, "s", width=5, label_points=False)
    chart.line(months, trl_prognostics, ORANGE, "^", width=5, label_points=False)
    chart.legend([(NAVY, "Flight Controller (FC)", "o"), (TEAL, "3-Axis Test Rig", "s"), (ORANGE, "Prognostics Software", "^")])
    chart.save(out / "chart_combined.png")


if __name__ == "__main__":
    build()
    print("Charts written to outputs/")
