import argparse
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
for candidate in (
    SCRIPT_DIR.parent / ".python_deps",
    SCRIPT_DIR.parent.parent / ".python_deps",
    Path.cwd() / ".python_deps",
):
    if candidate.exists():
        sys.path.insert(0, str(candidate))

try:
    from psd_tools import PSDImage
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: psd_tools. Install with: python -m pip install psd-tools"
    ) from exc


SCALE = 2
INK = (12, 34, 63, 255)
PAPER = (244, 237, 219, 255)
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
KEEP_TEXT_LAYERS = {"01", "02", "03"}
QR_BOX = (801, 1356, 982, 1530)
QR_BACKING = (790, 1348, 988, 1534)

TYPE = {
    "date": 43,
    "date_range": 22,
    "weekday": 27,
    "weekday_range": 17,
    "tag": 18,
    "category": 28,
    "title_max": 43,
    "title_min": 18,
    "host": 21,
    "time": 21,
    "place": 28,
}

ROWS = [
    {"date_box": (171, 568, 334, 760), "main_box": (354, 568, 744, 760), "side_box": (760, 568, 920, 760), "tag_y": 164},
    {"date_box": (171, 871, 334, 1063), "main_box": (354, 871, 744, 1063), "side_box": (760, 871, 920, 1063), "tag_y": 164},
    {"date_box": (171, 1177, 334, 1368), "main_box": (354, 1177, 744, 1368), "side_box": (760, 1177, 920, 1368), "tag_y": 164},
]


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size * SCALE)


def sc_box(box):
    return tuple(int(v * SCALE) for v in box)


def draw_center(draw, xy, text, fnt, fill=INK, spacing=0):
    box = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=spacing, align="center")
    x, y = xy
    draw.multiline_text(
        (x - (box[2] - box[0]) / 2, y - (box[3] - box[1]) / 2),
        text,
        font=fnt,
        fill=fill,
        spacing=spacing,
        align="center",
    )


def draw_centered_text(draw, xy, text, fnt, fill=INK):
    box = draw.textbbox((0, 0), text, font=fnt)
    x, y = xy
    draw.text((x - (box[2] - box[0]) / 2, y - (box[3] - box[1]) / 2), text, font=fnt, fill=fill)


