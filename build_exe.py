import os
import subprocess
import sys

def main():
    print("Building Spripe executable with PyInstaller...")
    
    # We include rembg as a hidden import as requested
    command = [
        "pyinstaller",
        "--name", "Spripe",
        "--windowed",
        "--hidden-import", "rembg",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--add-data", "spripe/gui/icons;spripe/gui/icons",
        "--add-data", "spripe/gui/styles.qss;spripe/gui",
        "spripe/__main__.py"
    ]
    
    try:
        subprocess.run(command, check=True)
        print("\nBuild successful! Executable is located in the 'dist/Spripe' directory.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()
