#!/usr/bin/env python3
"""
Split Wen Zi from single merged file into chapter-based files.
Handles non-sequential chapter order in the source file.
"""

import os
import re

def split_wenzi(content):
    """
    Split Wen Zi content by ## headers and save as individual files in correct order.
    """
    # Match ## 文子/卷 X (without requiring \n prefix)
    section_pattern = re.compile(r'## (文子/卷 [一二三四五六七八九十]+)')
    
    # Find all sections with their positions
    matches = list(section_pattern.finditer(content))
    
    if not matches:
        print("  No sections found in wenzi")
        return 0
    
    # Extract sections
    sections = []
    for i, match in enumerate(matches):
        section_title = match.group(1)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()
        sections.append((section_title, section_content))
    
    # Sort by correct order
    ju_order = {
        '卷一': ('01', 'Dao_Yuan'),
        '卷二': ('02', 'Jing_Cheng'),
        '卷三': ('03', 'Jiu_Shou'),
        '卷四': ('04', 'Fu_Yan'),
        '卷五': ('05', 'Dao_De'),
        '卷六': ('06', 'Shang_De'),
        '卷七': ('07', 'Wei_Ming'),
        '卷八': ('08', 'Zi_Ran'),
        '卷九': ('09', 'Xia_De'),
        '卷十': ('10', 'Shang_Ren'),
        '卷十一': ('11', 'Shang_Yi'),
        '卷十二': ('12', 'Shang_Li')
    }
    
    output_dir = "chapters/wenzi"
    os.makedirs(output_dir, exist_ok=True)
    
    # Sort sections by ju_order
    sections_sorted = sorted(sections, key=lambda x: ju_order.get(x[0].replace("文子/", ""), ('99', ''))[0])
    
    for section_title, section_content in sections_sorted:
        ju_num = section_title.replace("文子/", "")
        if ju_num in ju_order:
            num, name = ju_order[ju_num]
            filename = f"{num}_{name}.tagged.md"
        else:
            filename = f"{ju_num}.tagged.md"
        
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(section_content)
        
        print(f"  Created: {output_path}")
    
    return len(sections_sorted)

def main():
    print("Processing Wen Zi...")
    wenzi_path = "chapters/wenzi/00_Wen_Zi.tagged.md"
    if os.path.exists(wenzi_path):
        with open(wenzi_path, 'r', encoding='utf-8') as f:
            content = f.read()
        count = split_wenzi(content)
        print(f"  Split into {count} chapters\n")
    else:
        print(f"  File not found: {wenzi_path}\n")
    
    print("Done!")

if __name__ == "__main__":
    main()
