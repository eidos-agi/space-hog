"""Constants and configuration for Space Hog."""

# Common space hog directory patterns
SPACE_HOG_PATTERNS = {
    'node_modules': 'Node.js dependencies',
    '.git': 'Git repositories',
    '__pycache__': 'Python cache',
    '.pytest_cache': 'Pytest cache',
    'venv': 'Python virtual environments',
    '.venv': 'Python virtual environments',
    'env': 'Python virtual environments',
    '.tox': 'Tox testing environments',
    'target': 'Rust/Maven build artifacts',
    'build': 'Build directories',
    'dist': 'Distribution directories',
    '.gradle': 'Gradle cache',
    '.cargo': 'Cargo cache',
    'Pods': 'CocoaPods dependencies',
    'DerivedData': 'Xcode derived data',
    '.nuget': 'NuGet packages',
    'vendor': 'Vendor dependencies',
}

# Cache locations to scan
CACHE_LOCATIONS = [
    # System caches
    ('~/Library/Caches', 'Application caches'),
    ('~/.cache', 'General cache'),

    # AI tools (often huge!)
    ('~/.ollama', 'Ollama models'),
    ('~/.codeium', 'Codeium AI cache'),
    ('~/.gemini', 'Gemini CLI'),
    ('~/.claude', 'Claude Code cache'),

    # Dev tools
    ('~/Library/Application Support/Code/Cache', 'VS Code cache'),
    ('~/Library/Application Support/Code/CachedData', 'VS Code cached data'),
    ('~/.vscode', 'VS Code extensions'),
    ('~/Library/Application Support/Slack/Cache', 'Slack cache'),
    ('~/Library/Application Support/discord/Cache', 'Discord cache'),
    ('~/Library/Application Support/Google/Chrome/Default/Cache', 'Chrome cache'),

    # Xcode
    ('~/Library/Developer/Xcode/DerivedData', 'Xcode derived data'),
    ('~/Library/Developer/Xcode/Archives', 'Xcode archives'),
    ('~/Library/Developer/Xcode/iOS DeviceSupport', 'Xcode device symbols'),
    ('~/Library/Developer/CoreSimulator', 'iOS Simulators'),

    # Package managers
    ('~/.npm', 'NPM cache'),
    ('~/.yarn/cache', 'Yarn cache'),
    ('~/.pyenv', 'Python versions (pyenv)'),
    ('~/.local', 'pip/local installs'),
    ('~/.cargo', 'Rust packages'),
    ('~/.rustup', 'Rust toolchain'),

    # Other dev
    ('~/.mozbuild', 'Mozilla build cache'),
    ('~/.docker', 'Docker data'),
    ('~/Library/Containers/com.docker.docker', 'Docker Desktop'),
    ('~/Library/Containers/com.microsoft.teams2', 'Microsoft Teams'),
]

# Maps cache paths to their cleanup info keys
CACHE_TO_CLEANUP = {
    '~/.Trash': 'trash',
    '~/.npm': 'npm',
    '~/.yarn/cache': 'yarn',
    '~/Library/Caches': 'library_caches',
    '~/.cache': 'dot_cache',
    '~/Library/Developer/CoreSimulator': 'simulators',
    '~/Library/Developer/Xcode/DerivedData': 'xcode_derived',
    '~/Library/Developer/Xcode/iOS DeviceSupport': 'xcode_device_support',
    '~/Library/Containers/com.docker.docker': 'docker',
    '~/.docker': 'docker',
    '~/.ollama': 'ollama',
    '~/.cargo': 'cargo',
    '~/.pyenv': 'pyenv',
}

