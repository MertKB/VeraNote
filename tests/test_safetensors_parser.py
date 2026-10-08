"""
Tests for Safetensors lightweight header parser and architecture auto-detection.
Ensures zero RAM/VRAM full model loading, verifies metadata and tensor key detections,
and validates ModelSection / database integration.
"""

import os
import sys
import json
import struct
import tempfile

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.safetensors_parser import read_safetensors_header, detect_lora_architecture
import database


def create_dummy_safetensors(file_path: str, header_dict: dict, dummy_tensor_bytes: bytes = b""):
    """Creates a valid safetensors file binary with 8-byte header length + JSON header."""
    header_json = json.dumps(header_dict).encode('utf-8')
    header_len = len(header_json)
    with open(file_path, "wb") as f:
        f.write(struct.pack("<Q", header_len))
        f.write(header_json)
        if dummy_tensor_bytes:
            f.write(dummy_tensor_bytes)


def test_safetensors_header_reading():
    with tempfile.TemporaryDirectory() as tmpdir:
        sf_path = os.path.join(tmpdir, "test_model.safetensors")
        sample_header = {
            "__metadata__": {"ss_base_model_version": "flux_1_dev"},
            "transformer.single_blocks.0.linear1.weight": {"dtype": "F16", "shape": [10, 10], "data_offsets": [0, 200]}
        }
        create_dummy_safetensors(sf_path, sample_header, b"\x00" * 200)

        header = read_safetensors_header(sf_path)
        assert header is not None
        assert "__metadata__" in header
        assert header["__metadata__"]["ss_base_model_version"] == "flux_1_dev"
        assert "transformer.single_blocks.0.linear1.weight" in header


def test_corrupted_safetensors_header():
    with tempfile.TemporaryDirectory() as tmpdir:
        # File shorter than 8 bytes
        short_file = os.path.join(tmpdir, "short.safetensors")
        with open(short_file, "wb") as f:
            f.write(b"123")
        assert read_safetensors_header(short_file) is None
        assert detect_lora_architecture(short_file) == "Unknown"

        # Invalid JSON header
        bad_json_file = os.path.join(tmpdir, "bad_json.safetensors")
        with open(bad_json_file, "wb") as f:
            f.write(struct.pack("<Q", 10))
            f.write(b"not a json")
        assert read_safetensors_header(bad_json_file) is None
        assert detect_lora_architecture(bad_json_file) == "Unknown"


def test_detect_from_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Flux from metadata
        f_path = os.path.join(tmpdir, "lora1.safetensors")
        create_dummy_safetensors(f_path, {
            "__metadata__": {"modelspec.architecture": "flux:v1"}
        })
        assert detect_lora_architecture(f_path) == "Flux.1"

        # 2. SDXL from metadata
        xl_path = os.path.join(tmpdir, "lora2.safetensors")
        create_dummy_safetensors(xl_path, {
            "__metadata__": {"ss_base_model_version": "sd_xl_base_1.0"}
        })
        assert detect_lora_architecture(xl_path) == "SDXL"

        # 3. SD 1.5 from metadata
        sd15_path = os.path.join(tmpdir, "lora3.safetensors")
        create_dummy_safetensors(sd15_path, {
            "__metadata__": {"ss_sd_model_name": "v1-5-pruned-emaonly"}
        })
        assert detect_lora_architecture(sd15_path) == "SD 1.5"

        # 4. Pony from metadata
        pony_path = os.path.join(tmpdir, "lora4.safetensors")
        create_dummy_safetensors(pony_path, {
            "__metadata__": {"base_model": "Pony Diffusion V6 XL"}
        })
        assert detect_lora_architecture(pony_path) == "Pony"


