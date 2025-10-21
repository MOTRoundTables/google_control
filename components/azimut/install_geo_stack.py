# install_geo_stack.py
# Minimal installer for required libraries (excluding pandas as requested)
import sys, subprocess

packages = [
    "geopandas",
    "shapely",
    "pyproj",
    "xlsxwriter"
]

def pip_install(pkg):
    print(f"Installing {pkg}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

if __name__ == "__main__":
    for p in packages:
        pip_install(p)
    print("All requested packages installed.")