# Cleanup commands with safety information
CLEANUP_INFO = {
    'trash': {
        'command': 'rm -rf ~/.Trash/*',
        'name': 'Empty Trash',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Permanently deletes files already in your Trash.',
        'side_effects': ['Files cannot be recovered after this'],
        'recommendation': 'Safe to run. Review Trash contents first if unsure.',
    },
    'npm': {
        'command': 'npm cache clean --force && rm -rf ~/.npm/_npx/*',
        'name': 'Clear NPM Cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes cached npm packages and npx downloads.',
        'side_effects': [
            'Next npm install will re-download packages (slightly slower)',
            'Next npx command will re-download the tool',
            'No impact on installed node_modules',
        ],
        'recommendation': 'Safe to run. The _npx cache is often the biggest part.',
    },
    'docker': {
        'command': 'docker system prune -a',
        'name': 'Clear Docker',
        'risk': 'MODERATE',
        'risk_score': 2,
        'description': 'Removes stopped containers, unused networks, and ALL unused images.',
        'side_effects': [
            'Must re-pull/rebuild images not currently in use',
            'Build cache cleared (slower first builds)',
            'Does NOT delete volumes (data is safe)',
            'NOTE: VM disk (Docker.raw) does NOT shrink automatically!',
        ],
        'recommendation': 'Safe for dev machines. To reclaim VM disk space: Docker Desktop → Settings → Resources → reduce Virtual disk limit, or factory reset.',
    },
    'library_caches': {
        'command': 'rm -rf ~/Library/Caches/*',
        'name': 'Clear User Caches',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes application cache files. macOS regenerates them automatically.',
        'side_effects': [
            'Apps may be slower on first launch while rebuilding cache',
            'May need to re-login to some apps',
            'Some apps store non-cache data here (rare)',
        ],
        'recommendation': 'Generally safe. Consider backing up first if concerned.',
    },
    'dot_cache': {
        'command': 'rm -rf ~/.cache/*',
        'name': 'Clear ~/.cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes general cache directory used by CLI tools and apps.',
        'side_effects': [
            'Tools rebuild caches on next use',
            'May need to re-authenticate some CLI tools',
        ],
        'recommendation': 'Safe to run. Data regenerates automatically.',
    },
    'simulators': {
        'command': 'xcrun simctl delete unavailable',
        'name': 'Delete Unavailable iOS Simulators',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes simulators incompatible with current Xcode version.',
        'side_effects': ['Only removes simulators you cannot use anyway'],
        'recommendation': 'Safe to run. Also try "xcrun simctl runtime delete unavailable" for runtimes.',
    },
    'xcode_derived': {
        'command': 'rm -rf ~/Library/Developer/Xcode/DerivedData/*',
        'name': 'Clear Xcode DerivedData',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes Xcode build artifacts and indexes.',
        'side_effects': [
            'Next build will be slower (full rebuild)',
            'Xcode will re-index projects',
        ],
        'recommendation': 'Safe to run. Common fix for Xcode build issues.',
    },
    'yarn': {
        'command': 'yarn cache clean',
        'name': 'Clear Yarn Cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Removes cached yarn packages.',
        'side_effects': ['Next yarn install will re-download packages'],
        'recommendation': 'Safe to run.',
    },
    'ollama': {
        'command': 'ollama list  # then: ollama rm <model>',
        'name': 'Ollama Models',
        'risk': 'MODERATE',
        'risk_score': 2,
        'description': 'Large language models downloaded for local AI. Each model is 2-40+ GB.',
        'side_effects': [
            'Must re-download models if you remove them',
            'Run "ollama list" to see models first',
        ],
        'recommendation': 'Remove unused models with "ollama rm <model>". Keep models you use regularly.',
    },
    'xcode_device_support': {
        'command': 'rm -rf ~/Library/Developer/Xcode/iOS\\ DeviceSupport/*',
        'name': 'Xcode Device Symbols',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Debug symbols for physical iOS devices. Re-downloads when you connect a device.',
        'side_effects': [
            'First debug on each device will be slower (downloads symbols)',
        ],
        'recommendation': 'Safe to delete. Symbols re-download automatically when needed.',
    },
    'cargo': {
        'command': 'cargo cache -a  # or: rm -rf ~/.cargo/registry/cache',
        'name': 'Rust Cargo Cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Cached Rust crate downloads.',
        'side_effects': ['Next cargo build will re-download crates'],
        'recommendation': 'Safe to run. Install cargo-cache for better control: cargo install cargo-cache',
    },
    'pyenv': {
        'command': 'pyenv versions  # then: pyenv uninstall <version>',
        'name': 'Python Versions (pyenv)',
        'risk': 'MODERATE',
        'risk_score': 2,
        'description': 'Full Python installations managed by pyenv.',
        'side_effects': [
            'Must reinstall Python versions if you remove them',
            'Projects using removed versions will break',
        ],
        'recommendation': 'Run "pyenv versions" to see installed. Remove old versions you don\'t use.',
    },
}
