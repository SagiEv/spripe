"""
Module docstring.
"""
import os
import glob
import argparse


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

    # Rename to temporary names first to avoid any collision issues
    # We reverse the order of the files array so the last frame gets the lowest index
    temp_files = []
    reversed_files = list(reversed(files))

    for i, filepath in enumerate(reversed_files):
        temp_name = os.path.join(directory, f"__temp_{i:04d}.png")
        os.rename(filepath, temp_name)
        temp_files.append(temp_name)

    # Now rename to final names
    for i, temp_path in enumerate(temp_files):
        final_name = os.path.join(directory, f"{prefix}{i:04d}.png")
        os.rename(temp_path, final_name)

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
