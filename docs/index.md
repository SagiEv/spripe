# Welcome to spripe

**spripe** is a powerful pipeline tool designed specifically for managing, processing, and exporting 2D sprite animations. Whether you're working with video captures or raw PNG sequences, spripe helps you normalize frames, pin keyframes for onion-skinning, and effortlessly export your assets to your game engine.

## Getting Started

- **For Artists & Animators:** Check out the [User Tutorial](user/tutorial.md) to learn how to create projects, import assets, draw masks, and export clean spritesheets.
- **For Developers:** If you're looking to contribute to the codebase or understand how Spripe is built under the hood, start with the [Architecture Overview](dev/architecture.md).

## Core Features
- **Project Management:** Organize characters, stages, and UI elements into distinct Workspaces and Projects.
- **Animation Normalization:** Use Python-backed computer vision tools (GrabCut) to perfectly crop and align sprite animations.
- **Timeline & Onion Skinning:** Pin keyframes to serve as an onion skin while cleaning up neighboring frames in an animation sequence.
- **Non-Destructive Workflows:** Original video and raw frames are preserved alongside normalized outputs.
