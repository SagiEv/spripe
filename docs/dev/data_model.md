# Data Model & Storage

Spripe is designed to be filesystem-first, meaning it avoids complex local databases in favor of transparent folder structures and simple JSON files. This ensures artists can easily browse, backup, and version control their work.

## Directory Structure
When a Workspace is created, it maintains a top-level `projects.json` file. Each Project within the workspace gets its own folder containing a `project.json` file.

Inside a Project, Assets are stored as directories. An Asset directory contains three critical subdirectories for processing animations:

```text
Workspace_Directory/
├── projects.json
├── Project_Ninja/
│   ├── project.json
│   └── Asset_Idle/
│       ├── videos/                  # Original imported .mp4 files
│       │   └── Idle.mp4
│       ├── raw_output/              # Extracted raw frames
│       │   └── out_python_Idle/
│       │       ├── 0000.png
│       │       └── 0001.png
│       └── normalized_output/       # Final cropped/processed frames
│           └── normalized_Idle/
│               ├── 0000.png
│               └── 0001.png
```

## Configuration Files

### `projects.json`
Maintained by the `WorkspaceRegistry`. It serves as an index mapping project names to their absolute disk paths. This allows importing projects from external directories into the workspace view.

### `project.json`
Maintained by the `ProjectMetadataService`. It stores project-specific UI configurations, primarily the `virtual_folders` dictionary.
- Virtual folders allow the `AssetBrowser` to visually group assets (e.g. putting `Asset_Idle` and `Asset_Run` under a `Movement` folder) without having to alter the physical directory structure on disk.
