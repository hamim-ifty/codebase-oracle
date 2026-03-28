import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import git

from app.config import get_settings


@dataclass
class Document:
    content: str
    metadata: dict = field(default_factory=dict)


class RepoLoader:
    def __init__(self):
        self.settings = get_settings()

    def load_from_url(self, repo_url: str) -> list[Document]:
        settings = self.settings
        repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
        clone_path = Path(settings.CLONE_DIR) / repo_name
        clone_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[loader] Cloning {repo_url} into {clone_path}")
        try:
            if clone_path.exists():
                shutil.rmtree(clone_path)
            git.Repo.clone_from(repo_url, clone_path, depth=1)
            documents = self._walk_and_read(clone_path, repo_name, source="github")
            print(f"[loader] Loaded {len(documents)} files from GitHub")
            return documents
        finally:
            if clone_path.exists():
                shutil.rmtree(clone_path)
                print(f"[loader] Cleaned up {clone_path}")

    def load_from_zip(self, zip_path: Path, project_name: str) -> list[Document]:
        settings = self.settings
        extract_dir = Path(settings.CLONE_DIR) / f"zip_{project_name}"
        extract_dir.parent.mkdir(parents=True, exist_ok=True)

        print(f"[loader] Extracting zip to {extract_dir}")
        try:
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                # Zip bomb check
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > 200 * 1024 * 1024:
                    raise ValueError("Zip file is too large (exceeds 200MB uncompressed)")
                zf.extractall(extract_dir)

            # Handle single root folder pattern (e.g. "my-repo-main/")
            entries = list(extract_dir.iterdir())
            if len(entries) == 1 and entries[0].is_dir():
                root_dir = entries[0]
                print(f"[loader] Detected single root folder: {root_dir.name}, using its contents")
            else:
                root_dir = extract_dir

            documents = self._walk_and_read(root_dir, project_name, source="upload")
            print(f"[loader] Loaded {len(documents)} files from zip")
            return documents
        finally:
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
                print(f"[loader] Cleaned up {extract_dir}")

    def _walk_and_read(self, root: Path, repo_name: str, source: str) -> list[Document]:
        settings = self.settings
        documents = []
        max_bytes = settings.MAX_FILE_SIZE_KB * 1024

        # Important files to always include even if extension not in list
        important_names = {
            "README.md", "Dockerfile", "package.json", "requirements.txt",
            "pyproject.toml", "tsconfig.json", "docker-compose.yml",
            "docker-compose.yaml", "Makefile", ".env.example",
        }

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune skip dirs in-place
            dirnames[:] = [
                d for d in dirnames if d not in settings.SKIP_DIRS
            ]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                ext = file_path.suffix.lower()
                is_important = filename in important_names

                if ext not in settings.SUPPORTED_EXTENSIONS and not is_important:
                    continue

                try:
                    file_size = file_path.stat().st_size
                    if file_size > max_bytes and not is_important:
                        print(f"[loader] Skipping {file_path} (too large: {file_size // 1024}KB)")
                        continue

                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if not content.strip():
                        continue

                    relative_path = str(file_path.relative_to(root))
                    documents.append(Document(
                        content=content,
                        metadata={
                            "repo_name": repo_name,
                            "file_path": relative_path,
                            "file_name": filename,
                            "file_extension": ext,
                            "source": source,
                        },
                    ))
                except Exception as e:
                    print(f"[loader] Could not read {file_path}: {e}")

        return documents
