#!/usr/bin/env python3
"""
Extract first N vectors from large JSON file without loading it all into memory.
"""

import sys
import json

def extract_sample(input_file: str, output_file: str, sample_size: int = 1000):
    """Extract first N items from JSON array file"""
    print(f"📖 Reading {input_file}...")
    print(f"🎯 Extracting first {sample_size} vectors...")

    vectors = []
    current_object = []
    in_object = False
    brace_count = 0
    object_count = 0

    with open(input_file, 'r', encoding='utf-8') as f:
        # Skip opening bracket
        line = f.readline()
        if not line.strip().startswith('['):
            print(f"❌ File doesn't start with '[', got: {line[:50]}")
            return False

        for line in f:
            stripped = line.strip()

            # Check if we've collected enough
            if object_count >= sample_size:
                break

            # Track object boundaries by counting braces
            if '{' in line:
                if not in_object:
                    in_object = True
                    current_object = []
                brace_count += line.count('{')

            if in_object:
                current_object.append(line.rstrip('\n'))

            if '}' in line:
                brace_count -= line.count('}')

                # Complete object found
                if in_object and brace_count == 0:
                    # Parse the complete object
                    obj_text = '\n'.join(current_object)
                    # Remove trailing comma if present
                    obj_text = obj_text.rstrip(',').strip()
                    try:
                        vector_obj = json.loads(obj_text)
                        vectors.append(vector_obj)
                        object_count += 1

                        if object_count % 100 == 0:
                            print(f"   ✓ Extracted {object_count} vectors...")
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️  Failed to parse object {object_count}: {e}")

                    in_object = False
                    current_object = []

    print(f"✅ Extracted {len(vectors)} vectors")

    # Write output
    print(f"💾 Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(vectors, f, ensure_ascii=False, indent=2)

    print(f"✅ Sample created: {len(vectors)} vectors")
    return True

if __name__ == "__main__":
    input_file = "output/sanctions/vectors_tier01.json"
    output_file = "output/sanctions/vectors_sample.json"
    sample_size = 1000

    if len(sys.argv) > 1:
        sample_size = int(sys.argv[1])

    extract_sample(input_file, output_file, sample_size)
