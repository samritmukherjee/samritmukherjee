"""
Pre-processes the source portrait image for optimal ASCII conversion.
Crops transparent borders, centers on head/shoulders, and enhances contrast & sharpness.
"""

import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps


def preprocess_portrait(
    input_path: Path,
    output_path: Path = None,
    contrast_factor: float = 1.35,
    sharpness_factor: float = 1.4,
    crop_height_ratio: float = 0.92,
) -> Image.Image:
    """Preprocess portrait image for ASCII generation."""
    if not input_path.exists():
        raise FileNotFoundError(f"Source image not found: {input_path}")

    img = Image.open(input_path).convert("RGBA")

    # Crop out transparent padding
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Focus on upper torso, chest, neck, and face
    width, height = img.size
    target_height = int(height * crop_height_ratio)
    img = img.crop((0, 0, width, target_height))

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast_factor)

    # Enhance sharpness
    enhancer_sharpness = ImageEnhance.Sharpness(img)
    img = enhancer_sharpness.enhance(sharpness_factor)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG")
        print(f"Preprocessed image saved to: {output_path}")

    return img


def main():
    root = Path(__file__).resolve().parent.parent
    source_photo = root / "assets" / "source-photo.png"
    output_photo = root / "assets" / "prepped-photo.png"

    if not source_photo.exists():
        print(f"Error: {source_photo} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {source_photo}...")
    img = preprocess_portrait(source_photo, output_photo)
    print(f"Done. Dimensions: {img.size}")


if __name__ == "__main__":
    main()
