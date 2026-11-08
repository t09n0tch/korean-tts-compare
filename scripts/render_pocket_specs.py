"""Render a shareable Korean spec table to PNG and editable SVG.

uv run --with pillow python scripts/render_pocket_specs.py
Set TTS_INFOGRAPHIC_FONT to a Korean font file on non-macOS hosts.
"""
from pathlib import Path
import html
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/images"
OUT.mkdir(parents=True, exist_ok=True)
SPECS = json.loads((ROOT / "examples/pocket-inference-specs.json").read_text())
BENCH = json.loads((ROOT / SPECS["benchmark"]).read_text())["models"]
FONT = os.environ.get("TTS_INFOGRAPHIC_FONT", "/System/Library/Fonts/AppleSDGothicNeo.ttc")
W, H, SCALE = 1600, 2320, 2
INK, MUTED, BLUE, PURPLE = "#14213D", "#53627C", "#175CD3", "#6941C6"
BG, LINE = "#F3F6FB", "#DCE3EE"
im = Image.new("RGB", (W * SCALE, H * SCALE), BG)
draw = ImageDraw.Draw(im)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
       '<title id="title">Pocket-TTS Korean CPU 추론 사양 비교</title>',
       '<desc id="desc">100M과 300M의 모델 사양 및 Apple M6 CPU 4스레드 실측. 메모리와 합성 시간은 별도 실행에서 측정했습니다.</desc>']
fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in fonts:
        # Apple SD Gothic Neo: index 0 regular, index 6 bold.
        index = 6 if bold and Path(FONT).name == "AppleSDGothicNeo.ttc" else 0
        fonts[key] = ImageFont.truetype(FONT, int(size * SCALE), index=index)
    return fonts[key]


def rect(x, y, w, h, fill, radius=0, stroke=None):
    box = tuple(round(v * SCALE) for v in (x, y, x + w, y + h))
    draw.rounded_rectangle(box, radius=radius * SCALE, fill=fill, outline=stroke, width=SCALE)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"' + (f' stroke="{stroke}"' if stroke else '') + '/>')


def text(x, y, value, size=30, color=INK, bold=False, center=False, max_width=None):
    f = font(size, bold)
    width = draw.textlength(value, font=f) / SCALE
    if max_width and width > max_width:
        raise ValueError(f"Text overflows: {value} ({width:.0f} > {max_width})")
    if y > H - 30:
        raise ValueError("Text outside canvas")
    draw.text((x * SCALE, y * SCALE), value, font=f, fill=color, anchor="ms" if center else "ls")
    anchor = "middle" if center else "start"
    svg.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Apple SD Gothic Neo, Noto Sans KR, Malgun Gothic, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{html.escape(value)}</text>')


def rule(y):
    draw.line((72 * SCALE, y * SCALE, 1528 * SCALE, y * SCALE), fill=LINE, width=SCALE)
    svg.append(f'<path d="M72 {y}H1528" stroke="{LINE}"/>')


rect(0, 0, W, H, BG)
rect(72, 58, 7, 29, BLUE, 3)
text(96, 84, "DEVELOPER REFERENCE  /  CPU INFERENCE", 26, BLUE, True)
text(72, 166, "Pocket-TTS Korean", 70, INK, True)
text(72, 222, "100M · 300M 추론 사양과 로컬 실측 비교", 37, MUTED)
rect(72, 264, 1456, 94, "#E7EEF9", 18)
text(100, 304, "측정 환경", 27, BLUE, True)
text(270, 304, "Apple M6  /  RAM 32GB  /  macOS 27.0.1", 29, INK, True)
text(270, 339, "CPU 4스레드 · GPU 미사용 · 동일 상담 대사 5개 · 2026.11.08", 25, MUTED)

X1, X2 = 862, 1306
rect(72, 404, 1456, 1028, "#FFFFFF", 22, LINE)
rect(72, 404, 1456, 100, INK, 20)
rect(72, 484, 1456, 20, INK)
text(102, 462, "비교 항목", 31, "#FFFFFF", True)
text(X1, 450, "100M", 41, "#FFFFFF", True, True)
text(X2, 450, "300M", 41, "#FFFFFF", True, True)
text(X1, 487, "6-layer student", 24, "#BFD5FF", False, True)
text(X2, 487, "24-layer teacher", 24, "#DDCBFF", False, True)


def section(y, label):
    rect(72, y, 1456, 56, "#E9EEF6")
    text(102, y + 38, label, 27, MUTED, True)


def row(y, label, a, b, height=72, emphasis=False, index=0):
    fill = "#F0F5FF" if emphasis else ("#FFFFFF" if index % 2 == 0 else "#FAFBFD")
    rect(73, y, 1454, height, fill)
    text(102, y + height / 2 + 11, label, 29, INK, emphasis, max_width=510)
    text(X1, y + height / 2 + 12, a, 35, BLUE if emphasis else INK, True, True, 416)
    text(X2, y + height / 2 + 12, b, 35, PURPLE if emphasis else INK, True, True, 416)
    rule(y + height)


