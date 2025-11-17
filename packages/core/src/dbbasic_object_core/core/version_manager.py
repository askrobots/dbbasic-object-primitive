"""
Version Manager

Manages versions of objects (endpoints, data, code).

Every change is versioned:
- Before modification, save current version
- Store metadata in TSV (timestamp, author, message, hash)
- Store content in separate file (v1.txt, v2.txt, etc.)
- Can retrieve any historical version
- Can rollback to previous version

Design:
- versions/{object_id}/metadata.tsv - Version metadata
- versions/{object_id}/v1.txt - Version 1 content
- versions/{object_id}/v2.txt - Version 2 content
- etc.
"""

import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import csv


class VersionError(Exception):
    """Base exception for version-related errors"""
    pass


class VersionNotFoundError(VersionError):
    """Raised when version doesn't exist"""
    pass


class VersionManager:
    """
    Manages versions of objects.

    Each object has its own version history stored in:
    - versions/{object_id}/metadata.tsv
    - versions/{object_id}/v{N}.txt
    """

    def __init__(self, base_dir: Path | str):
        """
        Initialize version manager.

        Args:
            base_dir: Base directory for version storage
        """
        self.base_dir = Path(base_dir)
        self.versions_dir = self.base_dir / 'versions'
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def save_version(
        self,
        object_id: str,
        content: str,
        author: str,
        message: str,
    ) -> int:
        """
        Save a new version of an object.

        Args:
            object_id: ID of the object (e.g., 'hello', 'calculator')
            content: The content to version
            author: Who made this change
            message: Commit message

        Returns:
            The version ID (1, 2, 3, etc.)
        """
        # Create object's version directory
        obj_dir = self.versions_dir / object_id
        obj_dir.mkdir(parents=True, exist_ok=True)

        # Compute hash of content
        content_hash = self._compute_hash(content)

        # Get next version ID
        version_id = self._get_next_version_id(object_id)

        # Get timestamp
        timestamp = datetime.now().isoformat()

        # Save content to file
        content_file = obj_dir / f'v{version_id}.txt'
        content_file.write_text(content)

        # Save metadata to TSV
        metadata_file = obj_dir / 'metadata.tsv'
        is_new_file = not metadata_file.exists()

        with open(metadata_file, 'a', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['version_id', 'timestamp', 'author', 'message', 'hash'],
                delimiter='\t',
            )

            if is_new_file:
                writer.writeheader()

            writer.writerow({
                'version_id': version_id,
                'timestamp': timestamp,
                'author': author,
                'message': message,
                'hash': content_hash,
            })

        return version_id

    def get_version(self, object_id: str, version_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific version of an object.

        Args:
            object_id: ID of the object
            version_id: Version ID to retrieve (None = latest)

        Returns:
            Dictionary with version data, or None if not found
        """
        obj_dir = self.versions_dir / object_id

        if not obj_dir.exists():
            return None

        # Get metadata
        metadata_file = obj_dir / 'metadata.tsv'
        if not metadata_file.exists():
            return None

        # Read all versions
        versions = []
        with open(metadata_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                row['version_id'] = int(row['version_id'])
                versions.append(row)

        if not versions:
            return None

        # Find the version
        if version_id is None:
            # Get latest
            target_version = versions[-1]
        else:
            # Find specific version
            target_version = None
            for v in versions:
                if v['version_id'] == version_id:
                    target_version = v
                    break

            if target_version is None:
                return None

        # Read content
        content_file = obj_dir / f"v{target_version['version_id']}.txt"
        if not content_file.exists():
            return None

        content = content_file.read_text()

        # Return version with content
        return {
            **target_version,
            'content': content,
        }

    def get_history(
        self,
        object_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get version history for an object.

        Args:
            object_id: ID of the object
            limit: Maximum number of versions to return
            offset: Number of versions to skip (from most recent)

        Returns:
            List of version metadata (WITHOUT content)
        """
        obj_dir = self.versions_dir / object_id

        if not obj_dir.exists():
            return []

        metadata_file = obj_dir / 'metadata.tsv'
        if not metadata_file.exists():
            return []

        # Read all versions
        versions = []
        with open(metadata_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                row['version_id'] = int(row['version_id'])
                versions.append(row)

        if not versions:
            return []

        # Reverse (most recent first)
        versions.reverse()

        # Apply offset and limit
        if offset > 0:
            versions = versions[offset:]

        if limit is not None:
            versions = versions[:limit]

        return versions

    def rollback(
        self,
        object_id: str,
        to_version: int,
        author: str,
        message: str,
    ) -> int:
        """
        Rollback to a previous version.

        This creates a NEW version with the content from the old version.
        History is preserved (not deleted).

        Args:
            object_id: ID of the object
            to_version: Version ID to rollback to
            author: Who is performing the rollback
            message: Rollback message

        Returns:
            The new version ID

        Raises:
            VersionNotFoundError: If to_version doesn't exist
        """
        # Get the version to rollback to
        old_version = self.get_version(object_id, to_version)

        if old_version is None:
            raise VersionNotFoundError(f"Version {to_version} not found for object {object_id}")

        # Save a new version with the old content
        new_version_id = self.save_version(
            object_id=object_id,
            content=old_version['content'],
            author=author,
            message=message,
        )

        return new_version_id

    def _get_next_version_id(self, object_id: str) -> int:
        """Get the next version ID for an object"""
        obj_dir = self.versions_dir / object_id
        metadata_file = obj_dir / 'metadata.tsv'

        if not metadata_file.exists():
            return 1

        # Read existing versions
        with open(metadata_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            versions = list(reader)

        if not versions:
            return 1

        # Get max version ID and add 1
        max_id = max(int(v['version_id']) for v in versions)
        return max_id + 1

    def _compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