def test_detect_from_pruned_metadata_tensor_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Flux via single_blocks
        flux_path = os.path.join(tmpdir, "pruned_flux.safetensors")
        create_dummy_safetensors(flux_path, {
            "single_blocks.0.modulation.lin.weight": {"dtype": "F16", "shape": [1, 1], "data_offsets": [0, 2]}
        })
        assert detect_lora_architecture(flux_path) == "Flux.1"

        # 2. SD 3 / 3.5 via joint_blocks
        sd3_path = os.path.join(tmpdir, "pruned_sd3.safetensors")
        create_dummy_safetensors(sd3_path, {
            "joint_blocks.0.context_block.weight": {"dtype": "F16", "shape": [1, 1], "data_offsets": [0, 2]}
        })
        assert detect_lora_architecture(sd3_path) == "SD 3 / 3.5"

        # 3. SDXL via lora_unet_input_blocks / lora_te2
        sdxl_path = os.path.join(tmpdir, "pruned_sdxl.safetensors")
        create_dummy_safetensors(sdxl_path, {
            "lora_unet_input_blocks_4_1_proj_in.lora_up.weight": {"dtype": "F16", "shape": [1, 1], "data_offsets": [0, 2]},
            "lora_te2_text_model_encoder_layers_0_mlp_fc1.lora_down.weight": {"dtype": "F16", "shape": [1, 1], "data_offsets": [2, 4]}
        })
        assert detect_lora_architecture(sdxl_path) == "SDXL"

        # 4. SD 1.5 via lora_unet_down_blocks / lora_te_text_model
        sd15_path = os.path.join(tmpdir, "pruned_sd15.safetensors")
        create_dummy_safetensors(sd15_path, {
            "lora_unet_down_blocks_0_attentions_0_proj_in.lora_down.weight": {"dtype": "F16", "shape": [1, 1], "data_offsets": [0, 2]},
            "lora_te_text_model_encoder_layers_0_mlp_fc1.lora_up.weight": {"dtype": "F16", "shape": [1, 1], "data_offsets": [2, 4]}
        })
        assert detect_lora_architecture(sd15_path) == "SD 1.5"


def test_sdxl_subvariants():
    with tempfile.TemporaryDirectory() as tmpdir:
        from utils.safetensors_parser import map_architecture_to_canonical
        
        # 1. SDXL metadata + pony in filename -> Pony
        pony_sf = os.path.join(tmpdir, "character_pony_v6.safetensors")
        create_dummy_safetensors(pony_sf, {
            "__metadata__": {"ss_base_model_version": "sd_xl_base_1.0"}
        })
        assert detect_lora_architecture(pony_sf) == "Pony"
        assert map_architecture_to_canonical(detect_lora_architecture(pony_sf)) == "Pony"

        # 2. SDXL metadata + illustrious in metadata -> Illustrious
        ill_sf = os.path.join(tmpdir, "style_model.safetensors")
        create_dummy_safetensors(ill_sf, {
            "__metadata__": {
                "ss_base_model_version": "sd_xl_base_1.0",
                "ss_sd_model_name": "illustrious-xl-v1.0"
            }
        })
        assert detect_lora_architecture(ill_sf) == "Illustrious"
        assert map_architecture_to_canonical(detect_lora_architecture(ill_sf)) == "Illustrious"

        # 3. Pruned metadata + SDXL tensor keys + pony in tags -> Pony
        pruned_sf = os.path.join(tmpdir, "pruned_model.safetensors")
        create_dummy_safetensors(pruned_sf, {
            "lora_unet_input_blocks_4_1_proj_in.lora_up.weight": {"dtype": "F16", "shape": [1, 1], "data_offsets": [0, 2]}
        })
        assert detect_lora_architecture(pruned_sf, tags=["pony", "anime"]) == "Pony"
        assert detect_lora_architecture(pruned_sf, tags=["illustrious"]) == "Illustrious"
        assert detect_lora_architecture(pruned_sf, tags=["general"]) == "SDXL"

        # 4. NoobAI in metadata -> Illustrious
        noob_sf = os.path.join(tmpdir, "noob_art.safetensors")
        create_dummy_safetensors(noob_sf, {
            "__metadata__": {"modelspec.architecture": "noobai-xl"}
        })
        assert detect_lora_architecture(noob_sf) == "Illustrious"


