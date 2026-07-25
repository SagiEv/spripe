"""
Compresses normalized PNG animations using color quantization.
"""
import os
import glob
import argparse
import json
from PIL import Image


def compress_asset(
    asset_dir="",
    colors=256,
    overwrite=False,
    anim_name=None,
    progress_callback=None,
):
    """compress_asset function."""
    def log(msg):
        """log method."""
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    if anim_name is None:
        anim_name = []

    if asset_dir and os.path.exists(asset_dir):
        normalized_dir = os.path.join(asset_dir, "normalized_output")
        compressed_dir = os.path.join(asset_dir, "compressed_output")
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        normalized_dir = os.path.join(base_dir, "normalized_output")
        compressed_dir = os.path.join(base_dir, "compressed_output")

    anim_dirs = [
        d for d in glob.glob(os.path.join(normalized_dir, "normalized_*")) if os.path.isdir(d)
    ]

    if anim_name:
        anim_dirs = [
            d
            for d in anim_dirs
            if os.path.basename(d).removeprefix("normalized_") in anim_name
        ]
        overwrite = True

    if not anim_dirs:
        log("No normalized_* directories found to process.")
        return

    for anim_dir in anim_dirs:
        anim_name_str = os.path.basename(anim_dir).removeprefix("normalized_")
        out_dir = os.path.join(compressed_dir, f"compressed_{anim_name_str}")

        if os.path.exists(out_dir) and not overwrite:
            log(
                f"Skipping '{anim_name_str}': '{os.path.basename(out_dir)}' already exists. Use --overwrite to force."
            )
            continue

        os.makedirs(out_dir, exist_ok=True)
        frame_paths = sorted(glob.glob(os.path.join(anim_dir, "*.png")))
        
        if not frame_paths:
            log(f"Skipping '{anim_name_str}': No PNGs found.")
            continue
            
        log(f"Compressing '{anim_name_str}' to {colors} colors...")

        for frame_path in frame_paths:
            out_filename = os.path.basename(frame_path)
            out_path = os.path.join(out_dir, out_filename)
            
            try:
                with Image.open(frame_path) as img:
                    # Convert to RGBA if not already
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                        
                    # Quantize image (reduces colors to save space)
                    quantized = img.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
                    
                    # Save optimized
                    quantized.save(out_path, optimize=True, format="PNG")
            except Exception as e:
                log(f"Error compressing {frame_path}: {e}")

        # Save metadata
        meta_path = os.path.join(out_dir, "compression_meta.json")
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({"colors": colors}, f)
        except Exception as e:
            log(f"Error saving metadata: {e}")

    log("Compression complete!")


def main():
    """main function."""
    parser = argparse.ArgumentParser(
        description="Compress normalized sprite animations."
    )
    parser.add_argument(
        "--colors",
        type=int,
        default=256,
        help="Number of colors for quantization (1-256, default: 256)",
    )
    parser.add_argument(
        "--asset-dir",
        type=str,
        default="",
        help="Path to the specific asset directory to compress",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing compressed folders (default: skip)",
    )
    parser.add_argument(
        "--anim-name",
        type=str,
        nargs="*",
        default=[],
        help="Specific animation(s) to process. If provided, overwrites automatically.",
    )
    args = parser.parse_args()

    compress_asset(
        asset_dir=args.asset_dir,
        colors=args.colors,
        overwrite=args.overwrite,
        anim_name=args.anim_name,
    )


if __name__ == "__main__":
    main()
