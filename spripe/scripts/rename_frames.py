"""
Module docstring.
"""
import os
import glob
import argparse
import json


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

    # Read to_fix.json
    to_fix_path = os.path.join(directory, "to_fix.json")
    bad_frames = set()
    if os.path.exists(to_fix_path):
        try:
            with open(to_fix_path, "r", encoding="utf-8") as f:
                bad_frames = set(json.load(f))
        except Exception as e:
            print(f"Warning: Could not read {to_fix_path}: {e}")

    # Rename to temporary names first to avoid any collision issues
    # (e.g., if 0002.png is being renamed to 0001.png but 0001.png already exists)
    temp_files = []
    bad_temp_files = set()
    for i, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        temp_name = os.path.join(directory, f"__temp_{i:04d}.png")
        os.rename(filepath, temp_name)
        temp_files.append(temp_name)
        if filename in bad_frames:
            bad_temp_files.add(temp_name)

    # Now rename to final names
    new_bad_frames = []
    for i, temp_path in enumerate(temp_files):
        final_filename = f"{prefix}{i:04d}.png"
        final_name = os.path.join(directory, final_filename)
        os.rename(temp_path, final_name)
        if temp_path in bad_temp_files:
            new_bad_frames.append(final_filename)

    # Write new to_fix.json
    if new_bad_frames or os.path.exists(to_fix_path):
        try:
            with open(to_fix_path, "w", encoding="utf-8") as f:
                json.dump(new_bad_frames, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not write {to_fix_path}: {e}")

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
