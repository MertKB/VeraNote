# utils/workflow_parser.py
import json
import os
from collections import Counter

def parse_workflow_node_types(source):
    """
    ComfyUI workflow düğüm (node) tiplerini analiz eder ve frekanslarına göre sıralı döndürür.
    
    Args:
        source (str | dict): JSON dosyasının mutlak yolu, JSON metin dizgisi veya ayrıştırılmış dict.
        
    Returns:
        list of tuple: [(node_type, count), ...] şeklinde frekansa göre sıralı liste
    """
    if not source:
        return []

    data = None
    if isinstance(source, dict):
        data = source
    elif isinstance(source, str):
        if os.path.exists(source) and os.path.isfile(source):
            if source.lower().endswith('.png'):
                from utils.png_parser import extract_workflow_from_png, extract_prompt_from_png
                data = extract_workflow_from_png(source) or extract_prompt_from_png(source)
            else:
                try:
                    with open(source, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"Error parsing workflow file {source}: {e}")
                    return []
        else:
            try:
                data = json.loads(source)
            except Exception:
                return []

    if not isinstance(data, dict):
        return []

    node_types = []
    try:
        # 1. ComfyUI GUI formatı: {"nodes": [{"type": "KSampler", ...}], ...}
        if "nodes" in data and isinstance(data["nodes"], list):
            for node in data["nodes"]:
                if isinstance(node, dict) and "type" in node and node["type"]:
                    node_types.append(str(node["type"]))
        # 2. ComfyUI API formatı: {"3": {"class_type": "KSampler", ...}}
        else:
            for k, v in data.items():
                if isinstance(v, dict) and "class_type" in v and v["class_type"]:
                    node_types.append(str(v["class_type"]))
    except Exception as e:
        print(f"Error analyzing workflow node types: {e}")

    counter = Counter(node_types)
    return counter.most_common()
