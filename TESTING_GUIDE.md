# Testing Guide for Incremental Updates

## Issue You Encountered

### What Happened
1. **First Run**: Generated diagram with wrong values (Size: 1000, Overlap: 200) instead of actual code values (475, 50)
2. **Second Run**: After changing chunk_size to 800, the incremental update showed the OLD values (475, 50) instead of the NEW value (800)

### Root Cause
The git diff was including a `.md` documentation file that was added, not the actual Python code changes. The incremental update was analyzing the wrong file.

### Fix Applied
Updated `workflow_utils.py` to filter git diff to **only include code files** (`.py`, `.js`, `.ts`, `.java`), excluding documentation files like `.md`, `.txt`, etc.

---

## How to Test Properly

### Prerequisites
```bash
# Set your API key
$env:OPENAI_API_KEY = "sk-your-api-key"

# Navigate to your project
cd "C:\Users\T773534\Downloads\gen-ai-data-ingestion-1\gen-ai-data-ingestion\src\aia_koodo_pipeline"
```

### Test Scenario 1: Fresh Start (Full Mode)

```bash
# Step 1: Remove existing diagram (if any)
rm diagram.html

# Step 2: Generate initial diagram
python c:/Users/T773534/Desktop/mermaid-gen/main_incremental.py . --mode full --debug

# Step 3: Verify the diagram has CORRECT values from your code
# Open diagram.html and check if chunk_size matches your actual code (475)

# Step 4: Commit the diagram
git add diagram.html
git commit -m "Initial diagram with correct values"
```

### Test Scenario 2: Incremental Update (Code Change)

```bash
# Step 1: Make a REAL code change (not documentation)
# Edit your Python file that contains chunk_size
# For example, change chunk_size from 475 to 800

# Step 2: Commit ONLY the Python file
git add your_pipeline_file.py
git commit -m "Update chunk_size to 800"

# Step 3: Run incremental update
python c:/Users/T773534/Desktop/mermaid-gen/main_incremental.py . --mode incremental --debug

# Step 4: Check the debug output
cat incremental_update_debug.txt

# You should see:
# - Affected Nodes: ['B'] (or whatever node has chunking)
# - DIFF CONTEXT should show your Python file changes, NOT .md files
# - The updated diagram should show Size: 800

# Step 5: Verify the diagram
# Open diagram.html and confirm chunk_size is now 800
```

### Test Scenario 3: Documentation Changes (Should Be Ignored)

```bash
# Step 1: Make a documentation change
echo "# Updated docs" >> README.md
git add README.md
git commit -m "Update documentation"

# Step 2: Run incremental update
python c:/Users/T773534/Desktop/mermaid-gen/main_incremental.py . --mode incremental --debug

# Expected output:
# "⚠️  No code file changes detected, checking all files..."
# OR
# "No changes detected" (if the .md file doesn't affect the diagram)

# The diagram should remain unchanged
```

---

## Understanding the Debug Output

### Good Debug Output (After Fix)
```
================================================================================
DIFF CONTEXT:
================================================================================

diff --git a/src/pipeline.py b/src/pipeline.py
index abc123..def456 100644
--- a/src/pipeline.py
+++ b/src/pipeline.py
@@ -10,7 +10,7 @@
 
 # Chunking configuration
-chunk_size = 475
+chunk_size = 800
 chunk_overlap = 50
```

This shows:
- ✅ Python file changes
- ✅ Actual code diff
- ✅ Clear before/after values

### Bad Debug Output (Before Fix)
```
================================================================================
DIFF CONTEXT:
================================================================================

diff --git a/KOODO_PIPELINE_DIAGRAM.md b/KOODO_PIPELINE_DIAGRAM.md
new file mode 100644
index 00000000..e65a268f
--- /dev/null
+++ b/KOODO_PIPELINE_DIAGRAM.md
@@ -0,0 +1,290 @@
+# Koodo Pipeline - High-Level Architecture Diagram
+...
```

