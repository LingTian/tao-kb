#!/usr/bin/env python3
"""
Split Lie Zi and Wen Zi from single merged files into chapter-based files.
Following the same pattern as Zhuangzi.
"""

import os
import re

def split_by_section(content, file_prefix, output_dir):
    """
    Split content by ## headers and save as individual files.
    """
    # Match ## 列子/XXX篇 or ## 文子/卷 X
    section_pattern = re.compile(r'\n## (列子/[^#\n]+|文子/卷 [一二三四五六七八九十]+)')
    
    # Find all sections
    matches = list(section_pattern.finditer(content))
    
    if not matches:
        print(f"  No sections found in {file_prefix}")
        return 0
    
    output_dir = os.path.join("chapters", file_prefix)
    os.makedirs(output_dir, exist_ok=True)
    
    for i, match in enumerate(matches):
        section_title = match.group(1)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        
        section_content = content[start:end].strip()
        
        # Create filename from section title
        # 列子/仲尼篇 -> 04_Zhong_Ni_Pian.tagged.md
        # 文子/卷一 -> 01_Juan_Yi.tagged.md
        if section_title.startswith("列子/"):
            chapter_name = section_title.replace("列子/", "").replace("篇", "")
            # Convert Chinese numbers to digits
            chapter_map = {
                '天瑞': '01', '黃帝': '02', '周穆王': '03', '仲尼': '04',
                '湯問': '05', '力命': '06', '楊朱': '07', '說符': '08'
            }
            for cn, num in chapter_map.items():
                if cn in chapter_name:
                    filename = f"{num}_{cn}.tagged.md"
                    break
        else:  # 文子/卷 X
            ju_num = section_title.replace("文子/", "")
            # Convert Chinese numbers to digits
            ju_map = {
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
            if ju_num in ju_map:
                num, name = ju_map[ju_num]
                filename = f"{num}_{name}.tagged.md"
            else:
                filename = f"{ju_num}.tagged.md"
        
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(section_content)
        
        print(f"  Created: {output_path}")
    
    return len(matches)

def main():
    # Process Lie Zi
    print("Processing Lie Zi...")
    liezi_path = "chapters/liezi/00_Lie_Zi.tagged.md"
    if os.path.exists(liezi_path):
        with open(liezi_path, 'r', encoding='utf-8') as f:
            content = f.read()
        count = split_by_section(content, "liezi", "chapters/liezi")
        print(f"  Split into {count} chapters\n")
    else:
        print(f"  File not found: {liezi_path}\n")
    
    # Process Wen Zi
    print("Processing Wen Zi...")
    wenzi_path = "chapters/wenzi/00_Wen_Zi.tagged.md"
    if os.path.exists(wenzi_path):
        with open(wenzi_path, 'r', encoding='utf-8') as f:
            content = f.read()
        count = split_by_section(content, "wenzi", "chapters/wenzi")
        print(f"  Split into {count} chapters\n")
    else:
        print(f"  File not found: {wenzi_path}\n")
    
    print("Done! You can now remove the original merged files if needed.")

if __name__ == "__main__":
    main()
