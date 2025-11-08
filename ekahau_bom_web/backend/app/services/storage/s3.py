"""S3 storage backend implementation."""

import io
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.services.storage.base import StorageBackend, StorageError


class S3Storage(StorageBackend):
    """AWS S3 storage implementation.

    Compatible with:
    - AWS S3
    - MinIO
    - Wasabi
    - DigitalOcean Spaces
    - Dell EMC ECS
    - IBM Cloud Object Storage
    - Any S3-compatible storage
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        use_ssl: bool = True,
        verify: bool | str = True,
        ca_bundle: str | None = None,
    ):
        """Initialize S3 storage.

        Args:
            bucket: S3 bucket name (must already exist)
            region: AWS region or provider-specific region
            access_key: AWS access key ID (uses env/IAM if None)
            secret_key: AWS secret access key (uses env/IAM if None)
            endpoint_url: Custom endpoint for MinIO/Corporate S3 (None = AWS)
            use_ssl: Use HTTPS (default: True)
            verify: Verify SSL certificates (bool) or path to CA bundle (str)
            ca_bundle: Path to custom CA certificate bundle (overrides verify)

        Raises:
            StorageError: If credentials invalid or bucket not accessible
        """
        self.bucket = bucket

        # Use ca_bundle if provided, otherwise use verify
        verify_param = ca_bundle if ca_bundle else verify

        # Create S3 client
        try:
            self.s3 = boto3.client(
                "s3",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint_url,
                use_ssl=use_ssl,
                verify=verify_param,  # Can be bool or path to CA bundle
            )
        except NoCredentialsError as e:
            raise StorageError(f"AWS credentials not found: {e}") from e

        # Verify bucket exists and is accessible
        try:
            self.s3.head_bucket(Bucket=bucket)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                raise StorageError(f"Bucket '{bucket}' not found") from e
            else:
                raise StorageError(f"Cannot access bucket '{bucket}': {e}") from e

    def _get_s3_key(self, project_id: UUID, file_path: str = "") -> str:
        """Get S3 key for file.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            S3 key (e.g., "projects/uuid/reports/file.csv")
        """
        base = f"projects/{project_id}"
        return f"{base}/{file_path}" if file_path else base

    def save_file(self, project_id: UUID, file_path: str, content: bytes | BinaryIO) -> str:
        """Save file to S3.

        Args:
            project_id: Project UUID
            file_path: Relative file path
            content: File content as bytes or file-like object

        Returns:
            S3 URI (e.g., "s3://bucket/projects/uuid/file.txt")

        Raises:
            StorageError: If upload fails
        """
        s3_key = self._get_s3_key(project_id, file_path)

        try:
            if isinstance(content, bytes):
                self.s3.put_object(Bucket=self.bucket, Key=s3_key, Body=content)
            else:
                self.s3.upload_fileobj(content, self.bucket, s3_key)

            return f"s3://{self.bucket}/{s3_key}"

        except ClientError as e:
            raise StorageError(f"Failed to save to S3: {e}") from e

    def get_file(self, project_id: UUID, file_path: str) -> bytes:
        """Get file from S3.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If download fails
        """
        s3_key = self._get_s3_key(project_id, file_path)

        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
            return response["Body"].read()

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {file_path}") from e
            else:
                raise StorageError(f"Failed to get from S3: {e}") from e

    def delete_project(self, project_id: UUID) -> bool:
        """Delete all files in project (S3 prefix).

        Args:
            project_id: Project UUID

        Returns:
            True if successful

        Raises:
            StorageError: If deletion fails
        """
        prefix = self._get_s3_key(project_id) + "/"

        try:
            # List all objects with prefix
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            objects_to_delete = []
            for page in pages:
                if "Contents" in page:
                    objects_to_delete.extend([{"Key": obj["Key"]} for obj in page["Contents"]])

            # Delete in batches (S3 limit: 1000 per request)
            if objects_to_delete:
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i : i + 1000]
                    self.s3.delete_objects(Bucket=self.bucket, Delete={"Objects": batch})

            return True

        except ClientError as e:
            raise StorageError(f"Failed to delete project from S3: {e}") from e

    def delete_file(self, project_id: UUID, file_path: str) -> bool:
        """Delete specific file from S3.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            True if file was deleted, False if file didn't exist

        Raises:
            StorageError: If deletion fails
        """
        s3_key = self._get_s3_key(project_id, file_path)

        # Check if file exists first
        if not self.exists(project_id, file_path):
            return False

        try:
            self.s3.delete_object(Bucket=self.bucket, Key=s3_key)
            return True

        except ClientError as e:
            raise StorageError(f"Failed to delete file from S3: {e}") from e

    def exists(self, project_id: UUID, file_path: str = "") -> bool:
        """Check if file or prefix exists in S3.

        Args:
            project_id: Project UUID
            file_path: Relative file path (empty = check project directory)

        Returns:
            True if exists, False otherwise
        """
        if file_path:
            # Check specific file
            s3_key = self._get_s3_key(project_id, file_path)
            try:
                self.s3.head_object(Bucket=self.bucket, Key=s3_key)
                return True
            except ClientError:
                return False
        else:
            # Check if project has any files
            prefix = self._get_s3_key(project_id) + "/"
            try:
                response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix, MaxKeys=1)
                return response.get("KeyCount", 0) > 0
            except ClientError:
                return False

    def list_files(self, project_id: UUID, prefix: str = "", recursive: bool = True) -> list[str]:
        """List files in project.

        Args:
            project_id: Project UUID
            prefix: File path prefix filter (e.g., "reports/")
            recursive: Include subdirectories (always True for S3)

        Returns:
            Sorted list of relative file paths (with forward slashes)

        Raises:
            StorageError: If listing fails
        """
        s3_prefix = self._get_s3_key(project_id)
        if prefix:
            s3_prefix = f"{s3_prefix}/{prefix}"
        else:
            s3_prefix = f"{s3_prefix}/"

        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=s3_prefix)

            base_prefix = self._get_s3_key(project_id) + "/"
            files = []

            for page in pages:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]
                    # Remove project prefix to get relative path
                    rel_path = key[len(base_prefix) :]

                    if not recursive and "/" in rel_path:
                        # Skip nested files if not recursive
                        continue

                    files.append(rel_path)

            return sorted(files)

        except ClientError as e:
            raise StorageError(f"Failed to list S3 objects: {e}") from e

    def get_project_size(self, project_id: UUID) -> int:
        """Get total size of all files in project.

        Args:
            project_id: Project UUID

        Returns:
            Size in bytes

        Raises:
            StorageError: If calculation fails
        """
        prefix = self._get_s3_key(project_id) + "/"

        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            total_size = 0
            for page in pages:
                if "Contents" in page:
                    total_size += sum(obj["Size"] for obj in page["Contents"])

            return total_size

        except ClientError as e:
            raise StorageError(f"Failed to calculate S3 project size: {e}") from e

    def get_file_path(self, project_id: UUID, file_path: str) -> str:
        """Get S3 URI for file.

        Args:
            project_id: Project UUID
            file_path: Relative file path

        Returns:
            S3 URI (e.g., "s3://bucket/projects/uuid/file.txt")
        """
        s3_key = self._get_s3_key(project_id, file_path)
        return f"s3://{self.bucket}/{s3_key}"

    def get_project_dir(self, project_id: UUID) -> str:
        """Get S3 prefix for project.

        Args:
            project_id: Project UUID

        Returns:
            S3 prefix (e.g., "projects/uuid")
        """
        return self._get_s3_key(project_id)
