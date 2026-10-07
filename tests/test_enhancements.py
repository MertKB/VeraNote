import os
import sys
import json
import tempfile
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PIL import Image, PngImagePlugin

import database
from utils.png_parser import (
    extract_workflow_from_png,
    extract_prompt_from_png,
    extract_comfyui_metadata_from_png
)
from utils.workflow_parser import parse_workflow_node_types


def test_png_parser_and_workflow_node_extraction():
    # Create a synthetic PNG with ComfyUI prompt and workflow chunks
    prompt_payload = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 123456789,
                "steps": 25,
                "cfg": 7.5,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0]
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "v1-5-pruned-emaonly.safetensors"
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "masterpiece, best quality, cyberpunk neon city street at night, rain reflections"
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "worst quality, low quality, blurry"
            }
        },
        "10": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "cyberpunk_style.safetensors"
            }
        }
    }

    workflow_payload = {
        "nodes": [
            {"type": "KSampler", "id": 3},
            {"type": "CheckpointLoaderSimple", "id": 4},
            {"type": "CLIPTextEncode", "id": 6},
            {"type": "CLIPTextEncode", "id": 7},
            {"type": "LoraLoader", "id": 10},
            {"type": "VAEDecode", "id": 8}
        ]
    }

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        img = Image.new("RGB", (64, 64), color="indigo")
        meta = PngImagePlugin.PngInfo()
        meta.add_text("prompt", json.dumps(prompt_payload))
        meta.add_text("workflow", json.dumps(workflow_payload))
        img.save(tmp_path, "PNG", pnginfo=meta)

        # 1. Test extract_workflow_from_png
        wf = extract_workflow_from_png(tmp_path)
        assert wf is not None
        assert "nodes" in wf
        assert len(wf["nodes"]) == 6

        # 2. Test extract_prompt_from_png
        p = extract_prompt_from_png(tmp_path)
        assert p is not None
        assert "3" in p

        # 3. Test extract_comfyui_metadata_from_png
        comfy_meta = extract_comfyui_metadata_from_png(tmp_path)
        assert "cyberpunk neon city" in comfy_meta["positive_prompt"]
        assert "worst quality" in comfy_meta["negative_prompt"]
        assert "v1-5-pruned-emaonly.safetensors" in comfy_meta["models"]
        assert any("cyberpunk_style.safetensors" in m for m in comfy_meta["models"])
        assert comfy_meta["sampler_params"]["seed"] == 123456789
        assert comfy_meta["sampler_params"]["steps"] == 25
        assert comfy_meta["sampler_params"]["cfg"] == 7.5
        assert comfy_meta["sampler_params"]["sampler_name"] == "euler_ancestral"
        assert comfy_meta.get("base_architecture") == "SD 1.5"

        from utils.png_parser import detect_base_architecture
        assert detect_base_architecture(["flux1-dev.safetensors"]) == "Flux"
        assert detect_base_architecture(["sd_xl_base_1.0.safetensors"]) == "SDXL"
        assert detect_base_architecture(["ponyDiffusionV6XL.safetensors"]) == "Pony"

        # 4. Test parse_workflow_node_types from dict and from file
        node_counts_from_dict = dict(parse_workflow_node_types(workflow_payload))
        assert node_counts_from_dict["KSampler"] == 1
        assert node_counts_from_dict["CLIPTextEncode"] == 2
        assert node_counts_from_dict["VAEDecode"] == 1

        node_counts_from_file = dict(parse_workflow_node_types(tmp_path))
        assert node_counts_from_file["KSampler"] == 1
        assert node_counts_from_file["CLIPTextEncode"] == 2
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_note_model_association():
    # Save a test note
    note_id = database.save_note(None, "Enhancement Test Note", "Testing note model linking")
    assert note_id is not None

    # Get a model from DB or register one
    models = database.get_all_models_for_association()
    if not models:
        # Register a temporary model
        lib_name = "Test Enhancements Lib"
        database.add_library(lib_name)
        model_id = database.register_model(lib_name, "TestModel1", "/path/to/test.safetensors", "hash123")
    else:
        model_id = models[0]['id']

    # Associate
    assert database.associate_note_model(note_id, model_id) is True

    # Retrieve note with associated models
    note = database.get_note_by_id(note_id)
    assert note is not None
    assoc = note.get('associated_models', [])
    assert any(m['id'] == model_id for m in assoc)

    # Dissociate
    assert database.dissociate_note_model(note_id, model_id) is True
    note_after = database.get_note_by_id(note_id)
    assoc_after = note_after.get('associated_models', [])
    assert not any(m['id'] == model_id for m in assoc_after)

    # Cleanup test note
    database.permanently_delete_note(note_id)


def test_backup_and_restore_zip():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_path = tmp.name

    try:
        # 1. Export backup ZIP
        success = database.export_backup_zip(zip_path)
        assert success is True
        assert os.path.exists(zip_path)
        assert os.path.getsize(zip_path) > 0

        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            namelist = zf.namelist()
            assert "veranote.db" in namelist

        # 2. Import backup ZIP
        restore_success = database.import_backup_zip(zip_path)
        assert restore_success is True
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


def test_model_base_architecture():
    import time
    lib_name = "Arch Test Lib"
    database.add_library(lib_name)
    lib_id = database.get_library_id(lib_name)
    
    unique_path = f"/path/to/flux1-schnell-{time.time()}.safetensors"
    # 1. Register model with auto-detected architecture
    database.register_model(lib_id, "flux1-schnell-lora", unique_path, "h1")
    models = database.get_models_in_library(lib_name)
    assert len(models) >= 1
    m = [x for x in models if x['file_path'] == unique_path][0]
    assert m['base_architecture'] == "Flux"
    
    # 2. Update model architecture manually
    database.update_model_data(m['id'], "flux1-schnell-lora", "Notes", "Flux Dev")
    m_updated = database.get_model_by_id(m['id'])
    assert m_updated['base_architecture'] == "Flux Dev"

    # Cleanup
    database.delete_models([m['id']])
    with database.get_connection() as conn:
        conn.cursor().execute("DELETE FROM libraries WHERE id = ?;", (lib_id,))
        conn.commit()


if __name__ == "__main__":
    print("Running test_png_parser_and_workflow_node_extraction...")
    test_png_parser_and_workflow_node_extraction()
    print("  -> Passed!")

    print("Running test_note_model_association...")
    test_note_model_association()
    print("  -> Passed!")

    print("Running test_model_base_architecture...")
    test_model_base_architecture()
    print("  -> Passed!")

    print("Running test_backup_and_restore_zip...")
    test_backup_and_restore_zip()
    print("  -> Passed!")

    print("ALL ENHANCEMENT TESTS PASSED SUCCESSFULLY! [OK]")
