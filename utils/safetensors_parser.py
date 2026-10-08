# utils/safetensors_parser.py
"""
Lightweight Safetensors Header Parser & Architecture Detector for VeraNote.
Zero RAM/VRAM Tensor Allocations: Only reads the first 8 bytes (<Q) and the header JSON.
"""

import json
import os
import struct
import logging

logger = logging.getLogger(__name__)

# Max header size safeguard to protect against malicious or corrupt files (e.g. 100 MB)
MAX_HEADER_SIZE = 100 * 1024 * 1024


def read_safetensors_header(file_path: str) -> dict | None:
    """
    Safely reads only the metadata and tensor keys from a .safetensors header.
    Never loads tensors or weights into memory.
    
    Args:
        file_path (str): Absolute or relative path to the .safetensors file.
        
    Returns:
        dict | None: The parsed header JSON dictionary, or None if invalid/unreadable.
    """
    if not file_path or not os.path.exists(file_path):
        return None
        
    try:
        with open(file_path, "rb") as f:
            header_len_bytes = f.read(8)
            if len(header_len_bytes) < 8:
                return None
            
            # Read 8-byte unsigned little-endian integer for header length
            header_len = struct.unpack("<Q", header_len_bytes)[0]
            
            if header_len <= 0 or header_len > MAX_HEADER_SIZE:
                logger.warning(f"Invalid safetensors header length {header_len} in {file_path}")
                return None
                
            header_bytes = f.read(header_len)
            if len(header_bytes) < header_len:
                logger.warning(f"Incomplete safetensors header read in {file_path}")
                return None
                
            header_str = header_bytes.decode("utf-8", errors="replace")
            header_json = json.loads(header_str)
            return header_json if isinstance(header_json, dict) else None
    except Exception as e:
        logger.error(f"Error reading safetensors header from {file_path}: {e}")
        return None


def map_architecture_to_canonical(arch_str: str) -> str:
    """
    Maps detected architecture string to canonical UI options:
    Flux, SDXL, Pony, Illustrious, SD 1.5, SD3, SD 2.1, Diğer.
    """
    if not arch_str or arch_str.lower() in ("unknown", "bilinmiyor", "none", ""):
        return ""
    low = arch_str.lower()
    if "flux" in low:
        return "Flux"
    if "pony" in low:
        return "Pony"
    if "illustrious" in low or "noobai" in low:
        return "Illustrious"
    if "sdxl" in low:
        return "SDXL"
    if "1.5" in low or "sd15" in low or "v1-5" in low:
        return "SD 1.5"
    if "sd3" in low or "sd 3" in low:
        return "SD3"
    if "2.1" in low or "sd2" in low:
        return "SD 2.1"
    return "Diğer"


def _check_sdxl_subvariant(meta_str: str, file_path: str, tags_str: str) -> str:
    """
    When underlying architecture is determined as SDXL (or SDXL tensor blocks),
    checks file_path, metadata, or tags for Pony or Illustrious / NoobAI.
    Returns 'Pony', 'Illustrious', or 'SDXL'.
    """
    combined = f"{file_path} {meta_str} {tags_str}".lower()
    if "pony" in combined:
        return "Pony"
    if "illustrious" in combined or "noobai" in combined:
        return "Illustrious"
    return "SDXL"


