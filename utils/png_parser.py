# utils/png_parser.py
import json
import os
from PIL import Image

def _safe_json_loads(val):
    if not val:
        return None
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return None
    return None

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
            info = getattr(img, "info", {}) or {}
            workflow_str = info.get("workflow")
            if not workflow_str and hasattr(img, "text"):
                workflow_str = img.text.get("workflow")
            return _safe_json_loads(workflow_str)
    except Exception as e:
        print(f"Error extracting workflow from PNG metadata {image_path}: {e}")
        return None

def extract_prompt_from_png(image_path: str) -> dict | None:
    """
    PNG dosyasından ComfyUI 'prompt' yürütme grafiği (API execution graph) metadatasını ayıklar.
    """
    if not image_path or not os.path.exists(image_path):
        return None

    try:
        with Image.open(image_path) as img:
            info = getattr(img, "info", {}) or {}
            prompt_data = info.get("prompt")
            if not prompt_data and hasattr(img, "text"):
                prompt_data = img.text.get("prompt")
            return _safe_json_loads(prompt_data)
    except Exception as e:
        print(f"Error extracting prompt from PNG metadata {image_path}: {e}")
        return None

def extract_comfyui_metadata_from_png(image_path: str) -> dict:
    """
    PNG dosyasından ComfyUI workflow ve prompt chunk'larını okuyup
    pozitif/negatif promptları, model adlarını ve sampler ayarlarını ayıklar.
    
    Returns:
        dict: {
            'workflow': dict | None,
            'prompt': dict | None,
            'positive_prompt': str,
            'negative_prompt': str,
            'models': list of str,
            'sampler_params': dict,
            'formatted_summary': str
        }
    """
    res = {
        'workflow': None,
        'prompt': None,
        'positive_prompt': '',
        'negative_prompt': '',
        'models': [],
        'sampler_params': {},
        'formatted_summary': ''
    }
    if not image_path or not os.path.exists(image_path):
        return res

    try:
        with Image.open(image_path) as img:
            info = getattr(img, "info", {}) or {}
            text_chunks = getattr(img, "text", {}) or {}
            
            w_raw = info.get("workflow") or text_chunks.get("workflow")
            p_raw = info.get("prompt") or text_chunks.get("prompt")
            
            res['workflow'] = _safe_json_loads(w_raw)
            res['prompt'] = _safe_json_loads(p_raw)
    except Exception as e:
        print(f"Error reading PNG chunks {image_path}: {e}")
        return res

    # Prompt graph analysis
    prompt_graph = res['prompt']
    if isinstance(prompt_graph, dict):
        pos_id = None
        neg_id = None
        
        # 1. Search for sampler node to find exact positive/negative links
        for node_id, node_data in prompt_graph.items():
            if not isinstance(node_data, dict):
                continue
            class_type = node_data.get('class_type', '')
            inputs = node_data.get('inputs', {})
            if not isinstance(inputs, dict):
                continue
                
            if 'KSampler' in class_type or 'Sampler' in class_type:
                # Capture sampler params
                for k in ['seed', 'steps', 'cfg', 'sampler_name', 'scheduler', 'denoise']:
                    if k in inputs and k not in res['sampler_params']:
                        res['sampler_params'][k] = inputs[k]
                
                pos_ref = inputs.get('positive')
                if isinstance(pos_ref, list) and len(pos_ref) > 0:
                    pos_id = str(pos_ref[0])
                neg_ref = inputs.get('negative')
                if isinstance(neg_ref, list) and len(neg_ref) > 0:
                    neg_id = str(neg_ref[0])

            # Checkpoint & LoRA models
            for ckpt_key in ['ckpt_name', 'unet_name', 'model_name']:
                if ckpt_key in inputs and inputs[ckpt_key]:
                    val = str(inputs[ckpt_key])
                    if val not in res['models']:
                        res['models'].append(val)
            for lora_key in ['lora_name']:
                if lora_key in inputs and inputs[lora_key]:
                    val = f"LoRA: {inputs[lora_key]}"
                    if val not in res['models']:
                        res['models'].append(val)

        # Helper to find text in node or its ancestors
        def find_text_for_node(target_id, visited=None):
            if visited is None:
                visited = set()
            if not target_id or target_id in visited or target_id not in prompt_graph:
                return ""
            visited.add(target_id)
            n_data = prompt_graph[target_id]
            if not isinstance(n_data, dict):
                return ""
            inp = n_data.get('inputs', {})
            if isinstance(inp, dict):
                if 'text' in inp and isinstance(inp['text'], str) and inp['text'].strip():
                    return inp['text'].strip()
                # If conditioning passed through a conditioning combiner or LoRA
                for k, v in inp.items():
                    if isinstance(v, list) and len(v) > 0:
                        txt = find_text_for_node(str(v[0]), visited)
                        if txt:
                            return txt
            return ""

        if pos_id:
            res['positive_prompt'] = find_text_for_node(pos_id)
        if neg_id:
            res['negative_prompt'] = find_text_for_node(neg_id)

        # Fallback: if positive prompt not found by link, check any CLIPTextEncode node
        if not res['positive_prompt']:
            text_nodes = []
            for n_id, n_data in prompt_graph.items():
                if isinstance(n_data, dict) and 'CLIPText' in n_data.get('class_type', ''):
                    inp = n_data.get('inputs', {})
                    if isinstance(inp, dict) and isinstance(inp.get('text'), str) and inp['text'].strip():
                        text_nodes.append(inp['text'].strip())
            if text_nodes:
                res['positive_prompt'] = text_nodes[0]
                if len(text_nodes) > 1 and not res['negative_prompt']:
                    res['negative_prompt'] = text_nodes[1]

    # Formatted Summary string
    parts = []
    if res['positive_prompt']:
        parts.append(f"Prompt: {res['positive_prompt']}")
    if res['negative_prompt']:
        parts.append(f"Negative: {res['negative_prompt']}")
    if res['sampler_params']:
        params_str = ", ".join(f"{k}: {v}" for k, v in res['sampler_params'].items())
        parts.append(f"Settings: {params_str}")
    if res['models']:
        parts.append(f"Models: {', '.join(res['models'])}")
        
    res['formatted_summary'] = "\n\n".join(parts)
    return res