This shows:
- ❌ Documentation file (.md)
- ❌ Not actual code changes
- ❌ LLM can't extract real values from this

---

## Complete Test Workflow

### Clean Slate Test

```bash
# 1. Navigate to your project
cd "C:\Users\T773534\Downloads\gen-ai-data-ingestion-1\gen-ai-data-ingestion\src\aia_koodo_pipeline"

# 2. Remove old diagram and debug files
rm diagram.html, diff_context.txt, incremental_update_debug.txt, ast_debug_output.txt

# 3. Generate fresh diagram
python c:/Users/T773534/Desktop/mermaid-gen/main_incremental.py . --mode full --debug

# 4. Check if values are correct
# Open diagram.html - should show chunk_size: 475 (your actual value)

# 5. Commit the diagram
git add diagram.html
git commit -m "Fresh diagram with correct values"

# 6. Make a code change
# Edit your Python file: change chunk_size from 475 to 800

# 7. Commit the code change
git add src/your_file.py
git commit -m "Increase chunk_size to 800"

# 8. Run incremental update
python c:/Users/T773534/Desktop/mermaid-gen/main_incremental.py . --mode incremental --debug

# 9. Verify the update
cat incremental_update_debug.txt
# Should show:
# - Affected Nodes: ['B']
# - DIFF showing chunk_size: 475 -> 800
# - Impact: low or medium

# 10. Check the diagram
# Open diagram.html - should now show chunk_size: 800
```

---

## Troubleshooting

### Issue: "No changes detected"
**Cause**: No Python files were modified
**Solution**: Make sure you're editing `.py` files, not `.md` or `.txt` files

### Issue: Diagram shows wrong values
**Cause**: Initial diagram was generated incorrectly
**Solution**: 
1. Delete `diagram.html`
2. Run with `--mode full` to regenerate from scratch
3. Verify values are correct before committing

### Issue: Incremental update not working
**Cause**: Various reasons
**Solution**: Check `incremental_update_debug.txt` for:
- Which nodes were affected
- What the diff context shows
- Impact percentage

### Issue: "Could not parse existing diagram"
**Cause**: diagram.html is corrupted or invalid
**Solution**:
1. Delete `diagram.html`
2. Run with `--mode full`

---

## What Changed in the Fix

### Before (Broken)
```python
# workflow_utils.py - generate_diff_context()
result = subprocess.run(
    ["git", "diff", base_ref, "HEAD", "--unified=5"],
    # This included ALL files (.md, .txt, .py, etc.)
)
```

### After (Fixed)
```python
# workflow_utils.py - generate_diff_context()
result = subprocess.run(
    ["git", "diff", base_ref, "HEAD", "--unified=5", 
     "--", "*.py", "*.js", "*.ts", "*.java"],
    # Now only includes code files
)
```

This ensures the LLM only sees actual code changes, not documentation changes.

---

## Expected Behavior

### Full Mode
- Scans all Python files
- Extracts actual values from code
- Generates complete diagram
- **Use when**: First time or major refactor

### Incremental Mode
- Detects changed Python files only
- Compares with existing diagram
- Updates only affected nodes
- **Use when**: Small code changes

### Auto Mode (Recommended)
- Detects if diagram exists
- Chooses incremental or full automatically
- Falls back to full if needed
- **Use when**: You want it to "just work"

---

## Success Criteria

After the fix, you should see:

1. ✅ Initial diagram has correct values from your code
2. ✅ Code changes are detected (not .md files)
3. ✅ Incremental updates modify only affected nodes
4. ✅ Updated diagram reflects new values
5. ✅ Debug output shows Python file diffs, not .md files

---

## Quick Reference

```bash
# Generate initial diagram
python main_incremental.py . --mode full

# Update after code changes
python main_incremental.py . --mode incremental --debug

# Auto-detect mode
python main_incremental.py . --mode auto --debug

# Force full regeneration
python main_incremental.py . --force-full
```
