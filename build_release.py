from pathlib import Path
import zipfile
import py_compile
import shutil

PLUGIN_DIR = Path("basdonax_keyline_from_dem")
ZIP_NAME = Path("basdonax_keyline_from_dem.zip")

required = [
    "__init__.py",
    "metadata.txt",
    "plugin.py",
    "provider.py",
    "algorithm_keyline_from_dem.py",
]

def clean_cache(root: Path):
    for p in root.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    for p in root.rglob("*.pyc"):
        try:
            p.unlink()
        except Exception:
            pass

def validate_files(plugin_dir: Path):
    if not plugin_dir.exists():
        raise SystemExit(f"No existe carpeta plugin: {plugin_dir.resolve()}")

    missing = [f for f in required if not (plugin_dir / f).exists()]
    if missing:
        raise SystemExit(f"Faltan archivos requeridos: {missing}")

def compile_check(plugin_dir: Path):
    for py in plugin_dir.rglob("*.py"):
        py_compile.compile(str(py), doraise=True)
    print("OK sintaxis Python")

def build_zip(plugin_dir: Path, zip_name: Path):
    if zip_name.exists():
        zip_name.unlink()

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in plugin_dir.rglob("*"):
            if p.is_dir():
                continue
            if "__pycache__" in p.parts:
                continue
            if p.suffix == ".pyc":
                continue
            zf.write(p, p.as_posix())

    print(f"ZIP generado: {zip_name.resolve()}")

if __name__ == "__main__":
    validate_files(PLUGIN_DIR)
    clean_cache(PLUGIN_DIR)
    compile_check(PLUGIN_DIR)
    build_zip(PLUGIN_DIR, ZIP_NAME)