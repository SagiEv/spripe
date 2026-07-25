# Core Services

The backend logic for project manipulation is housed inside `core/project_services.py`. To maintain backward compatibility with older components, a facade class named `ProjectManager` (in `core/project_manager.py`) wraps these services.

## WorkspaceRegistry
Responsible for finding and loading projects within the user's defined Workspace directory. It maintains the `projects.json` file which maps Project Names to their Absolute Paths.

## ProjectMetadataService
Reads and writes `project.json` files located inside individual project directories. This service handles the configuration of Virtual Folders (how assets are visually grouped in the UI) and Folder Templates.

## FileSystemService
Handles all disk operations including:
- Creating/Deleting projects and assets.
- Converting `.mp4` video files into raw `.png` frames.
- Re-routing legacy `os.path` strings into modern `pathlib.Path` objects.
- Exporting zipped archives of the normalized outputs.

## Config
A static class in `core/config.py` that houses all magic strings, directory names (`raw_output`, `normalized_output`), and filename prefixes (`out_python_`).
