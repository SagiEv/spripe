"""
Module docstring.
"""
import cv2
import numpy as np
import os
import glob
import argparse


def get_bounding_box(image):
    """Returns the bounding box (x, y, w, h) of the non-transparent pixels."""
    if image is None or image.shape[2] != 4:
        return 0, 0, 0, 0
    alpha = image[:, :, 3]
    coords = cv2.findNonZero(alpha)
    if coords is None:
        return 0, 0, 0, 0
    x, y, w, h = cv2.boundingRect(coords)
    return x, y, w, h


def normalize_asset(
    asset_dir="",
    width=1920,
    height=1080,
    char_height=800,
    bottom_padding=100,
    overwrite=False,
    anim_name=None,
    progress_callback=None,
):
    """normalize_asset function."""
    def log(msg):
        """log method."""
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    if anim_name is None:
        anim_name = []

    if asset_dir and os.path.exists(asset_dir):
        raw_dir = os.path.join(asset_dir, "raw_output")
        normalized_dir = os.path.join(asset_dir, "normalized_output")
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        raw_dir = os.path.join(base_dir, "raw_output")
        normalized_dir = os.path.join(base_dir, "normalized_output")

    anim_dirs = [
        d for d in glob.glob(os.path.join(raw_dir, "out_python_*")) if os.path.isdir(d)
    ]

    if anim_name:
        anim_dirs = [
            d
            for d in anim_dirs
            if os.path.basename(d).removeprefix("out_python_") in anim_name
        ]
        overwrite = True  # Always overwrite if specifically requested

    if not anim_dirs:
        log("No out_python_* directories found to process.")
        return

    # Set anchor to bottom-center of the new 16:9 canvas
    target_anchor_x = width // 2
    target_anchor_y = height - bottom_padding

    for anim_dir in anim_dirs:
        anim_name_str = os.path.basename(anim_dir).removeprefix("out_python_")
        out_dir = os.path.join(normalized_dir, f"normalized_{anim_name_str}")

        if os.path.exists(out_dir) and not overwrite:
            log(
                f"Skipping '{anim_name_str}': '{os.path.basename(out_dir)}' already exists. Use --overwrite to force."
            )
            continue

        first_frame_path = os.path.join(anim_dir, "0000.png")
        if not os.path.exists(first_frame_path):
            log(f"Skipping '{anim_name_str}': No 0000.png found.")
            continue

        first_frame = cv2.imread(first_frame_path, cv2.IMREAD_UNCHANGED)
        if first_frame is None or first_frame.shape[2] != 4:
            log(
                f"Skipping '{anim_name_str}': Invalid image format in 0000.png (must be BGRA)."
            )
            continue

        x, y, w, h = get_bounding_box(first_frame)
        if h == 0:
            log(f"Skipping '{anim_name_str}': Empty first frame (no visible pixels).")
            continue

        # Calculate scale factor relative to the target height per animation
        scale_factor = char_height / h
        log(f"Processing '{anim_name_str}' with scale factor: {scale_factor:.4f}")

        # Calculate scaled dimensions and position based on THIS animation's first frame
        scaled_x = x * scale_factor
        scaled_y = y * scale_factor
        scaled_w = w * scale_factor
        scaled_h = h * scale_factor

        # Calculate the top-left offset required to place the bottom-center of the character
        # at the target anchor coordinates.
        offset_x = int(target_anchor_x - (scaled_x + scaled_w / 2.0))
        offset_y = int(target_anchor_y - (scaled_y + scaled_h))

        os.makedirs(out_dir, exist_ok=True)
        frame_paths = sorted(glob.glob(os.path.join(anim_dir, "*.png")))

        for frame_path in frame_paths:
            frame = cv2.imread(frame_path, cv2.IMREAD_UNCHANGED)
            if frame is None:
                continue

            new_w = int(round(frame.shape[1] * scale_factor))
            new_h = int(round(frame.shape[0] * scale_factor))

            # Use appropriate interpolation based on whether we are shrinking or enlarging
            interpolation = cv2.INTER_AREA if scale_factor < 1.0 else cv2.INTER_CUBIC
            resized_frame = cv2.resize(
                frame, (new_w, new_h), interpolation=interpolation
            )

            # Create a blank 16:9 canvas (all transparent)
            canvas = np.zeros((height, width, 4), dtype=np.uint8)

            # Calculate paste boundaries to prevent out-of-bounds errors
            paste_x1 = max(0, offset_x)
            paste_y1 = max(0, offset_y)
            paste_x2 = min(width, offset_x + new_w)
            paste_y2 = min(height, offset_y + new_h)

            src_x1 = paste_x1 - offset_x
            src_y1 = paste_y1 - offset_y
            src_x2 = src_x1 + (paste_x2 - paste_x1)
            src_y2 = src_y1 + (paste_y2 - paste_y1)

            if paste_x1 < paste_x2 and paste_y1 < paste_y2:
                # Direct copy since background is completely transparent
                canvas[paste_y1:paste_y2, paste_x1:paste_x2] = resized_frame[
                    src_y1:src_y2, src_x1:src_x2
                ]

            out_filename = os.path.basename(frame_path)
            cv2.imwrite(os.path.join(out_dir, out_filename), canvas)

    log("Normalization complete!")


def main():
    """main function."""
    parser = argparse.ArgumentParser(
        description="Normalize scale and position of sprite animations."
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1920,
        help="Output canvas width (16:9 ratio, default: 1920)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1080,
        help="Output canvas height (16:9 ratio, default: 1080)",
    )
    parser.add_argument(
        "--char-height",
        type=int,
        default=800,
        help="Target character height in pixels (default: 800)",
    )
    parser.add_argument(
        "--bottom-padding",
        type=int,
        default=100,
        help="Padding from the bottom of the canvas (default: 100)",
    )
    parser.add_argument(
        "--asset-dir",
        type=str,
        default="",
        help="Path to the specific asset directory to normalize",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing normalized folders (default: skip)",
    )
    parser.add_argument(
        "--anim-name",
        type=str,
        nargs="*",
        default=[],
        help="Specific animation(s) to process. If provided, overwrites automatically.",
    )
    args = parser.parse_args()

    normalize_asset(
        asset_dir=args.asset_dir,
        width=args.width,
        height=args.height,
        char_height=args.char_height,
        bottom_padding=args.bottom_padding,
        overwrite=args.overwrite,
        anim_name=args.anim_name,
    )


if __name__ == "__main__":
    main()
