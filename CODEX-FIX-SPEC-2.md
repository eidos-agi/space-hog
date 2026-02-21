# Codex Remediation Task #2: space-hog

You are tasked with fixing the remaining architectural, security, and quality issues found in the post-Codex audit. Please carefully apply the following fixes:

## 1. Eliminate `shell=True` in `stats.py`
- **File:** `space_hog/stats.py`
- **Issue:** `run_cleanup` executes `subprocess.run(command, shell=True)`. This bypasses all the safe deletion logic and leaves the app vulnerable to command injection.
- **Fix:** Remove `shell=True`. Change the signature of `run_cleanup` to accept a list of strings if necessary, or use `shlex.split(command)` to parse the string into a list before passing it to `subprocess.run`. Ensure that `shell=False` is used implicitly or explicitly.

## 2. Fix AppleScript Injection in `memory.py`
- **File:** `space_hog/memory.py`
- **Issue:** `remove_login_item` interpolates `app_name` into an AppleScript block executed via `osascript`.
- **Fix:** Strictly sanitize `app_name` before interpolation using an allowlist regex (e.g., `import re; app_name = re.sub(r'[^a-zA-Z0-9 ._-]', '', app_name)`) to prevent AppleScript injection.

## 3. Fix TOCTOU Race and State-After-Mutation in `safe_delete.py`
- **File:** `space_hog/safe_delete.py`
- **Issue 1:** `target.is_file()` is called *after* `send2trash.send2trash(str(target))`, which fails because the file is already moved. This causes all deleted files to be incorrectly logged as directories.
- **Issue 2:** The `is_symlink()` check is separated from `send2trash`, creating a TOCTOU race.
- **Fix:** In `move_to_trash()`, evaluate and store `is_file = target.is_file()` *before* calling `send2trash`. Pass `is_file` to `_record_removal` (e.g., `'file' if is_file else 'directory'`). If possible, ensure no symlinks are passed to `send2trash` by checking `target.is_symlink()` immediately before, though the primary fix is the `is_file` order.

## 4. Fix Symlink Traversal in `utils.py`
- **File:** `space_hog/utils.py`
- **Issue:** `get_dir_size` uses `path.rglob('*')`, which follows directory symlinks on Python < 3.13.
- **Fix:** Rewrite `get_dir_size` to use `os.walk(path, topdown=True, followlinks=False)` or `os.scandir` to safely traverse the directory without following symlinks. Sum the sizes of the files found.

## 5. Improve Docker Label Sanitization
- **File:** `space_hog/docker.py`
- **Issue:** `_sanitize_label_text` only strips control characters, allowing shell metacharacters like `;`, `|`, `$()`.
- **Fix:** Change the regex to a strict allowlist: `cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '', text).strip()`.

## 6. Fix `os.walk` Issues in `scanners.py`
- **File:** `space_hog/scanners.py`
- **Issue 1:** Missing `onerror` handler in `os.walk`, causing `PermissionError`s to silently abort the entire scan.
- **Fix 1:** Add an `onerror` callback to `os.walk` (e.g., `onerror=lambda e: None` or log a warning) so traversals continue past inaccessible directories.
- **Issue 2:** The pruning logic (`dirnames[:] = []`) prevents finding nested space hogs (e.g., `node_modules` inside `.venv`).
- **Fix 2:** Instead of clearing `dirnames` completely, selectively remove the matched directory name from `dirnames` or adjust the logic so it can still process independent nested hogs.

## 7. Fix Silent Exception Swallowing
- **File:** Across codebase (e.g., `safe_delete.py`, `utils.py`, `caches.py`).
- **Issue:** Too many `except Exception: pass` blocks hide errors.
- **Fix:** Where appropriate, change `except Exception:` to `except Exception as e: import logging; logging.warning(f"Error: {e}")` to ensure errors are at least visible.

## 8. Fix Build Metadata and Dependencies
- **File:** `pyproject.toml` and `space_hog/__init__.py`
- **Issue:** Version mismatch (`0.2.0` vs `0.5.0`). Missing `pytest` and `docker` dependencies.
- **Fix:** Update `pyproject.toml` version to `0.5.0` to match `__init__.py`. Add `docker` to `dependencies`. Add `[project.optional-dependencies]` with `test = ["pytest"]`.

Apply these fixes comprehensively and carefully.
