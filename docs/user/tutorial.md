# User Tutorial

Welcome to the **spripe** tutorial! This guide will walk you through the end-to-end process of importing a raw animation and exporting a clean, normalized spritesheet.

## 1. Workspaces and Projects
When you launch spripe, you are working within a **Workspace**. 
- A Workspace holds multiple **Projects**. Think of a Project as a specific character or a specific level.
- To create a new Project, click `File > New Project` and give it a name (e.g., `Ninja`).
- You can load projects from anywhere on your computer using `File > Open Project...` which will read a `.spripe` project directory and optionally copy it into your workspace. Access your latest work via `File > Recent Projects`.

## 2. Managing Assets
Inside a Project, you create **Assets**. An Asset might be `Idle_Animation` or `Attack_Combo`.
- Right-click your Project in the left browser and select **New Asset**.
- You can also organize Assets into **Virtual Folders** to keep things tidy (e.g., `Punches`, `Kicks`).

## 3. Importing Animations
Animations are stored inside Assets. You can import animations from raw video files (`.mp4`) or PNG sequences.
- Right-click an Asset and select **Import Animation (Video)**.
- Spripe will automatically extract the frames into a `raw_output` folder.

## 4. The Painter and Onion Skinning
Once you have an animation loaded, select it in the browser to view it on the **Timeline**.
1. **Cleaning Frames:** Use the Brush, Lasso, or Magic Wand tools to mask out the background. You can undo/redo mistakes using `Ctrl+Z` and `Ctrl+Y`.
2. **Timeline Tagging:** Right click a frame in the timeline to **Mark to Fix**. It outlines the frame in red so you remember to come back to it.
3. **Pinning Keyframes:** Find a frame with a good pose, and click the **📌 Pin** button in the Timeline.
4. **Onion Skin:** As you move to the next frame, the pinned frame will overlay at a low opacity. This helps you ensure the character's feet and center of mass stay aligned across frames!

## 5. Normalizing
When you finish painting your mask or cropping a frame:
- Go to the **Asset Dashboard**.
- Select the animation and click **Normalize**. 
- Spripe will process the raw frames and generate a perfectly cropped sequence in `normalized_output`.

## 6. Exporting
Once your animations are normalized:
- To export your entire workspace setup, go to `File > Save Project As...` and save it as a compressed `.spripepack`. This is great for backups and sharing!
- Alternatively, right-click a specific Animation or Asset in the browser, select **Export**, and save it as a ZIP archive, or export individual `.gif` / PNG frames directly to your game engine folders. Godot engine users can also set their desired PNG compression level for optimized engine importing!

## 7. AI Prompt Generation
If you use generative AI to brainstorm character designs, use the **AI Generation Dialog** located in the toolbar. 
- You can create, edit, and organize prompt templates in the **Prompts Manager**. Templates are strictly categorized for Asset Design, Reference Creation, or Animation Creation.
- Use the **Copy Final Prompt** button to easily port the constructed query into Midjourney or Gemini.
