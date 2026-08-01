# utils/workflow_parser.py
import json
import os
from collections import Counter

def parse_workflow_node_types(file_path):
    """
    Taraması yapılacak .json uzantılı ComfyUI workflow dosyasını okuyup,
    içindeki düğüm (node) tiplerini analiz eder ve frekanslarına göre sıralı döndürür.
    
    Args:
        file_path (str): JSON dosyasının mutlak yolu
        
    Returns:
        list of tuple: [(node_type, count), ...] şeklinde frekansa göre sıralı liste
    """
    if not file_path or not os.path.exists(file_path):
        return []

    node_types = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict):
            # 1. ComfyUI GUI formatı: {"nodes": [{"type": "KSampler", ...}], ...}
            if "nodes" in data and isinstance(data["nodes"], list):
                for node in data["nodes"]:
                    if isinstance(node, dict) and "type" in node:
                        node_types.append(node["type"])
            # 2. ComfyUI API formatı: {"3": {"class_type": "KSampler", ...}}
            else:
                for k, v in data.items():
                    if isinstance(v, dict) and "class_type" in v:
                        node_types.append(v["class_type"])
    except Exception as e:
        print(f"Error parsing workflow JSON {file_path}: {e}")

    # Düğüm frekanslarını hesapla ve en çok kullanılandan en aza doğru sırala
    counter = Counter(node_types)
    return counter.most_common()
