"""Gera os ícones PWA (maskable) do FinanPy a partir de um SVG programático.

Saídas:
  static/images/icons/icon-192.png         (any, 192×192)
  static/images/icons/icon-512.png         (any, 512×512)
  static/images/icons/icon-maskable-192.png (maskable, 192×192, safe zone 80%)
  static/images/icons/icon-maskable-512.png (maskable, 512×512, safe zone 80%)
  static/images/icons/apple-touch-icon.png (180×180, fundo opaco)
  static/images/icons/icon-96.png          (atalhos / shortcuts)
  static/images/icons/favicon-32.png
  static/images/icons/favicon-16.png

Identidade:
  Fundo:    gradiente diagonal primary-700 (#0369a1) → primary-500 (#0ea5e9)
  Glifo:    "F" em branco, peso 800, centralizado
  Borda:    arredondada (apenas para "any"; maskable é quadrado pleno)

Uso:
  python scripts/generate_pwa_icons.py

Reprodutível e versionável; sem dependências de design tools.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = REPO_ROOT / "static" / "images" / "icons"
ICON_DIR.mkdir(parents=True, exist_ok=True)

PRIMARY_700 = (3, 105, 161)   # #0369a1
PRIMARY_500 = (14, 165, 233)  # #0ea5e9
WHITE = (255, 255, 255)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Tenta carregar uma fonte bold do sistema; cai para default se nada."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _diagonal_gradient(size: int) -> Image.Image:
    """Cria um gradiente diagonal de PRIMARY_700 (top-left) para PRIMARY_500 (bottom-right)."""
    base = Image.new("RGB", (size, size), PRIMARY_700)
    pixels = base.load()
    # Diagonal: t = (x + y) / (2 * (size - 1))  ∈ [0, 1]
    denom = 2 * max(size - 1, 1)
    for y in range(size):
        for x in range(size):
            t = (x + y) / denom
            r = int(PRIMARY_700[0] + (PRIMARY_500[0] - PRIMARY_700[0]) * t)
            g = int(PRIMARY_700[1] + (PRIMARY_500[1] - PRIMARY_700[1]) * t)
            b = int(PRIMARY_700[2] + (PRIMARY_500[2] - PRIMARY_700[2]) * t)
            pixels[x, y] = (r, g, b)
    return base


def _rounded_mask(size: int, radius_ratio: float = 0.22) -> Image.Image:
    """Máscara alpha com cantos arredondados (estilo iOS/Android any-purpose)."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    radius = int(size * radius_ratio)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def _draw_glyph(canvas: Image.Image, glyph_size_ratio: float = 0.62) -> None:
    """Desenha o 'F' branco centralizado.

    glyph_size_ratio: tamanho da fonte como fração do canvas. Para maskable usar 0.5
    (safe zone 80% recomendada), para any-purpose 0.62 (mais visível em launcher).
    """
    size = canvas.size[0]
    font_size = int(size * glyph_size_ratio)
    font = _load_font(font_size)
    draw = ImageDraw.Draw(canvas)

    # Bounding box real do glifo (PIL>=10 usa textbbox)
    bbox = draw.textbbox((0, 0), "F", font=font)
    glyph_w = bbox[2] - bbox[0]
    glyph_h = bbox[3] - bbox[1]
    # Centraliza considerando o offset interno (bbox[0], bbox[1])
    x = (size - glyph_w) // 2 - bbox[0]
    y = (size - glyph_h) // 2 - bbox[1]
    draw.text((x, y), "F", fill=WHITE, font=font)


def make_any_icon(size: int) -> Image.Image:
    """Ícone com cantos arredondados (purpose=any)."""
    grad = _diagonal_gradient(size).convert("RGBA")
    mask = _rounded_mask(size, radius_ratio=0.22)
    grad.putalpha(mask)
    _draw_glyph(grad, glyph_size_ratio=0.62)
    return grad


def make_maskable_icon(size: int) -> Image.Image:
    """Ícone quadrado pleno (purpose=maskable). O glifo vive na safe zone (80%)."""
    grad = _diagonal_gradient(size).convert("RGBA")
    # Maskable não usa alpha — fica quadrado pleno; SO aplica a máscara
    _draw_glyph(grad, glyph_size_ratio=0.50)  # menor para caber no safe-zone 80%
    return grad


def make_apple_touch_icon(size: int = 180) -> Image.Image:
    """iOS espera fundo opaco e cantos retos (Safari aplica seu próprio raio)."""
    grad = _diagonal_gradient(size).convert("RGB")
    grad_rgba = grad.convert("RGBA")
    _draw_glyph(grad_rgba, glyph_size_ratio=0.62)
    return grad_rgba.convert("RGB")


def main() -> None:
    print(f"→ Gerando ícones em {ICON_DIR}")

    # Any-purpose (cantos arredondados)
    make_any_icon(192).save(ICON_DIR / "icon-192.png", optimize=True)
    make_any_icon(512).save(ICON_DIR / "icon-512.png", optimize=True)
    make_any_icon(96).save(ICON_DIR / "icon-96.png", optimize=True)

    # Maskable (quadrado pleno)
    make_maskable_icon(192).save(ICON_DIR / "icon-maskable-192.png", optimize=True)
    make_maskable_icon(512).save(ICON_DIR / "icon-maskable-512.png", optimize=True)

    # Apple touch icon (fundo opaco)
    make_apple_touch_icon(180).save(ICON_DIR / "apple-touch-icon.png", optimize=True)

    # Favicons
    make_any_icon(32).save(ICON_DIR / "favicon-32.png", optimize=True)
    make_any_icon(16).save(ICON_DIR / "favicon-16.png", optimize=True)

    print("✓ Ícones gerados:")
    for path in sorted(ICON_DIR.glob("*.png")):
        kb = path.stat().st_size / 1024
        print(f"  {path.name:32s} {kb:6.1f} KB")


if __name__ == "__main__":
    main()