def draw_italic_center(img, xy, text, fnt, fill=INK, shear=-0.10):
    temp = Image.new("RGBA", (520 * SCALE, 100 * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(temp)
    box = d.textbbox((0, 0), text, font=fnt)
    d.text(((temp.width - (box[2] - box[0])) // 2, (temp.height - (box[3] - box[1])) // 2 - box[1]), text, font=fnt, fill=fill)
    offset = abs(shear) * temp.height
    warped = temp.transform(
        (int(temp.width + offset), temp.height),
        Image.Transform.AFFINE,
        (1, shear, -offset if shear < 0 else 0, 0, 1, 0),
        Image.Resampling.BICUBIC,
    )
    bbox = warped.getbbox()
    if bbox:
        cropped = warped.crop(bbox)
        img.alpha_composite(cropped, (int(xy[0] - cropped.width / 2), int(xy[1] - cropped.height / 2)))


def paper_cover(img, box, seed):
    random.seed(seed)
    x1, y1, x2, y2 = sc_box(box)
    patch = Image.new("RGBA", (x2 - x1, y2 - y1), PAPER)
    noise = Image.effect_noise(patch.size, 7).convert("L")
    tint = Image.new("RGBA", patch.size, (250, 245, 231, 255))
    patch = Image.composite(tint, patch, noise.point(lambda p: 255 if p > 146 else 0))
    patch = patch.filter(ImageFilter.GaussianBlur(0.25))
    img.alpha_composite(patch, (x1, y1))


def compose_blank_template(template):
    psd = PSDImage.open(template)

    def include_layer(layer):
        if layer.kind != "type":
            return layer.visible
        return layer.visible and layer.name in KEEP_TEXT_LAYERS

    return psd.composite(layer_filter=include_layer).convert("RGBA")


def normalize_event(event):
    event = dict(event)
    tag = str(event.get("tag", "")).strip()
    event["tag"] = "" if tag.lower() in {"无", "无标签", "none", "null", ""} else tag
    place = str(event.get("place", "")).replace("/", "\n").strip()
    for suffix in ("邻里", "青隅", "童筑"):
        if place == f"蔡马{suffix}":
            place = f"蔡马\n{suffix}"
    event["place"] = place
    return event


def fit_font_for_line(draw, text, max_w, max_size, min_size, bold=True):
    size = max_size
    while size >= min_size:
        fnt = font(size, bold)
        box = draw.textbbox((0, 0), text, font=fnt)
        if box[2] - box[0] <= max_w * SCALE:
            return fnt
        size -= 1
    return font(min_size, bold)


def draw_fit_scaled_title(img, center, max_w, max_h, text, max_size, min_size, fill=INK, x_scale=0.88):
    text = text.replace("\r", "").replace("\n", "")
    size = max_size
    while size >= min_size:
        fnt = font(size, True)
        probe = Image.new("RGBA", (int(max_w * SCALE * 1.4), int(max_h * SCALE * 1.6)), (0, 0, 0, 0))
        box = ImageDraw.Draw(probe).textbbox((0, 0), text, font=fnt)
        if (box[2] - box[0]) * x_scale <= max_w * SCALE and box[3] - box[1] <= max_h * SCALE:
            break
        size -= 1
    fnt = font(size, True)
    text_box = Image.new("RGBA", (int(max_w * SCALE * 1.5), int(max_h * SCALE * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(text_box)
    box = d.textbbox((0, 0), text, font=fnt)
    d.text(((text_box.width - (box[2] - box[0])) / 2, (text_box.height - (box[3] - box[1])) / 2 - box[1]), text, font=fnt, fill=fill)
    crop = text_box.crop(text_box.getbbox())
    crop = crop.resize((int(crop.width * x_scale), crop.height), Image.Resampling.BICUBIC)
    img.alpha_composite(crop, (int(center[0] * SCALE - crop.width / 2), int(center[1] * SCALE - crop.height / 2)))


def draw_tag(draw, box, tag, y_offset=164):
    if not tag:
        return
    x1, y1, x2, y2 = sc_box(box)
    cx = (x1 + x2) / 2
    y = y1 + y_offset * SCALE
    poly = [
        (cx - 44 * SCALE, y - 17 * SCALE),
        (cx + 42 * SCALE, y - 21 * SCALE),
        (cx + 55 * SCALE, y),
        (cx + 39 * SCALE, y + 21 * SCALE),
        (cx - 50 * SCALE, y + 17 * SCALE),
        (cx - 57 * SCALE, y - 2 * SCALE),
    ]
    draw.polygon(poly, fill=(235, 194, 60, 255))
    draw.line(poly + [poly[0]], fill=(255, 255, 255, 255), width=3 * SCALE)
    draw_centered_text(draw, (cx, y - 1 * SCALE), tag, fit_font_for_line(draw, tag, 54, TYPE["tag"], 13, True), (255, 255, 255, 255))


def draw_date_block(img, box, date_text, weekday_text):
    x1, y1, x2, y2 = sc_box(box)
    cx = (x1 + x2) / 2
    if "-" in date_text:
        draw_italic_center(img, (cx, y1 + 70 * SCALE), date_text, font(TYPE["date_range"], True), shear=-0.07)
        draw_italic_center(img, (cx, y1 + 121 * SCALE), f"({weekday_text})", font(TYPE["weekday_range"], True), shear=-0.04)
    else:
        draw_italic_center(img, (cx, y1 + 73 * SCALE), date_text, font(TYPE["date"], True))
        draw_italic_center(img, (cx, y1 + 122 * SCALE), f"({weekday_text})", font(TYPE["weekday"], True), shear=-0.06)


def align_qr(img):
    qr = img.crop(sc_box(QR_BOX))
    bx1, by1, bx2, by2 = sc_box(QR_BACKING)
    paper_cover(img, QR_BACKING, 90)
    d = ImageDraw.Draw(img)
    d.rectangle((bx1 + 10 * SCALE, by1 + 10 * SCALE, bx2 - 10 * SCALE, by2 - 10 * SCALE), fill=(255, 255, 255, 255))
    img.alpha_composite(qr, (bx1 + ((bx2 - bx1) - qr.width) // 2, by1 + ((by2 - by1) - qr.height) // 2))


def draw_event(draw, img, row, idx, event):
    y = row["date_box"][1]
    paper_cover(img, (178, y + 18, 328, y + 184), idx * 10 + 1)
    draw_date_block(img, row["date_box"], event["date"], event["weekday"])
    draw_tag(draw, row["date_box"], event.get("tag", ""), row["tag_y"])

    mx1, my1, mx2, my2 = sc_box(row["main_box"])
    draw_center(draw, ((mx1 + mx2) / 2, my1 + 43 * SCALE), event["category"], font(TYPE["category"]))
    draw_fit_scaled_title(
        img,
        ((row["main_box"][0] + row["main_box"][2]) / 2, row["main_box"][1] + 94),
        row["main_box"][2] - row["main_box"][0] - 52,
        40,
        event["title"],
        TYPE["title_max"],
        TYPE["title_min"],
    )
    draw_center(draw, ((mx1 + mx2) / 2, my2 - 25 * SCALE), f"主理人：{event['host']}", font(TYPE["host"]))

    sx1, sy1, sx2, sy2 = sc_box(row["side_box"])
    draw_center(draw, ((sx1 + sx2) / 2, sy1 + 60 * SCALE), event["time"], font(TYPE["time"], True))
    draw_center(draw, ((sx1 + sx2) / 2, sy1 + 116 * SCALE), event["place"], font(TYPE["place"], True))


def render(template, events, output):
    if len(events) != 3:
        raise ValueError("events JSON must contain exactly three activity objects")
    base = compose_blank_template(template).resize((1024 * SCALE, 1536 * SCALE), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(base)
    for idx, (row, event) in enumerate(zip(ROWS, [normalize_event(e) for e in events]), start=1):
        draw_event(draw, base, row, idx, event)
    align_qr(base)
    base.convert("RGB").save(output, quality=98, dpi=(300, 300))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.events, "r", encoding="utf-8") as f:
        events = json.load(f)
    render(args.template, events, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
