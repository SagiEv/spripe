import cv2
import numpy as np
import argparse
import os
import shutil

def process_video(video_path, fps=12, use_ai=True, progress_callback=None):
    def log(msg):
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    # If video is in Asset/videos/name.mp4, then Asset is 2 levels up
    asset_dir = os.path.dirname(os.path.dirname(os.path.abspath(video_path)))
    if os.path.basename(os.path.dirname(os.path.abspath(video_path))) == "videos":
        # It's in the structured format
        out_dir = os.path.join(asset_dir, "raw_output", f"out_python_{video_name}")
    else:
        # Fallback to old behavior
        base_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(base_dir, "raw_output", f"out_python_{video_name}")
    
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        log(f"Error: Could not open video {video_path}")
        return

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps == 0:
        original_fps = 30 # fallback
        
    frame_interval = max(1, int(round(original_fps / fps)))
    
    frame_count = 0
    saved_count = 0
    
    log(f"Extracting frames at ~{fps} FPS...")
    
    if use_ai:
        log("Loading AI Background Removal Model (rembg)... This might take a moment.")
        from rembg import remove
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_interval == 0:
            if use_ai:
                # rembg.remove uses a neural network to perfectly isolate the character
                # and ignore gradients, shadows, and inconsistent background colors!
                bgra = remove(frame)
            else:
                # Old color-distance based removal
                bg_color = frame[0, 0].astype(np.int32)
                diff = np.abs(frame.astype(np.int32) - bg_color)
                max_diff = np.max(diff, axis=2)
                bg_mask = (max_diff <= 20).astype(np.uint8) * 255
                char_mask = cv2.bitwise_not(bg_mask)
                kernel = np.ones((2,2), np.uint8)
                mask_eroded = cv2.erode(char_mask, kernel, iterations=1)
                mask_smooth = cv2.GaussianBlur(mask_eroded, (3,3), 0)
                bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
                bgra[:, :, 3] = mask_smooth
            
            out_path = os.path.join(out_dir, f"{saved_count:04d}.png")
            cv2.imwrite(out_path, bgra)
            saved_count += 1
            
        frame_count += 1
        
    cap.release()
    log(f"Output saved to {out_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--fast", action="store_true", help="Use fast color keying instead of AI removal")
    args = parser.parse_args()
    
    process_video(args.video_path, args.fps, not args.fast)
