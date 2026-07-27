"""
Module docstring.
"""

import os
import glob
import argparse
import json


def reverse_sequence(directory, prefix=""):
    """reverse_sequence function."""
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return

    # Get all png files and sort them.
    # Sorting alphabetically works since they are zero-padded (e.g., 0001.png)
    files = sorted(glob.glob(os.path.join(directory, "*.png")))

    if not files:
        print(f"No PNG files found in '{directory}'.")
        return

    print(f"Found {len(files)} files in '{directory}'. Reversing order...")

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
    # We reverse the order of the files array so the last frame gets the lowest index
    temp_files = []
    bad_temp_files = set()
    reversed_files = list(reversed(files))

    for i, filepath in enumerate(reversed_files):
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
        f"Successfully reversed order for {len(temp_files)} files in '{os.path.basename(directory)}'."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reverse the order of an image sequence."
    )
    parser.add_argument("directory", help="The directory containing the PNG sequence")
    args = parser.parse_args()

    reverse_sequence(args.directory)
