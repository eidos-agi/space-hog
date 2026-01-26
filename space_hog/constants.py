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
    ('~/Library/Logs', 'User log files'),

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
    ('~/Library/Application Support/Firefox/Profiles', 'Firefox profiles/cache'),
    ('~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Cache', 'Brave cache'),

    # Xcode
    ('~/Library/Developer/Xcode/DerivedData', 'Xcode derived data'),
    ('~/Library/Developer/Xcode/Archives', 'Xcode archives'),
    ('~/Library/Developer/Xcode/iOS DeviceSupport', 'Xcode device symbols'),
    ('~/Library/Developer/CoreSimulator', 'iOS Simulators'),

    # Package managers
    ('~/.npm', 'NPM cache'),
    ('~/.yarn/cache', 'Yarn cache'),
    ('~/.pnpm-store', 'pnpm store'),
    ('~/.bun/install/cache', 'Bun package cache'),
    ('~/.pyenv', 'Python versions (pyenv)'),
    ('~/.local', 'pip/local installs'),
    ('~/.cargo', 'Rust packages'),
    ('~/.rustup', 'Rust toolchain'),
    ('~/.gradle', 'Gradle cache'),
    ('~/.m2', 'Maven repository'),
    ('~/.cocoapods', 'CocoaPods cache'),

    # iOS/Mobile backups (often HUGE)
    ('~/Library/Application Support/MobileSync/Backup', 'iOS device backups'),

    # Mail
    ('~/Library/Mail', 'Mail data and attachments'),
    ('~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads', 'Mail downloads'),

    # Photos
    ('~/Library/Containers/com.apple.Photos/Data/Library', 'Photos library cache'),

    # Other dev
    ('~/.mozbuild', 'Mozilla build cache'),
    ('~/.docker', 'Docker data'),
    ('~/Library/Containers/com.docker.docker', 'Docker Desktop'),
    ('~/Library/Containers/com.microsoft.teams2', 'Microsoft Teams'),
    ('~/Library/Group Containers/group.com.apple.notes', 'Apple Notes data'),
]

# Maps cache paths to their cleanup info keys
CACHE_TO_CLEANUP = {
    '~/.Trash': 'trash',
    '~/.npm': 'npm',
    '~/.yarn/cache': 'yarn',
    '~/.pnpm-store': 'pnpm',
    '~/.bun/install/cache': 'bun',
    '~/Library/Caches': 'library_caches',
    '~/.cache': 'dot_cache',
    '~/Library/Logs': 'user_logs',
    '~/Library/Developer/CoreSimulator': 'simulators',
    '~/Library/Developer/Xcode/DerivedData': 'xcode_derived',
    '~/Library/Developer/Xcode/iOS DeviceSupport': 'xcode_device_support',
    '~/Library/Containers/com.docker.docker': 'docker',
    '~/.docker': 'docker',
    '~/.ollama': 'ollama',
    '~/.cargo': 'cargo',
    '~/.pyenv': 'pyenv',
    '~/.gradle': 'gradle',
    '~/.m2': 'maven',
    '~/.cocoapods': 'cocoapods',
    '~/Library/Application Support/MobileSync/Backup': 'ios_backups',
    '~/Library/Mail': 'mail',
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
    'pnpm': {
        'command': 'pnpm store prune',
        'name': 'pnpm Store',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'pnpm global content-addressable store.',
        'side_effects': ['Removes packages not referenced by any project'],
        'recommendation': 'Safe to run. pnpm re-downloads packages on next install.',
    },
    'bun': {
        'command': 'rm -rf ~/.bun/install/cache/*',
        'name': 'Bun Package Cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Cached packages downloaded by Bun.',
        'side_effects': ['Next bun install will re-download packages'],
        'recommendation': 'Safe to run.',
    },
    'user_logs': {
        'command': 'rm -rf ~/Library/Logs/*',
        'name': 'User Log Files',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Application log files. Usually not needed after debugging.',
        'side_effects': ['Lose historical logs for debugging'],
        'recommendation': 'Safe to clear. Apps recreate logs as needed.',
    },
    'gradle': {
        'command': 'rm -rf ~/.gradle/caches/*',
        'name': 'Gradle Cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Cached Gradle builds and downloaded dependencies.',
        'side_effects': ['Next build will re-download dependencies'],
        'recommendation': 'Safe to run. Consider keeping ~/.gradle/wrapper.',
    },
    'maven': {
        'command': 'rm -rf ~/.m2/repository/*',
        'name': 'Maven Repository',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Local Maven repository with downloaded artifacts.',
        'side_effects': ['Next build will re-download dependencies'],
        'recommendation': 'Safe to run.',
    },
    'cocoapods': {
        'command': 'pod cache clean --all',
        'name': 'CocoaPods Cache',
        'risk': 'SAFE',
        'risk_score': 1,
        'description': 'Cached CocoaPods specifications and downloads.',
        'side_effects': ['Next pod install will re-download pods'],
        'recommendation': 'Safe to run.',
    },
    'ios_backups': {
        'command': 'ls -la ~/Library/Application\\ Support/MobileSync/Backup/  # Delete via Finder > iPhone > Manage Backups',
        'name': 'iOS Device Backups',
        'risk': 'CAUTION',
        'risk_score': 3,
        'description': 'Full backups of iPhones/iPads. Can be 20-100+ GB each.',
        'side_effects': [
            'CANNOT recover device from deleted backup',
            'May lose photos, messages, app data not in iCloud',
        ],
        'recommendation': 'Review in Finder > iPhone > Manage Backups. Delete old device backups you no longer need.',
    },
    'mail': {
        'command': 'ls -la ~/Library/Mail/  # Clean via Mail.app > Mailbox > Erase Deleted Items',
        'name': 'Mail Data',
        'risk': 'CAUTION',
        'risk_score': 3,
        'description': 'Local email data including attachments. Can be very large.',
        'side_effects': [
            'Mail.app manages this - manual deletion may corrupt database',
            'Attachments re-download from server (if IMAP)',
        ],
        'recommendation': 'Use Mail.app > Mailbox > Erase Deleted Items. Or rebuild mailbox.',
    },
}