def test_database_and_scanner_safetensors_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Register a model with real safetensors file
        sf_path = os.path.join(tmpdir, "custom_flux_lora.safetensors")
        create_dummy_safetensors(sf_path, {
            "double_blocks.0.img_attn.proj.weight": {"dtype": "F16", "shape": [1, 1], "data_offsets": [0, 2]}
        })

        # Register through database.py
        model_id = database.register_model(1, "custom_flux_lora", sf_path, "dummyhash")
        assert model_id is not None

        # Fetch model from DB and verify base_architecture is Flux
        m = database.get_model_by_id(model_id)
        assert m is not None
        assert m["base_architecture"] == "Flux"

        # Test updating base_architecture directly via database helper
        database.update_model_base_architecture(model_id, "Illustrious")
        m2 = database.get_model_by_id(model_id)
        assert m2["base_architecture"] == "Illustrious"


def test_metadata_tag_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        from utils.safetensors_parser import (
            extract_metadata_tags_and_triggers,
            extract_primary_trigger_phrase,
            merge_tags
        )

        sf_path = os.path.join(tmpdir, "tag_test_model.safetensors")
        sample_tag_freq = json.dumps({
            "10_char_main": {
                "1girl": 50,
                "fox ears": 45,
                "blue hair": 30,
                "smile": 20
            },
            "5_char_dress": {
                "1girl": 25,
                "white dress": 40,
                "fox ears": 20
            }
        })
        create_dummy_safetensors(sf_path, {
            "__metadata__": {
                "modelspec.trigger_phrase": "fubuki_vtuber, fox girl",
                "ss_tag_frequency": sample_tag_freq
            }
        })

        # 1. Primary trigger phrase
        primary = extract_primary_trigger_phrase(sf_path)
        assert primary == "fubuki_vtuber, fox girl"

        # 2. Extracted tags ordered: primary triggers first, then highest frequency tags
        extracted = extract_metadata_tags_and_triggers(sf_path, max_tags=10)
        assert extracted[0] == "fubuki_vtuber"
        assert extracted[1] == "fox girl"
        # Total counts: 1girl: 75, fox ears: 65, white dress: 40, blue hair: 30, smile: 20
        assert extracted[2] == "1girl"
        assert extracted[3] == "fox ears"
        assert extracted[4] == "white dress"
        assert extracted[5] == "blue hair"
        assert extracted[6] == "smile"

        # 3. Test merge_tags preserving existing user tags
        user_tags = ["my_custom_tag", "1girl"]
        merged = merge_tags(user_tags, extracted)
        # user_tags stay at the front:
        assert merged[0] == "my_custom_tag"
        assert merged[1] == "1girl"
        # Newly extracted tags appended, with duplicates ('1girl') filtered out:
        assert "fubuki_vtuber" in merged
        assert "white dress" in merged
        assert merged.count("1girl") == 1


def test_database_set_and_batch_tags():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Register a test model
        sf_path = os.path.join(tmpdir, "db_tag_model.safetensors")
        create_dummy_safetensors(sf_path, {"__metadata__": {"ss_base_model_version": "sd_xl"}})

        model_id = database.register_model(1, "db_tag_model", sf_path, "dummyhash")
        assert model_id is not None

        # Set tags using set_model_tags
        tags_to_set = ["vtuber", "anime", "holo"]
        assert database.set_model_tags(model_id, tags_to_set)

        # Verify tags retrieved from DB
        m = database.get_model_by_id(model_id)
        assert set(m["tags"]) == set(tags_to_set)

        # Batch add additional tags
        assert database.add_model_tags_batch(model_id, ["waifu", "holo"]) # 'holo' is duplicate
        m2 = database.get_model_by_id(model_id)
        assert "waifu" in m2["tags"]
        assert len(m2["tags"]) == 4 # vtuber, anime, holo, waifu


