"""Convert a PDF file into JPEG images, one file per page.

Usage:
    python pdf_to_jpeg.py input.pdf
    python pdf_to_jpeg.py input.pdf --output-dir output_images --dpi 200
"""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz
from PIL import Image


def room_filename_from_page(page_number: int) -> str:
    """Map page number to room-style filename.

    Pattern per 60 pages (4 floors x 15 rooms):
    - pages 1-15   -> 1-101 .. 1-115
    - pages 16-30  -> 1-201 .. 1-215
    - pages 31-45  -> 1-301 .. 1-315
    - pages 46-60  -> 1-401 .. 1-415
    - page 61+     -> 2-101 .. and so on
    """
    if page_number < 1:
        raise ValueError("page_number must be >= 1")

    rooms_per_floor = 15
    floors_per_building = 4
    pages_per_building = rooms_per_floor * floors_per_building

    zero_based = page_number - 1
    building = (zero_based // pages_per_building) + 1
    within_building = zero_based % pages_per_building

    floor = (within_building // rooms_per_floor) + 1
    room_index = (within_building % rooms_per_floor) + 1
    room_number = (floor * 100) + room_index

    return f"{building}-{room_number}"


def convert_pdf_to_jpeg(pdf_path: str | Path, output_dir: str | Path | None = None, dpi: int = 200, quality: int = 95) -> list[Path]:
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    if output_dir is None:
        output_path = pdf_file.with_name(f"{pdf_file.stem}_jpeg")
    else:
        output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    created_files: list[Path] = []

    with fitz.open(pdf_file) as document:
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

            room_name = room_filename_from_page(page_index + 1)
            output_file = output_path / f"{room_name}.jpg"
            image.save(output_file, format="JPEG", quality=quality, optimize=True)
            created_files.append(output_file)

    return created_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a PDF file into JPEG images.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output-dir", help="Directory for the JPEG files")
    parser.add_argument("--dpi", type=int, default=200, help="Render resolution in DPI (default: 200)")
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality from 1 to 100 (default: 95)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created_files = convert_pdf_to_jpeg(
        args.pdf_path,
        output_dir=args.output_dir,
        dpi=args.dpi,
        quality=args.quality,
    )

    for file_path in created_files:
        print(file_path)


if __name__ == "__main__":
    main()