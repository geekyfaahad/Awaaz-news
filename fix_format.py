"""Fix the broken _format_google_news_ask_ai_reply function."""

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the broken lines (1341-1352 area, 0-indexed: 1340-1351)
# The issue: line 1342 has "status_para_clean = status_para.strip()" inside "if not items:"
# and line 1343 has "return (" at wrong indent level

# Find the exact lines
fix_start = None
fix_end = None

for i, line in enumerate(lines):
    if 'status_para_clean = status_para.strip()' in line and i > 1300 and i < 1360:
        fix_start = i - 1  # The "if not items:" line before it
        print(f"Found status_para_clean at line {i+1}")
    if fix_start is not None and fix_end is None:
        # Find the closing ) of the return
        if line.strip() == ')' and i > fix_start + 5:
            fix_end = i + 1
            print(f"Found closing ) at line {i+1}")
            break

if fix_start is not None and fix_end is not None:
    print(f"Replacing lines {fix_start+1} to {fix_end}")
    
    new_block = [
        '    if not items:\n',
        '        return (\n',
        '            f"We ran the same Google News RSS search the app uses for articles.\\n\\n"\n',
        '            f"**Search used:** \\"{display_q}\\"\\n\\n"\n',
        '            "No headlines were returned (or the feed could not be read). "\n',
        "            \"That often means the topic isn't indexed with those exact words yet, or it's very niche. \"\n",
        '            "Try adding a location, organization name, or year.\\n\\n"\n',
        '            "**STATUS: Unverified**\\n"\n',
        '            "No corroboration from Google News in this search \\u2014 searching on X.com might yield more info."\n',
        '        )\n',
    ]
    
    lines[fix_start:fix_end] = new_block
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("SUCCESS: Fixed the broken if-not-items block")
else:
    print(f"ERROR: Could not find the broken block. fix_start={fix_start}, fix_end={fix_end}")
    # Debug: show lines around 1340
    for i in range(1338, min(1355, len(lines))):
        print(f"  {i+1}: {lines[i].rstrip()}")