def test_trigger_words_persistence_and_no_rescan_on_open():
    """Validates that:
    1. Triggers are extracted ONLY on new model registration.
    2. Existing models in DB with empty triggers are NOT auto-rescan/overwritten on card open.
    3. Manual 'Dosyadan Çek' explicitly extracts & merges triggers via signal.
    """
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as tmpdir:
        sf_path = os.path.join(tmpdir, "lora_triggers.safetensors")
        create_dummy_safetensors(sf_path, {
            "__metadata__": {
                "modelspec.trigger_phrase": "masterpiece trigger",
                "ss_tag_frequency": json.dumps({"set1": {"hat": 20, "boots": 10}})
            }
        })

        # 1. First-time registration -> triggers automatically extracted
        model_id = database.register_model(1, "lora_triggers", sf_path, "hash1")
        assert model_id is not None
        triggers = database.get_trigger_words(model_id)
        assert "masterpiece trigger" in triggers
        assert "hat" in triggers
        assert "boots" in triggers

        # 2. User clears triggers (saved with empty trigger list in DB)
        database.set_trigger_words(model_id, [])
        assert database.get_trigger_words(model_id) == []

        # 3. Subsequent register_model calls for existing card MUST NOT re-scan or re-populate triggers
        re_id = database.register_model(1, "lora_triggers", sf_path, "hash1")
        assert database.get_trigger_words(model_id) == []

        # 4. Opening existing model in ModelSection MUST NOT re-scan file or fill triggers
        from ui.detail.model_section import ModelSection
        section = ModelSection()

        # Track signals
        emitted_triggers = []
        section.set_triggers_requested.connect(lambda mid, trigs: emitted_triggers.append((mid, trigs)))

        model_dict = database.get_model_by_id(model_id)
        section.set_model(model_dict, trigger_words=[])

        # Assert no auto-fill occurred upon opening card
        assert section.trigger_words == []
        assert len(emitted_triggers) == 0

        # Assert tags section does not have file fetch/reset buttons
        assert not hasattr(section, 'fetch_tags_btn')
        assert not hasattr(section, 'reset_tags_btn')

        # Assert trigger words section HAS fetch and reset buttons
        assert hasattr(section, 'fetch_tw_btn')
        assert hasattr(section, 'reset_tw_btn')

        # 5. User explicitly clicks "Dosyadan Çek" (run_fetch_triggers)
        section.run_fetch_triggers()
        assert len(emitted_triggers) == 1
        mid, trigs = emitted_triggers[0]
        assert mid == model_id
        assert "masterpiece trigger" in trigs
        assert "hat" in trigs
        assert "boots" in trigs


if __name__ == "__main__":
    print("Running test_safetensors_header_reading...")
    test_safetensors_header_reading()
    print(" -> Passed!")

    print("Running test_corrupted_safetensors_header...")
    test_corrupted_safetensors_header()
    print(" -> Passed!")

    print("Running test_detect_from_metadata...")
    test_detect_from_metadata()
    print(" -> Passed!")

    print("Running test_detect_from_pruned_metadata_tensor_keys...")
    test_detect_from_pruned_metadata_tensor_keys()
    print(" -> Passed!")

    print("Running test_sdxl_subvariants...")
    test_sdxl_subvariants()
    print(" -> Passed!")

    print("Running test_database_and_scanner_safetensors_integration...")
    test_database_and_scanner_safetensors_integration()
    print(" -> Passed!")

    print("Running test_metadata_tag_extraction...")
    test_metadata_tag_extraction()
    print(" -> Passed!")

    print("Running test_database_set_and_batch_tags...")
    test_database_set_and_batch_tags()
    print(" -> Passed!")

    print("Running test_trigger_words_persistence_and_no_rescan_on_open...")
    test_trigger_words_persistence_and_no_rescan_on_open()
    print(" -> Passed!")

    print("\nALL SAFETENSORS PARSER TESTS PASSED SUCCESSFULLY! [OK]")
