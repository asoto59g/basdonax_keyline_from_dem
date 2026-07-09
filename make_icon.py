from pathlib import Path
import cairosvg

BASE = Path(__file__).resolve().parent

svg_path = BASE / "icon.svg"
png_path = BASE / "icon.png"

if not svg_path.exists():
    raise FileNotFoundError(f"No existe el archivo SVG: {svg_path}")

cairosvg.svg2png(
    url=str(svg_path),
    write_to=str(png_path),
    output_width=256,
    output_height=256
)

print(f"icon.png generado correctamente: {png_path}")