def detect_lora_architecture(file_path: str, tags: list | str | None = None) -> str:
    """
    Detects base architecture (Flux.1, SD 3 / 3.5, SDXL, SD 1.5, Pony, Illustrious, etc.)
    using lightweight safetensors header inspection.
    
    Steps:
      1. Inspect __metadata__ (ss_base_model_version, modelspec.architecture, ss_sd_model_name, base_model, etc.).
         If SDXL is detected, check file_path, metadata, or tags for 'pony' or 'illustrious' sub-variants.
      2. If metadata is pruned or missing, inspect tensor key names in header.
         If SDXL tensor blocks are present, resolve sub-variant (Pony / Illustrious / SDXL).
      3. Fallback to filename/path and tags heuristic if header is missing or unrecognized.
      4. Returns "Unknown" if not determinable.
    """
    if not file_path:
        return "Unknown"

    # Normalize tags string
    tags_tokens = []
    if tags:
        if isinstance(tags, (list, tuple)):
            tags_tokens = [str(t).lower() for t in tags]
        elif isinstance(tags, str):
            tags_tokens = [tags.lower()]
    tags_str = " ".join(tags_tokens)

    header = None
    if file_path.lower().endswith(".safetensors"):
        header = read_safetensors_header(file_path)

    meta_str = ""
    if header and isinstance(header, dict):
        # 1. Check __metadata__
        metadata = header.get("__metadata__")
        if isinstance(metadata, dict):
            # Convert all metadata values and keys to lowercase string for fast scanning
            meta_str = " ".join(
                f"{str(k).lower()}:{str(v).lower()}" 
                for k, v in metadata.items()
                if isinstance(k, (str, int, float)) and isinstance(v, (str, int, float))
            )
            
            # Specific metadata fields prioritized
            base_model_ver = str(metadata.get("ss_base_model_version", "")).lower()
            modelspec_arch = str(metadata.get("modelspec.architecture", "")).lower()
            sd_model_name = str(metadata.get("ss_sd_model_name", "")).lower()
            base_model = str(metadata.get("base_model", "")).lower()
            meta_combined = f"{base_model_ver} {modelspec_arch} {sd_model_name} {base_model} {meta_str}"

            if "flux" in meta_combined:
                return "Flux.1"
            if "sd3" in meta_combined or "sd_3" in meta_combined or "stable diffusion 3" in meta_combined:
                return "SD 3 / 3.5"
            if "pony" in meta_combined:
                return "Pony"
            if "illustrious" in meta_combined or "noobai" in meta_combined:
                return "Illustrious"
            if "sd_xl" in meta_combined or "sdxl" in meta_combined or "stable diffusion xl" in meta_combined:
                return _check_sdxl_subvariant(meta_str, file_path, tags_str)
            if "sd_1_5" in meta_combined or "v1-5" in meta_combined or "sd 1.5" in meta_combined or "sd1.5" in meta_combined:
                return "SD 1.5"
            if "sd_2_1" in meta_combined or "sd2.1" in meta_combined or "sd 2.1" in meta_combined:
                return "SD 2.1"

        # 2. Inspect tensor key names (excluding __metadata__)
        tensor_keys = [k for k in header.keys() if k != "__metadata__"]
        
        # Check Flux.1
        if any("double_blocks" in k or "single_blocks" in k for k in tensor_keys):
            return "Flux.1"

        # Check SD 3 / 3.5
        if any("joint_blocks" in k for k in tensor_keys):
            return "SD 3 / 3.5"

        # Check explicit Pony tensor keys
        if any("pony" in k.lower() for k in tensor_keys):
            return "Pony"

        # Check SDXL tensor keys
        if any(
            "lora_unet_input_blocks" in k or 
            "lora_te2" in k or 
            "conditioner.embedders.1" in k or 
            "text_encoders.1" in k 
            for k in tensor_keys
        ):
            # Resolve SDXL subvariant: Pony, Illustrious, or generic SDXL
            return _check_sdxl_subvariant(meta_str, file_path, tags_str)

        # Check SD 1.5 tensor keys
        if any(
            "lora_unet_down_blocks" in k or 
            "lora_te_text_model" in k or 
            "down_blocks" in k 
            for k in tensor_keys
        ):
            return "SD 1.5"

    # 3. Fallback to file name and tags heuristic
    combined_fallback = f"{os.path.basename(file_path).lower()} {tags_str}"
    if "flux" in combined_fallback:
        return "Flux.1"
    if "sd3" in combined_fallback or "sd 3" in combined_fallback:
        return "SD 3 / 3.5"
    if "pony" in combined_fallback:
        return "Pony"
    if "illustrious" in combined_fallback or "noobai" in combined_fallback:
        return "Illustrious"
    if "sdxl" in combined_fallback or "xl" in combined_fallback:
        return _check_sdxl_subvariant(meta_str, file_path, tags_str)
    if "1.5" in combined_fallback or "sd15" in combined_fallback or "sd1.5" in combined_fallback or "v1-5" in combined_fallback:
        return "SD 1.5"
    if "2.1" in combined_fallback or "sd2" in combined_fallback:
        return "SD 2.1"

    return "Unknown"


