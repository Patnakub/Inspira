import os
import hashlib
import json
from glob import glob

def hash_filename(title):
    return hashlib.md5(title.encode("utf-8")).hexdigest() + ".json"

def process_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check if it's a list or dict
        if isinstance(data, list) and len(data) > 0:
            title = data[0].get("title", "")
            for d in data:
                d["original_filename"] = os.path.basename(file_path)
        elif isinstance(data, dict):
            title = data.get("title", "")
            data["original_filename"] = os.path.basename(file_path)
        else:
            print(f"Missing title field in file: {file_path}")
            return

        if not title:
            print(f"No title found for hashing: {file_path}")
            return

        # Generate new filename from hash
        new_name = hash_filename(title)
        new_path = os.path.join(os.path.dirname(file_path), new_name)

        # Write file with new name
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Remove original file if names differ
        if os.path.abspath(new_path) != os.path.abspath(file_path):
            os.remove(file_path)

        print(f"{os.path.basename(file_path)} renamed to {new_name}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

# Base folders and target mode
base_folders = ["./scrapy_project/spiders"]
modes = ["upcoming"]  # Only rename upcoming files

for base in base_folders:
    for mode in modes:
        target_path = os.path.join(base, "**", "raw_data", mode, "*.json")
        json_files = glob(target_path, recursive=True)

        print(f"\nProcessing {len(json_files)} files in {mode} mode")

        for file_path in json_files:
            process_json_file(file_path)
