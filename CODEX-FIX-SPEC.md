# Codex Remediation Task: space-hog

You are tasked with remediating critical security and performance vulnerabilities in the `space-hog` repository. Apply the following fixes:

## 1. Eliminate Command Injection (RCE)
- **File:** `space_hog/safe_delete.py`
- **Issue:** The `move_to_trash` function uses string interpolation inside an AppleScript block (`osascript`) to delete files. This allows arbitrary code execution if a filename contains quotes or AppleScript commands.
- **Fix:** Replace the entire `osascript` block with the `send2trash` Python library. Add `send2trash` to `pyproject.toml` dependencies (e.g., `send2trash>=1.8.0`). Make sure to `import send2trash` and use `send2trash.send2trash(str(target))`.

## 2. Prevent Symlink Traversal (Arbitrary File Deletion)
- **File:** `space_hog/safe_delete.py` and `space_hog/scanners.py`
- **Issue:** Directory traversals (e.g., `target.iterdir()` or `rglob`) follow symlinks blindly. If a directory contains a symlink to `/usr/local`, the tool might delete system files.
- **Fix:** Add `is_symlink()` checks. For `safe_delete.py`'s `trash_contents`, skip items where `item.is_symlink()` is true and append a warning to the `errors` list.

## 3. Fix Unbounded Resource Consumption (Performance / DoS)
- **File:** `space_hog/scanners.py`
- **Issue:** `find_space_hogs` iterates over `SPACE_HOG_PATTERNS` and calls `root.rglob(pattern)` for each one (17 separate full-disk traversals). This takes `O(P * N)` time.
- **Fix:** Refactor `find_space_hogs` to use a single `os.walk(root)` pass. During the pass, check if the current directory name matches any key in `SPACE_HOG_PATTERNS`. If it does, calculate its size, add it to the results, and remove it from `dirnames` so `os.walk` doesn't recurse into it. Also, skip any symlinks using `os.path.islink`.

## 4. Fix Silent Exception Swallowing
- **File:** `space_hog/safe_delete.py`
- **Issue:** The `_record_removal` function has an empty `except Exception: pass` block.
- **Fix:** Change it to `except Exception as e: import logging; logging.warning(f"Failed to record removal: {e}")` to ensure failures are visible without crashing the app.

## 5. Prevent Docker Label Injection
- **File:** `space_hog/docker.py`
- **Issue:** `analyze_docker_volumes` parses project names from Docker labels and later these are embedded in suggested CLI commands without sanitization.
- **Fix:** Sanitize the extracted `project` variable by stripping control characters (e.g., using a regex like `re.sub(r'[\x00-\x1f\x7f]', '', text)`). Also, update `print_docker_analysis` to use `shlex.quote(proj)` when generating the `docker volume rm` suggestion.

Please thoroughly apply these changes. Ensure all code remains functional.