def extract_metadata_tags_and_triggers(file_path: str, max_tags: int = 15) -> list[str]:
    """
    Safely extracts tags and trigger words from .safetensors header without loading tensors.
    
    1. Checks modelspec.trigger_phrase or trigger_phrase as primary trigger.
    2. Parses ss_tag_frequency JSON block and aggregates tag counts across all buckets.
    3. Sorts tags by frequency descending and takes top max_tags (e.g. 10-15).
    4. Merges primary trigger(s) at index 0 and deduplicates case-insensitively.
    
    Args:
        file_path (str): Path to .safetensors file.
        max_tags (int): Maximum frequency tags to return (default 15).
        
    Returns:
        list[str]: Clean list of extracted tags and triggers.
    """
    if not file_path or not file_path.lower().endswith(".safetensors"):
        return []

    header = read_safetensors_header(file_path)
    if not header or not isinstance(header, dict):
        return []

    metadata = header.get("__metadata__")
    if not metadata or not isinstance(metadata, dict):
        return []

    primary_triggers = []
    # 1. Check modelspec.trigger_phrase or trigger_phrase
    trigger_raw = metadata.get("modelspec.trigger_phrase") or metadata.get("trigger_phrase") or ""
    if isinstance(trigger_raw, str) and trigger_raw.strip():
        for part in trigger_raw.split(","):
            cleaned = part.strip()
            if cleaned:
                primary_triggers.append(cleaned)
    elif isinstance(trigger_raw, (list, tuple)):
        for item in trigger_raw:
            cleaned = str(item).strip()
            if cleaned:
                primary_triggers.append(cleaned)

    # 2. Check ss_tag_frequency
    freq_raw = metadata.get("ss_tag_frequency")
    freq_data = None
    if isinstance(freq_raw, str):
        try:
            freq_data = json.loads(freq_raw)
        except Exception:
            freq_data = None
    elif isinstance(freq_raw, dict):
        freq_data = freq_raw

    tag_counts = {}
    if isinstance(freq_data, dict):
        for bucket_key, bucket_val in freq_data.items():
            if isinstance(bucket_val, dict):
                for tag, count in bucket_val.items():
                    clean_tag = str(tag).strip()
                    if clean_tag:
                        try:
                            cnt = int(count)
                        except (ValueError, TypeError):
                            cnt = 1
                        tag_counts[clean_tag] = tag_counts.get(clean_tag, 0) + cnt
            elif isinstance(bucket_val, (int, float)):
                clean_tag = str(bucket_key).strip()
                if clean_tag:
                    tag_counts[clean_tag] = tag_counts.get(clean_tag, 0) + int(bucket_val)

    # Sort frequency tags descending
    sorted_freq = [
        tag for tag, _ in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    freq_top = sorted_freq[:max_tags]

    # If no frequency tags found, check modelspec.tags or tags
    if not freq_top:
        extra_tags = metadata.get("modelspec.tags") or metadata.get("tags") or ""
        if isinstance(extra_tags, str) and extra_tags.strip():
            for t in extra_tags.split(","):
                cleaned = t.strip()
                if cleaned:
                    freq_top.append(cleaned)
        elif isinstance(extra_tags, (list, tuple)):
            for t in extra_tags:
                cleaned = str(t).strip()
                if cleaned:
                    freq_top.append(cleaned)

    # Combine primary triggers first, then frequency tags, deduplicating case-insensitively
    seen = set()
    final_tags = []
    for tag in primary_triggers + freq_top:
        clean = tag.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            final_tags.append(clean)

    return final_tags


def extract_primary_trigger_phrase(file_path: str) -> str:
    """Returns primary trigger phrase from modelspec.trigger_phrase or metadata, or empty string."""
    if not file_path or not file_path.lower().endswith(".safetensors"):
        return ""
    header = read_safetensors_header(file_path)
    if not header or not isinstance(header, dict):
        return ""
    metadata = header.get("__metadata__")
    if not metadata or not isinstance(metadata, dict):
        return ""
    raw = metadata.get("modelspec.trigger_phrase") or metadata.get("trigger_phrase") or ""
    return str(raw).strip()


def merge_tags(existing_tags: list[str], new_tags: list[str]) -> list[str]:
    """
    Merges newly extracted tags into existing tags:
    - Existing user tags are kept at the front in original order.
    - New tags are appended to the end without duplicates (case-insensitive check).
    """
    merged = []
    seen = set()
    for t in existing_tags or []:
        clean = str(t).strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            merged.append(clean)
    for t in new_tags or []:
        clean = str(t).strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            merged.append(clean)
    return merged
