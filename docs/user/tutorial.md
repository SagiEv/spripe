# User Tutorial

Welcome to the **spripe** tutorial! This guide will walk you through the end-to-end process of importing a raw animation and exporting a clean, normalized spritesheet.

## 1. Workspaces and Projects
When you launch spripe, you are working within a **Workspace**. 
- A Workspace holds multiple **Projects**. Think of a Project as a specific character or a specific level.
- To create a new Project, click `File > New Project` and give it a name (e.g., `Ninja`).

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
1. **Cleaning Frames:** Use the Brush, Lasso, or Magic Wand tools to mask out the background.
2. **Pinning Keyframes:** Find a frame with a good pose, and click the **📌 Pin** button in the Timeline.
3. **Onion Skin:** As you move to the next frame, the pinned frame will overlay at a low opacity. This helps you ensure the character's feet and center of mass stay aligned across frames!

## 5. Normalizing
When you finish painting your mask or cropping a frame:
- Go to the **Asset Dashboard**.
- Select the animation and click **Normalize**. 
- Spripe will process the raw frames and generate a perfectly cropped sequence in `normalized_output`.

## 6. Exporting
Once your animations are normalized:
- Right-click the Animation (or the whole Asset) in the browser.
- Select **Export**.
- You can export as a ZIP archive or a direct folder copy, ready to be dropped into Unity, Godot, or Unreal Engine.
