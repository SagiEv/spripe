"""
Exports a sequence of PNG frames into a GIF.
"""

import os
import glob
import argparse
from PIL import Image


def export_gif(input_dir, output_path, fps=30, loop=0, progress_callback=None):
    """export_gif function."""

    def log(msg):
        """log method."""
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    frame_paths = sorted(glob.glob(os.path.join(input_dir, "*.png")))
    if not frame_paths:
        log(f"No PNG frames found in {input_dir}")
        return False

    log(f"Generating GIF from {len(frame_paths)} frames at {fps} fps...")

    frames = []
    try:
        for path in frame_paths:
            # We open and copy to ensure we keep it in memory
            # safely without holding file handles open forever
            with Image.open(path) as img:
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                # Convert to palette mode preserving transparency
                alpha = img.split()[3]
                img_p = img.convert("P", palette=Image.ADAPTIVE, colors=255)
                mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
                img_p.paste(255, mask)
                frames.append(img_p)

        duration = int(1000 / fps) if fps > 0 else 33

        frames[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=loop,
            disposal=2,  # Restore to background color for transparency
            transparency=255,
            optimize=False,
        )
        log(f"GIF exported successfully to {output_path}")
        return True
    except Exception as e:
        log(f"Error exporting GIF: {e}")
        return False


def main():
    """main function."""
    parser = argparse.ArgumentParser(description="Export animation to GIF.")
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing PNG frames",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        required=True,
        help="Output GIF file path",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Frames per second (default: 30)",
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="Loop count (0 for infinite, default: 0)",
    )
    args = parser.parse_args()

    export_gif(
        input_dir=args.input_dir,
        output_path=args.output_path,
        fps=args.fps,
        loop=args.loop,
    )


if __name__ == "__main__":
    main()
