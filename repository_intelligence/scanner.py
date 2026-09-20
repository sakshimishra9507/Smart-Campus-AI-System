from pathlib import Path
from .models import RepositoryFile

DEFAULT_IGNORES = {".git", ".hg", ".svn", "__pycache__", ".venv", "venv", "node_modules", "dist", "build", ".next", "coverage"}

class RepositoryScanner:
    def __init__(self, ignore_names=None, max_file_size=2_000_000):
        self.ignore_names = set(ignore_names or DEFAULT_IGNORES)
        self.max_file_size = max_file_size

    def scan(self, root: str):
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")
        files, directories = [], set()
        for path in root_path.rglob("*"):
            if any(part in self.ignore_names for part in path.parts):
                continue
            rel = path.relative_to(root_path).as_posix()
            if path.is_dir():
                directories.add(rel)
                continue
            try:
                size = path.stat().st_size
                sample = path.read_bytes()[:4096]
                binary = b"\\x00" in sample
            except OSError:
                continue
            files.append(RepositoryFile(rel, size, None, binary))
            parent = Path(rel).parent.as_posix()
            while parent not in (".", ""):
                directories.add(parent)
                parent = Path(parent).parent.as_posix()
        return sorted(files, key=lambda x: x.path), sorted(directories)
