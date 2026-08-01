# utils/png_parser.py
import json
import os
from PIL import Image

def extract_workflow_from_png(image_path: str) -> dict | None:
    """
    Yerel olarak PNG dosyasından ComfyUI iş akışı (workflow) metadatasını ayıklar.
    
    Args:
        image_path (str): PNG dosyasının mutlak yolu
        
    Returns:
        dict | None: Ayıklanan workflow sözlüğü veya bulunamazsa None
    """
    if not image_path or not os.path.exists(image_path):
        return None

    try:
        with Image.open(image_path) as img:
            # Metadata img.info içindedir
            info = img.info
            if not info:
                return None
                
            workflow_str = info.get("workflow")
            if not workflow_str:
                return None
                
            # Eğer veri zaten bir dict ise (Pillow bazı formatlarda otomatik ayrıştırabilir) direkt dönebiliriz
            if isinstance(workflow_str, dict):
                return workflow_str
                
            # String ise JSON olarak yükleyelim
            if isinstance(workflow_str, str):
                return json.loads(workflow_str)
                
    except Exception as e:
        print(f"Error extracting workflow from PNG metadata {image_path}: {e}")
        
    return None
