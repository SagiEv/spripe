"""
Tests for export_gif.py
"""
import os
import tempfile
from PIL import Image
from spripe.scripts.export_gif import export_gif

def test_export_gif_transparency():
    """Test that export_gif correctly creates a GIF and preserves transparency."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create dummy PNG frames with transparency
        frame1_path = os.path.join(temp_dir, "frame1.png")
        frame2_path = os.path.join(temp_dir, "frame2.png")
        
        # 10x10 image: half transparent, half opaque
        img1 = Image.new("RGBA", (10, 10), (255, 0, 0, 0)) # Fully transparent red
        img1.paste((255, 0, 0, 255), (0, 0, 5, 10)) # Opaque red left half
        img1.save(frame1_path)
        
        img2 = Image.new("RGBA", (10, 10), (0, 255, 0, 0)) # Fully transparent green
        img2.paste((0, 255, 0, 255), (5, 0, 10, 10)) # Opaque green right half
        img2.save(frame2_path)
        
        output_gif = os.path.join(temp_dir, "output.gif")
        
        # Run export
        result = export_gif(temp_dir, output_gif, fps=10)
        assert result is True
        assert os.path.exists(output_gif)
        
        # Verify GIF properties
        with Image.open(output_gif) as gif:
            assert gif.n_frames == 2
            assert "transparency" in gif.info
            
            # Check frame 0
            gif.seek(0)
            img_rgba1 = gif.convert("RGBA")
            pixel1_opaque = img_rgba1.getpixel((0, 0))
            pixel1_transp = img_rgba1.getpixel((9, 0))
            
            assert pixel1_opaque[3] > 0 # Opaque part
            assert pixel1_transp[3] == 0 # Transparent part

            # Check frame 1
            gif.seek(1)
            img_rgba2 = gif.convert("RGBA")
            pixel2_transp = img_rgba2.getpixel((0, 0))
            pixel2_opaque = img_rgba2.getpixel((9, 0))
            
            assert pixel2_transp[3] == 0 # Transparent part
            assert pixel2_opaque[3] > 0 # Opaque part

def test_export_gif_no_frames():
    """Test that export_gif handles empty directories gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_gif = os.path.join(temp_dir, "output.gif")
        result = export_gif(temp_dir, output_gif, fps=10)
        assert result is False
        assert not os.path.exists(output_gif)
