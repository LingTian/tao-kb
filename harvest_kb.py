import os
import re
import json

def harvest_tags(directory):
    """
    Scans the specified directory for tagged markdown files,
    extracts all 〖@Type:Content〗 tags, and organizes them
    into a structured knowledge index.
    """
    kb_index = {
        "metadata": {
            "project": "tao-kb",
            "source": "Tao Te Ching (Wang Bi version)",
            "total_chapters": 81
        },
        "stats": {
            "total_tags": 0,
            "type_counts": {}
        },
        "entities": {}
    }

    # Regex to find tags like 〖@Concept:Dao〗
    tag_pattern = re.compile(r'〖@(\w+):([^〗]+)〗')

    files = [f for f in os.listdir(directory) if f.endswith('.tagged.md')]
    files.sort()

    for filename in files:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

            # Find all tags in the current file
            matches = tag_pattern.findall(content)

            for tag_type, tag_content in matches:
                kb_index["stats"]["total_tags"] += 1
                
                # Update type counts
                kb_index["stats"]["type_counts"][tag_type] = kb_index["stats"]["type_counts"].get(tag_type, 0) + 1

                # Normalize tag content for indexing (e.g., handling Duality pipes)
                if tag_type == "对立":
                    # For dualities, index both sides
                    parts = tag_content.split('|')
                    for part in parts:
                        add_to_entities(kb_index, tag_type, part, filename)
                else:
                    add_to_entities(kb_index, tag_type, tag_content, filename)

    return kb_index

def add_to_entities(kb, tag_type, content, source_file):
    """Helper to add an entity to the index if it doesn't exist."""
    if content not in kb["entities"]:
        kb["entities"][content] = {
            "type": tag_type,
            "count": 0,
            "occurrences": []
        }
    
    kb["entities"][content]["count"] += 1
    if source_file not in kb["entities"][content]["occurrences"]:
        kb["entities"][content]["occurrences"].append(source_file)

if __name__ == "__main__":
    chapters_dir = "tao-kb/chapters"
    output_file = "tao-kb/kb_index.json"

    if not os.path.exists(chapters_dir):
        print(f"Error: Directory {chapters_dir} not found.")
    else:
        index = harvest_tags(chapters_dir)
        
        with open(output_file, 'w', encoding='utf-8') as out_f:
            json.dump(index, out_f, ensure_ascii=False, indent=2)
            
        print(f"Success! Harvested {index['stats']['total_tags']} tags.")
        print(f"Knowledge index saved to {output_file}")
        
        # Print a short summary
        print("\nSummary by Type:")
        for t, c in index["stats"]["type_counts"].items():
            print(f"- {t}: {c}")
