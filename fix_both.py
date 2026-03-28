"""
Fix both broken functions:
1. Remove the misplaced 'if not items' block from _format_x_com_search_reply (lines 1325-1334)
2. Fix the broken 'if not items' in _format_google_news_ask_ai_reply (lines 1342-1353)
"""

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines before fix: {len(lines)}")

# === FIX 1: Remove misplaced block from _format_x_com_search_reply ===
# Find the "status_para_clean" return in the X function, followed by the misplaced "if not items:"
# The X function's status_para return ends, then there's a bogus "if not items:" block
# We need to find and remove lines 1325-1334 (the misplaced Google News block inside X function)

# Find the misplaced block - it has "if not items:" right after the X function's status_para
# but before _format_google_news_ask_ai_reply
fix1_start = None
fix1_end = None

for i, line in enumerate(lines):
    # Find the misplaced "if not items:" that references display_q inside the X function
    # It should be after the X function's status_para block and before _format_google_news_ask_ai_reply
    if i > 1310 and i < 1340 and line.strip() == 'if not items:':
        # Check if the next lines reference "Google News RSS"
        next_few = ''.join(lines[i:i+10])
        if 'Google News RSS search' in next_few:
            fix1_start = i
            print(f"FIX1: Found misplaced 'if not items:' at line {i+1}")
            # Find the closing ) of this return
            for j in range(i+1, min(i+15, len(lines))):
                if lines[j].strip() == ')':
                    fix1_end = j + 1
                    print(f"FIX1: Block ends at line {j+1}")
                    break
            break

# Also need to add the correct return for the X function
# The X function should end with:
#     status_para_clean = status_para.strip()
#     return (
#         f"{status_para_clean}\n\n"
#         f"**X.com search**..."
#     )
# But currently the return that follows status_para was already there.
# Let me check what comes after the misplaced block

if fix1_start is not None and fix1_end is not None:
    # Check if there's a blank line after the misplaced block
    print(f"FIX1: Removing lines {fix1_start+1} to {fix1_end}")
    # Remove the misplaced block
    del lines[fix1_start:fix1_end]
    print("FIX1: Done")
else:
    print("FIX1: No misplaced block found (may already be fixed)")

# Re-scan for the status_para_clean in X function to make sure its return is correct
# Also add the status_para_clean return for X function
for i, line in enumerate(lines):
    if 'status_para_clean = status_para.strip()' in line and i > 1280 and i < 1340:
        print(f"X function status_para_clean at line {i+1}")
        # Check next line has return with status_para_clean
        if 'status_para_clean' in lines[i+1]:
            print("  X return looks correct")
        break

# Now write intermediate state
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Re-read
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"\nTotal lines after FIX1: {len(lines)}")

# === FIX 2: Fix the broken _format_google_news_ask_ai_reply ===
# Find its "if not items:" block that has the broken status_para_clean reference

fix2_start = None
fix2_end = None

for i, line in enumerate(lines):
    if 'def _format_google_news_ask_ai_reply' in line:
        print(f"\nFIX2: Found function at line {i+1}")
        # Find "if not items:" after this
        for j in range(i+1, min(i+20, len(lines))):
            if lines[j].strip().startswith('if not items'):
                fix2_start = j
                print(f"FIX2: Found 'if not items:' at line {j+1}")
                # Find where this block ends
                for k in range(j+1, min(j+20, len(lines))):
                    stripped = lines[k].strip()
                    # The block ends when we hit a line at the same or lesser indent
                    # that doesn't belong to the return statement
                    if stripped == ')':
                        fix2_end = k + 1
                        print(f"FIX2: Block ends at line {k+1}")
                        break
                break
        break

if fix2_start is not None and fix2_end is not None:
    print(f"FIX2: Replacing lines {fix2_start+1} to {fix2_end}")
    
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
    
    lines[fix2_start:fix2_end] = new_block
    print("FIX2: Done")
else:
    print("FIX2: Could not find the broken block")

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\nTotal lines after FIX2: {len(lines)}")

# Verify syntax
import py_compile
try:
    py_compile.compile('app.py', doraise=True)
    print("\nSyntax check: OK")
except py_compile.PyCompileError as e:
    print(f"\nSyntax check FAILED: {e}")
