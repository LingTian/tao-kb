import os
import re
import json
from collections import defaultdict

def extract_tags(content):
    # Find all 〖@Type:Content〗
    tags = re.findall(r'〖@([^:]+):([^〗]+)〗', content)
    return tags

base_dir = "chapters/zhuangzi"
nodes = {} # { (type, name): count }
edges = defaultdict(int) # { ((t1, n1), (t2, n2)): count }

file_entities = {} # { filename: set of (type, name) }

for file in os.listdir(base_dir):
    if file.endswith(".tagged.md"):
        path = os.path.join(base_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tags = extract_tags(content)
        entities = set()
        for t_type, name in tags:
            node_key = (t_type, name)
            nodes[node_key] = nodes.get(node_key, 0) + 1
            entities.add(node_key)
        
        file_entities[file] = entities
        
        # Link entities that appear in the same file (co-occurrence)
        # For a large graph, we might want to restrict this to paragraphs,
        # but let's start with file-level for a "Chapter-Entity" map or just entity-entity.
        ent_list = list(entities)
        for i in range(len(ent_list)):
            for j in range(i + 1, len(ent_list)):
                pair = tuple(sorted([ent_list[i], ent_list[j]]))
                edges[pair] += 1

# Format for JSON
kg_data = {
    "nodes": [{"id": f"{t}:{n}", "type": t, "name": n, "weight": count} for (t, n), count in nodes.items()],
    "links": [{"source": f"{p[0][0]}:{p[0][1]}", "target": f"{p[1][0]}:{p[1][1]}", "weight": count} for p, count in edges.items() if count > 1] # Only strong links
}

with open("zhuangzi_kg.json", "w", encoding='utf-8') as f:
    json.dump(kg_data, f, ensure_ascii=False, indent=2)

# Generate a Mermaid file for the most important nodes (top 30 by weight)
top_nodes = sorted(nodes.items(), key=lambda x: x[1], reverse=True)[:40]
top_node_ids = {f"{t}:{n}" for (t, n), count in top_nodes}

mermaid = "graph LR\n"
# Color definitions
mermaid += "classDef person fill:#f9f,stroke:#333,stroke-width:2px;\n"
mermaid += "classDef place fill:#ccf,stroke:#333,stroke-width:2px;\n"
mermaid += "classDef bio fill:#cfc,stroke:#333,stroke-width:2px;\n"
mermaid += "classDef concept fill:#fcf,stroke:#333,stroke-width:2px;\n"
mermaid += "classDef state fill:#ffc,stroke:#333,stroke-width:2px;\n"

type_to_class = {
    "人物": "person",
    "地名": "place",
    "生物": "bio",
    "概念": "concept",
    "境界": "state"
}

for (t, n), count in top_nodes:
    node_id = f"{t}_{n}".replace(" ", "_").replace("(", "").replace(")", "")
    mermaid += f"  {node_id}({n})\n"
    if t in type_to_class:
        mermaid += f"  class {node_id} {type_to_class[t]};\n"

# Add edges between top nodes
for (p1, p2), count in edges.items():
    id1 = f"{p1[0]}:{p1[1]}"
    id2 = f"{p2[0]}:{p2[1]}"
    if id1 in top_node_ids and id2 in top_node_ids and count > 2:
        m_id1 = id1.replace(":", "_").replace(" ", "_").replace("(", "").replace(")", "")
        m_id2 = id2.replace(":", "_").replace(" ", "_").replace("(", "").replace(")", "")
        mermaid += f"  {m_id1} --- {m_id2}\n"

with open("zhuangzi_kg.mmd", "w", encoding='utf-8') as f:
    f.write(mermaid)

print("Knowledge graph data generated.")
