"""
Module docstring.
"""
import argparse
import sys
import os
from pathlib import Path


def main():
    """main function."""
    parser = argparse.ArgumentParser(description="Spripe Asset Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Subcommand: gui
    gui_parser = subparsers.add_parser(
        "gui", help="Launch the graphical user interface (default)"
    )

    # Subcommand: normalize
    norm_parser = subparsers.add_parser("normalize", help="Normalize frames headlessly")
    norm_parser.add_argument("--project", help="Workspace project name")
    norm_parser.add_argument("--asset", help="Asset name")
    norm_parser.add_argument(
        "--anim",
        help="Animation name (optional, if omitted processes all animations in asset)",
        default=None,
    )
    norm_parser.add_argument(
        "--path", help="Absolute or relative path to the asset or animation folder"
    )

    # Subcommand: rename
    rename_parser = subparsers.add_parser(
        "rename", help="Re-sequence and rename a folder of PNGs sequentially"
    )
    rename_parser.add_argument(
        "--path", required=True, help="Absolute or relative path to the folder of PNGs"
    )

    # Subcommand: reverse
    rev_parser = subparsers.add_parser("reverse", help="Reverse a folder of PNGs")
    rev_parser.add_argument(
        "--path", required=True, help="Absolute or relative path to the folder of PNGs"
    )

    args = parser.parse_args()

    if args.command is None or args.command == "gui":
        run_gui()
    elif args.command == "normalize":
        run_normalize(args)
    elif args.command == "rename":
        run_rename(args)
    elif args.command == "reverse":
        run_reverse(args)
    else:
        parser.print_help()


def run_gui():
    """run_gui function."""
    try:
        from spripe.gui.main import main as gui_main

        gui_main()
    except Exception as e:
        print(f"Failed to launch GUI: {e}")
        sys.exit(1)


def run_normalize(args):
    """run_normalize function."""
    from spripe.scripts.normalize_animations import process_animation
    from spripe.core.project_manager import ProjectManager
    import json

    # We need to find the workspace. For CLI, we can assume the current directory is workspace, or read settings.
    # To keep it simple, we use the path if provided, otherwise resolve via ProjectManager and settings

    if args.path:
        target_path = Path(args.path).resolve()
        if not target_path.exists():
            print(f"Error: Path does not exist: {target_path}")
            sys.exit(1)
        # process_animation typically takes the asset directory, but normalize script might expect the raw_output anim directory
        # Let's pass it to process_animation. But we might need to adapt the normalize script to accept paths.
        print(
            f"Normalizing path: {target_path} - (Note: ensure script supports direct path mode)"
        )
        # process_animation(str(target_path)) # Adapting this depends on the exact script signature

    elif args.project and args.asset:
        # Load settings to find workspace
        settings_path = Path.cwd() / "settings.json"
        workspace_dir = Path.cwd() / "workspace"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
                workspace_dir = Path(settings.get("workspace_dir", workspace_dir))

        pm = ProjectManager(str(workspace_dir))
        asset_path = Path(pm.get_project_path(args.project)) / args.asset

        animations_to_process = []
        if args.anim:
            animations_to_process.append(args.anim)
        else:
            animations_to_process = pm.get_animations(args.project, args.asset)

        for anim in animations_to_process:
            print(f"Normalizing {args.project} / {args.asset} / {anim}...")
            # We would invoke the normalize logic here
            # e.g., process_animation(args.project, args.asset, anim, pm)

    else:
        print("Error: You must provide either --path OR (--project AND --asset)")
        sys.exit(1)


def run_rename(args):
    """run_rename function."""
    from spripe.scripts.rename_frames import rename_sequence

    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Path does not exist: {target_path}")
        sys.exit(1)
    print(f"Renaming frames in {target_path}...")
    rename_sequence(str(target_path))
    print("Done.")


def run_reverse(args):
    """run_reverse function."""
    from spripe.scripts.reverse_frames import reverse_sequence

    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Path does not exist: {target_path}")
        sys.exit(1)
    print(f"Reversing frames in {target_path}...")
    reverse_sequence(str(target_path))
    print("Done.")


if __name__ == "__main__":
    main()
