# services/workflow_generator.py
"""
Service layer for ComfyUI workflow generation, parameter injection,
multi-LoRA chaining, resolution management, and metadata embedding into PNG/JSON files.
Supports both Text-to-Image (Txt2Img via EmptyLatentImage) and Image-to-Image (Img2Img via LoadImage).
"""

import copy
import json
import os
import random
import sys
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


def get_templates_dir() -> str:
    """Returns the absolute path to the templates directory."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = os.path.join(sys._MEIPASS, 'templates')
        if os.path.isdir(base_dir):
            return base_dir
    # Workspace root
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    if os.path.isdir(base_dir):
        return base_dir
    return os.path.abspath('templates')


def load_template(template_name_or_path: str = "default_workflow.json") -> dict:
    """
    Loads a ComfyUI workflow JSON template from disk.
    Falls back to built-in template structure if not found.
    """
    path = template_name_or_path
    if not os.path.isabs(path):
        candidate = os.path.join(get_templates_dir(), template_name_or_path)
        if os.path.exists(candidate):
            path = candidate

    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading template {path}: {e}")

    # Fallback minimal template structure
    return {
        "workflow": {
            "last_node_id": 9,
            "last_link_id": 13,
            "nodes": [],
            "links": [],
            "extra": {},
            "version": 0.4
        },
        "prompt": {}
    }


def generate_workflow(params: dict, template_data: dict = None) -> tuple[dict, dict]:
    """
    Injects user parameters into ComfyUI workflow (UI) and prompt (API) structures.
    Supports single or multiple LoRAs, custom width/height, and Txt2Img / Img2Img modes.

    Parameters in params:
        - mode (str, optional): 'txt2img' or 'img2img' (inferred if omitted)
        - image_path (str, optional): Filename or path for input image
        - width (int, optional): Image width for EmptyLatentImage (default: 1024)
        - height (int, optional): Image height for EmptyLatentImage (default: 1024)
        - batch_size (int, optional): Batch size (default: 1)
        - positive_prompt (str): Text for positive CLIPTextEncode
        - negative_prompt (str): Text for negative CLIPTextEncode
        - checkpoint (str): Model ckpt_name for CheckpointLoaderSimple
        - loras (list[dict], optional): List of dicts: [{'name': '...', 'strength_model': 1.0, 'strength_clip': 1.0}]
        - lora_name (str, optional): Backward-compatible single LoRA name
        - lora_strength_model (float, optional): Backward-compatible single LoRA model strength
        - lora_strength_clip (float, optional): Backward-compatible single LoRA clip strength
        - seed (int): KSampler seed (default: random)
        - steps (int): KSampler steps (default: 20)
        - cfg (float): KSampler CFG scale (default: 7.0)
        - denoise (float): KSampler denoise ratio (default: 1.0 for txt2img, 0.75 for img2img)
        - sampler_name (str): KSampler sampler_name (default: "euler")
        - scheduler (str): KSampler scheduler (default: "normal")

    Returns:
        tuple[dict, dict]: (workflow_dict, prompt_dict)
    """
    if template_data is None:
        template_data = load_template()

    workflow = copy.deepcopy(template_data.get("workflow", {}))
    prompt = copy.deepcopy(template_data.get("prompt", {}))

    # Determine mode & image
    raw_img = params.get("image_path") or params.get("image_name") or ""
    has_image = bool(raw_img and os.path.exists(raw_img))
    mode = params.get("mode")
    if not mode:
        mode = "img2img" if has_image else "txt2img"

    image_name = os.path.basename(raw_img) if raw_img else "input.png"
    width = int(params.get("width", 1024))
    height = int(params.get("height", 1024))
    batch_size = int(params.get("batch_size", 1))

    pos_prompt = str(params.get("positive_prompt") or "")
    neg_prompt = str(params.get("negative_prompt") or "")
    checkpoint = str(params.get("checkpoint") or "v1-5-pruned-emaonly.safetensors")

    # Collect LoRAs (supporting both list of loras and legacy single lora)
    no_lora_vals = (
        "none", "", "yok", "secilmedi", "seçilmedi",
        "lora eklenmedi (yalnızca model)", "lora eklenmedi (yalnizca model)",
        "no lora added (model only)", "no lora added (only base model used)",
    )
    loras = []
    if "loras" in params and isinstance(params["loras"], list):
        for item in params["loras"]:
            if isinstance(item, dict):
                l_name = str(item.get("name") or "").strip()
                if l_name and l_name.lower() not in no_lora_vals:
                    loras.append({
                        "name": l_name,
                        "strength_model": float(item.get("strength_model", 1.0)),
                        "strength_clip": float(item.get("strength_clip", 1.0))
                    })
    elif params.get("lora_name"):
        l_name = str(params.get("lora_name")).strip()
        if l_name and l_name.lower() not in no_lora_vals:
            loras.append({
                "name": l_name,
                "strength_model": float(params.get("lora_strength_model", 1.0)),
                "strength_clip": float(params.get("lora_strength_clip", 1.0))
            })

    seed = params.get("seed")
    if seed is None or seed == -1:
        seed = random.randint(100000000000, 999999999999)
    else:
        seed = int(seed)

    steps = int(params.get("steps", 20))
    cfg = float(params.get("cfg", 7.0))
    default_denoise = 0.75 if mode == "img2img" else 1.0
    denoise = float(params.get("denoise", default_denoise))
    sampler_name = str(params.get("sampler_name") or "euler")
    scheduler = str(params.get("scheduler") or "normal")

    # 1. Update API prompt graph
    if isinstance(prompt, dict):
        # Locate CheckpointLoaderSimple
        ckpt_id = None
        for n_id, n_data in prompt.items():
            if isinstance(n_data, dict) and n_data.get("class_type") == "CheckpointLoaderSimple":
                ckpt_id = str(n_id)
                n_data.setdefault("inputs", {})["ckpt_name"] = checkpoint
                break
        if not ckpt_id:
            ckpt_id = "4"
            prompt[ckpt_id] = {
                "inputs": {"ckpt_name": checkpoint},
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"}
            }

        # Remove existing template LoRALoader nodes from prompt to cleanly rebuild chain
        existing_lora_ids = [n_id for n_id, n_data in prompt.items() if isinstance(n_data, dict) and n_data.get("class_type") == "LoraLoader"]
        for lid in existing_lora_ids:
            del prompt[lid]

        # Chain LoRA loaders
        current_model = [ckpt_id, 0]
        current_clip = [ckpt_id, 1]

        for i, lora_info in enumerate(loras):
            lora_node_id = str(100 + i) if i > 0 else "7"
            prompt[lora_node_id] = {
                "inputs": {
                    "lora_name": lora_info["name"],
                    "strength_model": lora_info["strength_model"],
                    "strength_clip": lora_info["strength_clip"],
                    "model": current_model,
                    "clip": current_clip
                },
                "class_type": "LoraLoader",
                "_meta": {"title": f"Load LoRA ({lora_info['name']})"}
            }
            current_model = [lora_node_id, 0]
            current_clip = [lora_node_id, 1]

        # Handle Latent Image: Txt2Img (EmptyLatentImage) vs Img2Img (LoadImage + VAEEncode)
        latent_source = None
        if mode == "txt2img":
            # Remove LoadImage and VAEEncode from prompt
            prompt.pop("1", None)
            prompt.pop("2", None)

            empty_latent_id = "10"
            prompt[empty_latent_id] = {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": batch_size
                },
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"}
            }
            latent_source = [empty_latent_id, 0]
        else:
            # Img2Img
            prompt.pop("10", None)
            prompt["1"] = {
                "inputs": {
                    "image": image_name,
                    "upload": "image"
                },
                "class_type": "LoadImage",
                "_meta": {"title": "Load Image"}
            }
            prompt["2"] = {
                "inputs": {
                    "pixels": ["1", 0],
                    "vae": [ckpt_id, 2]
                },
                "class_type": "VAEEncode",
                "_meta": {"title": "VAE Encode"}
            }
            latent_source = ["2", 0]

        # Connect positive & negative prompts
        pos_id = None
        neg_id = None
        for n_id, n_data in prompt.items():
            if isinstance(n_data, dict) and "KSampler" in n_data.get("class_type", ""):
                inputs = n_data.get("inputs", {})
                if isinstance(inputs.get("positive"), list) and inputs["positive"]:
                    pos_id = str(inputs["positive"][0])
                if isinstance(inputs.get("negative"), list) and inputs["negative"]:
                    neg_id = str(inputs["negative"][0])
                break

        if not pos_id:
            pos_id = "5"
        if not neg_id:
            neg_id = "6"

        prompt[pos_id] = {
            "inputs": {
                "text": pos_prompt,
                "clip": current_clip
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Prompt)"}
        }
        prompt[neg_id] = {
            "inputs": {
                "text": neg_prompt,
                "clip": current_clip
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Negative)"}
        }

        # KSampler
        prompt["3"] = {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": denoise,
                "model": current_model,
                "positive": [pos_id, 0],
                "negative": [neg_id, 0],
                "latent_image": latent_source
            },
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"}
        }

        # VAEDecode & SaveImage
        prompt["8"] = {
            "inputs": {
                "samples": ["3", 0],
                "vae": [ckpt_id, 2]
            },
            "class_type": "VAEDecode",
            "_meta": {"title": "VAE Decode"}
        }
        prompt["9"] = {
            "inputs": {
                "filename_prefix": "VeraNote",
                "images": ["8", 0]
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"}
        }

    # 2. Rebuild UI workflow graph (nodes and links) with 100% link integrity
    if isinstance(workflow, dict):
        updated_nodes = []
        links = []
        link_id_counter = 0

        def create_link(src_node, src_slot, dst_node, dst_slot, link_type):
            nonlocal link_id_counter
            link_id_counter += 1
            links.append([link_id_counter, src_node["id"], src_slot, dst_node["id"], dst_slot, link_type])
            # Ensure source output slots exist
            while len(src_node.setdefault("outputs", [])) <= src_slot:
                src_node["outputs"].append({"name": link_type, "type": link_type, "links": []})
            if src_node["outputs"][src_slot].get("links") is None:
                src_node["outputs"][src_slot]["links"] = []
            src_node["outputs"][src_slot]["links"].append(link_id_counter)
            # Ensure target input slots exist
            while len(dst_node.setdefault("inputs", [])) <= dst_slot:
                dst_node["inputs"].append({"name": "", "type": link_type, "link": None})
            dst_node["inputs"][dst_slot]["link"] = link_id_counter
            return link_id_counter

        # 1. Checkpoint Node
        node_ckpt = {
            "id": 4,
            "type": "CheckpointLoaderSimple",
            "pos": [50, 100],
            "size": [315, 98],
            "flags": {},
            "order": 1,
            "mode": 0,
            "inputs": [],
            "outputs": [
                {"name": "MODEL", "type": "MODEL", "links": [], "shape": 3, "slot_index": 0},
                {"name": "CLIP", "type": "CLIP", "links": [], "shape": 3, "slot_index": 1},
                {"name": "VAE", "type": "VAE", "links": [], "shape": 3, "slot_index": 2}
            ],
            "properties": {"Node name for S&R": "CheckpointLoaderSimple"},
            "widgets_values": [checkpoint]
        }
        updated_nodes.append(node_ckpt)

        # 2. LoRA Nodes (chained)
        lora_nodes = []
        for i, l_info in enumerate(loras):
            l_id = 7 if i == 0 else 100 + i
            l_node = {
                "id": l_id,
                "type": "LoraLoader",
                "pos": [450 + i * 40, 100 + i * 40],
                "size": [315, 126],
                "flags": {},
                "order": 2 + i,
                "mode": 0,
                "inputs": [
                    {"name": "model", "type": "MODEL", "link": None},
                    {"name": "clip", "type": "CLIP", "link": None}
                ],
                "outputs": [
                    {"name": "MODEL", "type": "MODEL", "links": [], "shape": 3, "slot_index": 0},
                    {"name": "CLIP", "type": "CLIP", "links": [], "shape": 3, "slot_index": 1}
                ],
                "properties": {"Node name for S&R": "LoraLoader"},
                "widgets_values": [l_info["name"], l_info["strength_model"], l_info["strength_clip"]]
            }
            lora_nodes.append(l_node)
            updated_nodes.append(l_node)

        # 3. Latent Nodes (Txt2Img vs Img2Img)
        node_empty_latent = None
        node_load_img = None
        node_vae_enc = None

        if mode == "txt2img":
            node_empty_latent = {
                "id": 10,
                "type": "EmptyLatentImage",
                "pos": [450, 450],
                "size": [210, 106],
                "flags": {},
                "order": 2,
                "mode": 0,
                "inputs": [],
                "outputs": [
                    {"name": "LATENT", "type": "LATENT", "links": [], "shape": 3, "slot_index": 0}
                ],
                "properties": {"Node name for S&R": "EmptyLatentImage"},
                "widgets_values": [width, height, batch_size]
            }
            updated_nodes.append(node_empty_latent)
        else:
            node_load_img = {
                "id": 1,
                "type": "LoadImage",
                "pos": [50, 450],
                "size": [315, 314],
                "flags": {},
                "order": 0,
                "mode": 0,
                "inputs": [],
                "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": [], "shape": 3, "slot_index": 0},
                    {"name": "MASK", "type": "MASK", "links": [], "shape": 3, "slot_index": 1}
                ],
                "properties": {"Node name for S&R": "LoadImage"},
                "widgets_values": [image_name, "image"]
            }
            node_vae_enc = {
                "id": 2,
                "type": "VAEEncode",
                "pos": [450, 450],
                "size": [210, 46],
                "flags": {},
                "order": 3,
                "mode": 0,
                "inputs": [
                    {"name": "pixels", "type": "IMAGE", "link": None},
                    {"name": "vae", "type": "VAE", "link": None}
                ],
                "outputs": [
                    {"name": "LATENT", "type": "LATENT", "links": [], "shape": 3, "slot_index": 0}
                ],
                "properties": {"Node name for S&R": "VAEEncode"},
                "widgets_values": []
            }
            updated_nodes.append(node_load_img)
            updated_nodes.append(node_vae_enc)

        # 4. Prompt Nodes
        node_pos = {
            "id": 5,
            "type": "CLIPTextEncode",
            "pos": [820, 50],
            "size": [420, 180],
            "flags": {},
            "order": 4,
            "mode": 0,
            "title": "CLIP Text Encode (Positive)",
            "inputs": [
                {"name": "clip", "type": "CLIP", "link": None}
            ],
            "outputs": [
                {"name": "CONDITIONING", "type": "CONDITIONING", "links": [], "shape": 3, "slot_index": 0}
            ],
            "properties": {"Node name for S&R": "CLIPTextEncode"},
            "widgets_values": [pos_prompt]
        }
        node_neg = {
            "id": 6,
            "type": "CLIPTextEncode",
            "pos": [820, 270],
            "size": [420, 180],
            "flags": {},
            "order": 5,
            "mode": 0,
            "title": "CLIP Text Encode (Negative)",
            "inputs": [
                {"name": "clip", "type": "CLIP", "link": None}
            ],
            "outputs": [
                {"name": "CONDITIONING", "type": "CONDITIONING", "links": [], "shape": 3, "slot_index": 0}
            ],
            "properties": {"Node name for S&R": "CLIPTextEncode"},
            "widgets_values": [neg_prompt]
        }
        updated_nodes.append(node_pos)
        updated_nodes.append(node_neg)

        # 5. KSampler Node
        node_ksampler = {
            "id": 3,
            "type": "KSampler",
            "pos": [1300, 150],
            "size": [315, 262],
            "flags": {},
            "order": 6,
            "mode": 0,
            "inputs": [
                {"name": "model", "type": "MODEL", "link": None},
                {"name": "positive", "type": "CONDITIONING", "link": None},
                {"name": "negative", "type": "CONDITIONING", "link": None},
                {"name": "latent_image", "type": "LATENT", "link": None}
            ],
            "outputs": [
                {"name": "LATENT", "type": "LATENT", "links": [], "shape": 3, "slot_index": 0}
            ],
            "properties": {"Node name for S&R": "KSampler"},
            "widgets_values": [seed, "randomize", steps, cfg, sampler_name, scheduler, denoise]
        }
        updated_nodes.append(node_ksampler)

        # 6. VAEDecode Node
        node_vae_dec = {
            "id": 8,
            "type": "VAEDecode",
            "pos": [1680, 150],
            "size": [210, 46],
            "flags": {},
            "order": 7,
            "mode": 0,
            "inputs": [
                {"name": "samples", "type": "LATENT", "link": None},
                {"name": "vae", "type": "VAE", "link": None}
            ],
            "outputs": [
                {"name": "IMAGE", "type": "IMAGE", "links": [], "shape": 3, "slot_index": 0}
            ],
            "properties": {"Node name for S&R": "VAEDecode"},
            "widgets_values": []
        }
        updated_nodes.append(node_vae_dec)

        # 7. SaveImage Node
        node_save_img = {
            "id": 9,
            "type": "SaveImage",
            "pos": [1950, 150],
            "size": [315, 270],
            "flags": {},
            "order": 8,
            "mode": 0,
            "inputs": [
                {"name": "images", "type": "IMAGE", "link": None}
            ],
            "outputs": [],
            "properties": {"Node name for S&R": "SaveImage"},
            "widgets_values": ["VeraNote"]
        }
        updated_nodes.append(node_save_img)

        # ---- Build Links ----
        # Model & Clip wiring
        if not lora_nodes:
            create_link(node_ckpt, 0, node_ksampler, 0, "MODEL")
            create_link(node_ckpt, 1, node_pos, 0, "CLIP")
            create_link(node_ckpt, 1, node_neg, 0, "CLIP")
        else:
            # Checkpoint to first LoRA
            create_link(node_ckpt, 0, lora_nodes[0], 0, "MODEL")
            create_link(node_ckpt, 1, lora_nodes[0], 1, "CLIP")
            # Intermediate LoRAs
            for i in range(len(lora_nodes) - 1):
                create_link(lora_nodes[i], 0, lora_nodes[i+1], 0, "MODEL")
                create_link(lora_nodes[i], 1, lora_nodes[i+1], 1, "CLIP")
            # Last LoRA to KSampler and Prompts
            create_link(lora_nodes[-1], 0, node_ksampler, 0, "MODEL")
            create_link(lora_nodes[-1], 1, node_pos, 0, "CLIP")
            create_link(lora_nodes[-1], 1, node_neg, 0, "CLIP")

        # Conditioning wiring (Prompts -> KSampler)
        create_link(node_pos, 0, node_ksampler, 1, "CONDITIONING")
        create_link(node_neg, 0, node_ksampler, 2, "CONDITIONING")

        # Latent Image wiring
        if mode == "txt2img":
            create_link(node_empty_latent, 0, node_ksampler, 3, "LATENT")
        else:
            create_link(node_load_img, 0, node_vae_enc, 0, "IMAGE")
            create_link(node_ckpt, 2, node_vae_enc, 1, "VAE")
            create_link(node_vae_enc, 0, node_ksampler, 3, "LATENT")

        # VAE Decode wiring
        create_link(node_ksampler, 0, node_vae_dec, 0, "LATENT")
        create_link(node_ckpt, 2, node_vae_dec, 1, "VAE")

        # Save Image wiring
        create_link(node_vae_dec, 0, node_save_img, 0, "IMAGE")

        workflow["nodes"] = updated_nodes
        workflow["links"] = links
        workflow["last_link_id"] = link_id_counter
        workflow["last_node_id"] = max(n["id"] for n in updated_nodes)

    return workflow, prompt


def export_workflow_to_json(output_path: str, workflow_dict: dict, prompt_dict: dict = None) -> bool:
    """
    Saves the ComfyUI workflow JSON to disk.
    If prompt_dict is provided, embeds it in the workflow's extra dict so both formats exist.
    """
    try:
        data_to_save = copy.deepcopy(workflow_dict)
        if prompt_dict:
            extra = data_to_save.setdefault("extra", {})
            extra["prompt"] = prompt_dict

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error exporting workflow JSON to {output_path}: {e}")
        return False


def create_workflow_canvas_image(width: int = 1024, height: int = 1024, title: str = "VeraNote Workflow", subtitle: str = "") -> Image.Image:
    """
    Creates an elegant, high-contrast placeholder PNG canvas when no input image is provided.
    Features subtle grid pattern, metadata header, and ComfyUI drag-and-drop indicator.
    """
    canvas_w = max(512, min(width, 1920))
    canvas_h = max(512, min(height, 1920))

    img = Image.new("RGBA", (canvas_w, canvas_h), (24, 25, 27, 255))
    draw = ImageDraw.Draw(img)

    # Subtle grid dots
    step = 64
    for x in range(0, canvas_w, step):
        for y in range(0, canvas_h, step):
            draw.point((x, y), fill=(45, 47, 52, 255))

    # Center card border
    margin_x = max(24, canvas_w // 8)
    margin_y = max(24, canvas_h // 8)
    card_rect = [margin_x, margin_y, canvas_w - margin_x, canvas_h - margin_y]
    draw.rounded_rectangle(card_rect, radius=16, fill=(30, 31, 34, 230), outline=(68, 71, 78, 255), width=2)

    center_x = canvas_w // 2
    center_y = canvas_h // 2
    draw.text((center_x, center_y - 40), title, fill=(227, 227, 227, 255), anchor="mm")
    draw.text((center_x, center_y + 10), f"{width} x {height}  |  Txt2Img", fill=(138, 180, 248, 255), anchor="mm")
    if subtitle:
        draw.text((center_x, center_y + 45), subtitle, fill=(154, 160, 166, 255), anchor="mm")
    draw.text((center_x, canvas_h - margin_y - 25), "ComfyUI Drag & Drop Ready", fill=(100, 105, 115, 255), anchor="mm")

    return img


def export_workflow_to_png(input_image_path: str, output_path: str, workflow_dict: dict, prompt_dict: dict, width: int = 1024, height: int = 1024, subtitle: str = "") -> bool:
    """
    Embeds ComfyUI 'workflow' and 'prompt' text chunks into the PNG image metadata.
    If input_image_path is provided, uses it. If not, generates an elegant canvas with specified resolution.
    ComfyUI reads these chunks directly when a PNG is dragged into its web canvas.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if input_image_path and os.path.exists(input_image_path):
            with Image.open(input_image_path) as src_img:
                img = src_img.copy()
        else:
            # Generate canvas
            img = create_workflow_canvas_image(width=width, height=height, title="VeraNote ComfyUI Workflow", subtitle=subtitle)

        pnginfo = PngImagePlugin.PngInfo()
        if workflow_dict:
            pnginfo.add_text("workflow", json.dumps(workflow_dict, ensure_ascii=False))
        if prompt_dict:
            pnginfo.add_text("prompt", json.dumps(prompt_dict, ensure_ascii=False))

        # Save with metadata
        img.save(output_path, "PNG", pnginfo=pnginfo)
        return True
    except Exception as e:
        print(f"Error exporting ComfyUI PNG to {output_path}: {e}")
        return False
