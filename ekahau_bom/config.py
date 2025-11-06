"""Configuration management for EkahauBOM.

This module handles loading, validation, and merging of configuration from YAML files
with command-line arguments.
"""

from __future__ import annotations


import logging
from pathlib import Path
from typing import Any, Optional
import yaml

logger = logging.getLogger(__name__)

# Default configuration file location
DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / "config"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"


class ConfigError(Exception):
    """Exception raised for configuration errors."""

    pass


class Config:
    """Configuration manager for EkahauBOM.

    Handles loading configuration from YAML files and merging with CLI arguments.
    CLI arguments always take precedence over configuration file values.
    """

    def __init__(self, config_data: dict[str, Any] | None = None):
        """Initialize configuration.

        Args:
            config_data: Configuration dictionary. If None, empty config is created.
        """
        self._data = config_data or {}
        self._config_dir = DEFAULT_CONFIG_DIR

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Config":
        """Load configuration from YAML file.

        Args:
            config_path: Path to configuration file. If None, uses default location.

        Returns:
            Config instance with loaded configuration

        Raises:
            ConfigError: If configuration file is invalid or cannot be loaded
        """
        if config_path is None:
            config_path = DEFAULT_CONFIG_FILE

        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            logger.info("Using default configuration")
            return cls()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                logger.warning(f"Configuration file is empty: {config_path}")
                return cls()

            if not isinstance(config_data, dict):
                raise ConfigError(f"Invalid configuration file format: {config_path}")

            logger.info(f"Loaded configuration from: {config_path}")
            config = cls(config_data)
            config._config_dir = config_path.parent

            # Validate configuration
            config._validate()

            return config

        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse configuration file: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")

    def _validate(self):
        """Validate configuration structure and values.

        Raises:
            ConfigError: If configuration is invalid
        """
        # Validate export formats
        if "export" in self._data and "formats" in self._data["export"]:
            formats = self._data["export"]["formats"]
            if not isinstance(formats, list):
                raise ConfigError("export.formats must be a list")

            valid_formats = {"csv", "excel", "html", "json", "pdf"}
            for fmt in formats:
                if fmt not in valid_formats:
                    raise ConfigError(
                        f"Invalid export format: {fmt}. Must be one of: {valid_formats}"
                    )

        # Validate pricing discount
        if "pricing" in self._data and "default_discount" in self._data["pricing"]:
            discount = self._data["pricing"]["default_discount"]
            if not isinstance(discount, (int, float)):
                raise ConfigError("pricing.default_discount must be a number")
            if not 0 <= discount <= 100:
                raise ConfigError("pricing.default_discount must be between 0 and 100")

        # Validate logging level
        if "logging" in self._data and "level" in self._data["logging"]:
            level = self._data["logging"]["level"]
            valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            if level not in valid_levels:
                raise ConfigError(f"Invalid logging level: {level}. Must be one of: {valid_levels}")

        # Validate grouping dimension
        if "grouping" in self._data and "group_by" in self._data["grouping"]:
            group_by = self._data["grouping"]["group_by"]
            if group_by is not None:
                valid_dimensions = {"floor", "color", "vendor", "model", "tag"}
                if group_by not in valid_dimensions:
                    raise ConfigError(
                        f"Invalid grouping dimension: {group_by}. Must be one of: {valid_dimensions}"
                    )

        # Validate PDF settings
        if "pdf" in self._data:
            if "paper_size" in self._data["pdf"]:
                paper_size = self._data["pdf"]["paper_size"]
                valid_sizes = {"A4", "Letter", "Legal"}
                if paper_size not in valid_sizes:
                    raise ConfigError(
                        f"Invalid PDF paper size: {paper_size}. Must be one of: {valid_sizes}"
                    )

            if "orientation" in self._data["pdf"]:
                orientation = self._data["pdf"]["orientation"]
                valid_orientations = {"portrait", "landscape"}
                if orientation not in valid_orientations:
                    raise ConfigError(
                        f"Invalid PDF orientation: {orientation}. Must be one of: {valid_orientations}"
                    )

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key path.

        Args:
            key: Dot-separated key path (e.g., "export.formats")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get("export.formats")
            ['csv', 'excel']
            >>> config.get("export.timestamp", False)
            False
        """
        keys = key.split(".")
        value = self._data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve path relative to configuration directory.

        Args:
            path: Path to resolve (can be absolute or relative)

        Returns:
            Resolved absolute path
        """
        path = Path(path)

        if path.is_absolute():
            return path

        # Try relative to config directory first
        config_relative = self._config_dir / path
        if config_relative.exists():
            return config_relative

        # Try relative to current directory
        return Path.cwd() / path

    def merge_with_args(self, args: Any) -> dict[str, Any]:
        """Merge configuration with command-line arguments.

        CLI arguments take precedence over configuration file values.

        Args:
            args: Parsed command-line arguments (from argparse)

        Returns:
            Dictionary with merged configuration
        """
        merged = {}

        # Output directory
        if hasattr(args, "output_dir") and args.output_dir:
            merged["output_dir"] = args.output_dir
        else:
            merged["output_dir"] = Path(self.get("export.output_dir", "output"))

        # Export formats
        if hasattr(args, "format") and args.format:
            merged["export_formats"] = [f.strip() for f in args.format.split(",")]
        else:
            merged["export_formats"] = self.get("export.formats", ["csv"])

        # Colors config
        if hasattr(args, "colors_config") and args.colors_config:
            merged["colors_config"] = args.colors_config
        else:
            colors_db = self.get("colors.database")
            if colors_db:
                merged["colors_config"] = self.resolve_path(colors_db)
            else:
                merged["colors_config"] = None

        # Pricing
        merged["enable_pricing"] = getattr(args, "enable_pricing", False) or self.get(
            "pricing.enabled", False
        )

        if hasattr(args, "pricing_file") and args.pricing_file:
            merged["pricing_file"] = args.pricing_file
        else:
            pricing_db = self.get("pricing.database")
            if pricing_db:
                merged["pricing_file"] = self.resolve_path(pricing_db)
            else:
                merged["pricing_file"] = None

        if hasattr(args, "discount") and args.discount > 0:
            merged["discount"] = args.discount
        else:
            merged["discount"] = self.get("pricing.default_discount", 0.0)

        merged["no_volume_discounts"] = getattr(args, "no_volume_discounts", False) or not self.get(
            "pricing.volume_discounts", True
        )

        # Filters
        merged["filter_floors"] = self._merge_list_arg(
            args, "filter_floor", self.get("filters.include_floors", [])
        )
        merged["filter_colors"] = self._merge_list_arg(
            args, "filter_color", self.get("filters.include_colors", [])
        )
        merged["filter_vendors"] = self._merge_list_arg(
            args, "filter_vendor", self.get("filters.include_vendors", [])
        )
        merged["filter_models"] = self._merge_list_arg(
            args, "filter_model", self.get("filters.include_models", [])
        )
        merged["filter_tags"] = getattr(args, "filter_tag", None) or self.get("filters.tags", None)

        merged["exclude_floors"] = self._merge_list_arg(
            args, "exclude_floor", self.get("filters.exclude_floors", [])
        )
        merged["exclude_colors"] = self._merge_list_arg(
            args, "exclude_color", self.get("filters.exclude_colors", [])
        )
        merged["exclude_vendors"] = self._merge_list_arg(
            args, "exclude_vendor", self.get("filters.exclude_vendors", [])
        )

        # Grouping
        if hasattr(args, "group_by") and args.group_by:
            merged["group_by"] = args.group_by
        else:
            merged["group_by"] = self.get("grouping.group_by")

        if hasattr(args, "tag_key") and args.tag_key:
            merged["tag_key"] = args.tag_key
        else:
            merged["tag_key"] = self.get("grouping.tag_key")

        # Logging
        if hasattr(args, "verbose") and args.verbose:
            merged["log_level"] = "DEBUG"
        else:
            merged["log_level"] = self.get("logging.level", "INFO")

        if hasattr(args, "log_file") and args.log_file:
            merged["log_file"] = args.log_file
        else:
            log_file = self.get("logging.file")
            merged["log_file"] = self.resolve_path(log_file) if log_file else None

        # Batch processing
        merged["batch"] = getattr(args, "batch", None)

        if hasattr(args, "recursive") and args.recursive:
            merged["recursive"] = args.recursive
        else:
            merged["recursive"] = self.get("batch.recursive", False)

        # Visualization
        merged["visualize_floor_plans"] = getattr(args, "visualize_floor_plans", False)
        merged["ap_circle_radius"] = getattr(args, "ap_circle_radius", 15)
        merged["no_ap_names"] = getattr(args, "no_ap_names", False)
        merged["show_azimuth_arrows"] = getattr(args, "show_azimuth_arrows", False)
        merged["ap_opacity"] = getattr(args, "ap_opacity", 1.0)

        # Notes visualization
        merged["include_text_notes"] = getattr(args, "include_text_notes", False)
        merged["include_picture_notes"] = getattr(args, "include_picture_notes", False)
        merged["include_cable_notes"] = getattr(args, "include_cable_notes", False)

        # Project naming
        merged["project_name"] = getattr(args, "project_name", None)

        # Output options
        merged["quiet"] = getattr(args, "quiet", False)

        return merged

    def _merge_list_arg(self, args: Any, arg_name: str, config_default: list) -> list[str] | None:
        """Merge list argument from CLI with config default.

        Args:
            args: Parsed command-line arguments
            arg_name: Name of the argument
            config_default: Default value from config

        Returns:
            List of values or None
        """
        if hasattr(args, arg_name):
            arg_value = getattr(args, arg_name)
            if arg_value:
                # Parse comma-separated string
                return [x.strip() for x in arg_value.split(",")]

        # Use config default if available and not empty
        if config_default:
            return config_default

        return None

    def to_dict(self) -> dict[str, Any]:
        """Get configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self._data.copy()


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from file.

    Convenience function for loading configuration.

    Args:
        config_path: Path to configuration file. If None, uses default location.

    Returns:
        Config instance

    Raises:
        ConfigError: If configuration is invalid
    """
    return Config.load(config_path)
