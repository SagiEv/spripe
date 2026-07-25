"""
Module docstring.
"""
import os
import glob
import argparse


def rename_sequence(directory, prefix=""):
    """rename_sequence function."""
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return

    # Get all png files and sort them.
    # Sorting alphabetically works since they are zero-padded (e.g., 0001.png)
    files = sorted(glob.glob(os.path.join(directory, "*.png")))

    if not files:
        print(f"No PNG files found in '{directory}'.")
        return

    print(f"Found {len(files)} files in '{directory}'. Renaming...")

    # Rename to temporary names first to avoid any collision issues
    # (e.g., if 0002.png is being renamed to 0001.png but 0001.png already exists)
    temp_files = []
    for i, filepath in enumerate(files):
        temp_name = os.path.join(directory, f"__temp_{i:04d}.png")
        os.rename(filepath, temp_name)
        temp_files.append(temp_name)

    # Now rename to final names
    for i, temp_path in enumerate(temp_files):
        final_name = os.path.join(directory, f"{prefix}{i:04d}.png")
        os.rename(temp_path, final_name)

    print(
        f"Successfully renamed {len(temp_files)} files in '{os.path.basename(directory)}'."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rename an image sequence to a continuous 0000.png, 0001.png... sequence."
    )
    parser.add_argument(
        "directory", nargs="?", help="The directory containing the PNG sequence"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all out_python_* directories in the current folder",
    )
    args = parser.parse_args()

    if args.all:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        anim_dirs = [
            d
            for d in glob.glob(os.path.join(base_dir, "raw_output", "out_python_*"))
            if os.path.isdir(d)
        ]
        if not anim_dirs:
            print("No out_python_* directories found.")
        for d in anim_dirs:
            rename_sequence(d)
    elif args.directory:
        rename_sequence(args.directory)
    else:
        print("Error: Please specify a directory or use the --all flag.")
        parser.print_help()