section(504, "01   모델 사양  /  공개 모델 카드 및 설치 파일")
models = SPECS["models"]
rows = [
    ("전체 파라미터 · Mimi 코덱 포함", f'{models["pocket100"]["parameters"] / 1e6:.2f}M', f'{models["pocket300"]["parameters"] / 1e6:.2f}M'),
    ("FlowLM Transformer 층 수", "6 layers", "24 layers"),
    ("가중치 파일 크기", f'{models["pocket100"]["weights_bytes"] / 1e6:.0f} MB', f'{models["pocket300"]["weights_bytes"] / 1e9:.3f} GB'),
    ("추론 정밀도 · 양자화 없음", "FP32", "FP32"),
    ("음성 출력", "24 kHz · Mono", "24 kHz · Mono"),
]
for i, values in enumerate(rows):
    row(560 + i * 72, *values, index=i)

section(920, "02   CPU 실측  /  같은 원문 5개를 순차 생성")
a, b = BENCH["pocket100"], BENCH["pocket300"]
ma, mb = SPECS["memory_measurement"]["pocket100"], SPECS["memory_measurement"]["pocket300"]
rows = [
    ("프로세스 최대 RAM · RSS", f'{ma["maximum_rss_bytes"] / 1e9:.2f} GB', f'{mb["maximum_rss_bytes"] / 1e9:.2f} GB'),
    ("초기 준비 시간", f'{a["load_seconds"]:.2f} s', f'{b["load_seconds"]:.2f} s'),
    ("5개 전체 합성 시간 · 준비 제외", f'{a["generation_seconds"]:.2f} s', f'{b["generation_seconds"]:.2f} s'),
    ("5개 전체 출력 음성 길이", f'{a["audio_seconds"]:.2f} s', f'{b["audio_seconds"]:.2f} s'),
    ("RTF · 낮을수록 빠름", f'{a["rtf"]:.4f}', f'{b["rtf"]:.4f}'),
    ("대사 1개 합성 시간", *[
        f'{min(item["generation_seconds"] for item in model["items"]):.2f}–{max(item["generation_seconds"] for item in model["items"]):.2f} s'
        for model in (a, b)
    ]),
]
for i, values in enumerate(rows):
    row(976 + i * 76, *values, height=76, emphasis=i in (0, 2), index=i)

rect(72, 1470, 1456, 226, "#FFFFFF", 20, LINE)
text(102, 1515, "재현 가능한 실행 설정", 30, INK, True)
text(102, 1560, "Python 3.11  ·  PyTorch 2.11  ·  Pocket-TTS 4.0.1  ·  device=cpu", 29, MUTED, max_width=1396)
text(102, 1604, "threads=4  ·  temperature=0.3  ·  decode steps=1  ·  EOS=-1.0  ·  seed=42", 28, MUTED, max_width=1396)
text(102, 1648, "공통 참조 음성: Supertonic F1 합성음 8.77초  /  다운로드 후 오프라인 실행", 28, MUTED, max_width=1396)

text(72, 1762, "수치를 읽는 방법", 31, INK, True)
notes = [
    "최대 RSS: 별도 실행에서 로딩·합성 중 측정한 프로세스 메모리. 공식 최소 RAM이 아닙니다.",
    "초기 준비: 런타임 import + 모델 로딩 + 참조 음성 처리. 합성 시간은 준비 시간을 제외합니다.",
    "RTF = 전체 합성 시간 ÷ 전체 출력 음성 길이. 1 미만이면 재생 시간보다 빠릅니다.",
    "현재 UI는 전체 WAV 완성 후 재생합니다. 이 수치는 첫 청크 지연(TTFA)이 아닙니다.",
    "Intel 장비 성능은 미측정입니다. Windows 설치 경로는 WSL2 Ubuntu입니다.",
]
for i, value in enumerate(notes):
    rect(74, 1799 + i * 43, 6, 6, MUTED, 3)
    text(94, 1817 + i * 43, value, 27, MUTED, max_width=1434)

rule(2030)
text(72, 2076, "seastar105 한국어 커뮤니티 모델 · Kyutai Pocket-TTS 기반", 27, INK, True)
text(72, 2115, "가중치 CC BY 4.0  /  런타임 코드 MIT  ·  가중치·RSS 용량은 십진 단위", 26, MUTED)
text(72, 2163, "모델 카드  huggingface.co/seastar105/pocket-tts-korean-{100m,300m}", 24, MUTED)
text(72, 2201, "실측 기록  github.com/t09n0tch/korean-tts-compare/tree/main/examples", 24, MUTED)
text(72, 2269, "KOREAN CPU TTS COMPARE", 23, BLUE, True)
text(1388, 2269, "2026.11.08", 23, MUTED)
svg.append("</svg>")
im.save(OUT / "pocket-korean-inference-specs.png", optimize=True)
(OUT / "pocket-korean-inference-specs.svg").write_text("\n".join(svg), encoding="utf-8")
print(f"Rendered {W * SCALE}×{H * SCALE} PNG and editable SVG in {OUT}")
