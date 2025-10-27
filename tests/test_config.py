"""Tests for config module."""

import pytest
from pathlib import Path
import tempfile
import yaml

from ekahau_bom.config import Config, ConfigError


class TestConfigLoading:
    """Test configuration loading."""

    def test_load_nonexistent_config(self):
        """Test loading nonexistent config returns empty config."""
        config = Config.load(Path("nonexistent.yaml"))
        assert config.get('export.formats') is None

    def test_load_empty_config(self):
        """Test loading empty config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert config.get('export.formats') is None
        finally:
            config_path.unlink()

    def test_load_valid_config(self):
        """Test loading valid configuration."""
        config_data = {
            'export': {
                'formats': ['csv', 'excel'],
                'output_dir': 'reports'
            },
            'pricing': {
                'enabled': True,
                'default_discount': 10.0
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert config.get('export.formats') == ['csv', 'excel']
            assert config.get('export.output_dir') == 'reports'
            assert config.get('pricing.enabled') is True
            assert config.get('pricing.default_discount') == 10.0
        finally:
            config_path.unlink()

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:\n  - broken")
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigError):
                Config.load(config_path)
        finally:
            config_path.unlink()


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_export_formats(self):
        """Test validation of export formats."""
        # Invalid format
        config_data = {'export': {'formats': ['invalid_format']}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigError, match="Invalid export format"):
                Config.load(config_path)
        finally:
            config_path.unlink()

    def test_validate_discount(self):
        """Test validation of discount value."""
        # Discount > 100
        config_data = {'pricing': {'default_discount': 150.0}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigError, match="must be between 0 and 100"):
                Config.load(config_path)
        finally:
            config_path.unlink()

    def test_validate_logging_level(self):
        """Test validation of logging level."""
        # Invalid level
        config_data = {'logging': {'level': 'INVALID'}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigError, match="Invalid logging level"):
                Config.load(config_path)
        finally:
            config_path.unlink()

    def test_validate_grouping_dimension(self):
        """Test validation of grouping dimension."""
        # Invalid grouping
        config_data = {'grouping': {'group_by': 'invalid_dimension'}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigError, match="Invalid grouping dimension"):
                Config.load(config_path)
        finally:
            config_path.unlink()


class TestConfigGet:
    """Test configuration get method."""

    def test_get_simple_key(self):
        """Test getting simple key."""
        config = Config({'key': 'value'})
        assert config.get('key') == 'value'

    def test_get_nested_key(self):
        """Test getting nested key."""
        config = Config({
            'export': {
                'formats': ['csv'],
                'output_dir': 'output'
            }
        })
        assert config.get('export.formats') == ['csv']
        assert config.get('export.output_dir') == 'output'

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key returns default."""
        config = Config({})
        assert config.get('nonexistent') is None
        assert config.get('nonexistent', 'default') == 'default'

    def test_get_deeply_nested_key(self):
        """Test getting deeply nested key."""
        config = Config({
            'level1': {
                'level2': {
                    'level3': 'value'
                }
            }
        })
        assert config.get('level1.level2.level3') == 'value'


class TestConfigMergeWithArgs:
    """Test merging configuration with CLI arguments."""

    def test_cli_overrides_config(self):
        """Test that CLI arguments override config values."""
        config = Config({
            'export': {
                'output_dir': 'config_output',
                'formats': ['csv']
            }
        })

        class MockArgs:
            output_dir = Path('cli_output')
            format = 'excel'
            colors_config = None
            verbose = False
            log_file = None
            filter_floor = None
            filter_color = None
            filter_vendor = None
            filter_model = None
            filter_tag = None
            exclude_floor = None
            exclude_color = None
            exclude_vendor = None
            group_by = None
            tag_key = None
            enable_pricing = False
            pricing_file = None
            discount = 0.0
            no_volume_discounts = False
            batch = None
            recursive = False

        merged = config.merge_with_args(MockArgs())

        assert merged['output_dir'] == Path('cli_output')
        assert merged['export_formats'] == ['excel']

    def test_config_defaults_when_no_cli(self):
        """Test that config defaults are used when CLI args are not provided."""
        config = Config({
            'export': {
                'output_dir': 'config_output',
                'formats': ['excel', 'html']
            },
            'pricing': {
                'enabled': True,
                'default_discount': 15.0
            }
        })

        class MockArgs:
            output_dir = None
            format = None
            colors_config = None
            verbose = False
            log_file = None
            filter_floor = None
            filter_color = None
            filter_vendor = None
            filter_model = None
            filter_tag = None
            exclude_floor = None
            exclude_color = None
            exclude_vendor = None
            group_by = None
            tag_key = None
            enable_pricing = False
            pricing_file = None
            discount = 0.0
            no_volume_discounts = False
            batch = None
            recursive = False

        merged = config.merge_with_args(MockArgs())

        assert merged['export_formats'] == ['excel', 'html']
        assert merged['discount'] == 15.0

    def test_merge_filters(self):
        """Test merging filter arguments."""
        config = Config({
            'filters': {
                'include_floors': ['Floor 1', 'Floor 2'],
                'exclude_colors': ['Gray']
            }
        })

        class MockArgs:
            output_dir = None
            format = None
            colors_config = None
            verbose = False
            log_file = None
            filter_floor = 'Floor 3,Floor 4'  # CLI override
            filter_color = None
            filter_vendor = None
            filter_model = None
            filter_tag = None
            exclude_floor = None
            exclude_color = None  # Config value should be used
            exclude_vendor = None
            group_by = None
            tag_key = None
            enable_pricing = False
            pricing_file = None
            discount = 0.0
            no_volume_discounts = False
            batch = None
            recursive = False

        merged = config.merge_with_args(MockArgs())

        # CLI override takes precedence
        assert merged['filter_floors'] == ['Floor 3', 'Floor 4']
        # Config default used when CLI not provided
        assert merged['exclude_colors'] == ['Gray']


class TestConfigResolvePath:
    """Test path resolution."""

    def test_resolve_absolute_path(self):
        """Test that absolute paths are returned as-is."""
        config = Config()
        # Use a proper absolute path that works on both Unix and Windows
        import os
        if os.name == 'nt':  # Windows
            path = Path('C:/absolute/path/to/file.yaml')
        else:  # Unix
            path = Path('/absolute/path/to/file.yaml')
        resolved = config.resolve_path(path)
        assert resolved == path
        assert resolved.is_absolute()

    def test_resolve_relative_path(self):
        """Test that relative paths are resolved relative to config dir."""
        config = Config()
        config._config_dir = Path(__file__).parent  # Set to test directory

        # This will resolve relative to config directory
        path = config.resolve_path('test_file.yaml')
        assert path.is_absolute()


class TestConfigValidationExtended:
    """Extended tests for Config validation to improve coverage."""

    def test_load_config_with_none_path_uses_default(self):
        """Test that load with None uses DEFAULT_CONFIG_FILE."""
        # Since DEFAULT_CONFIG_FILE likely doesn't exist, should return default config
        config = Config.load(None)
        assert isinstance(config, Config)

    def test_validate_formats_not_list(self):
        """Test validation error when formats is not a list."""
        config_data = {
            'export': {
                'formats': 'csv'  # Should be a list, not a string
            }
        }
        with pytest.raises(ConfigError, match="export.formats must be a list"):
            config = Config(config_data)
            config._validate()

    def test_validate_discount_not_number(self):
        """Test validation error when discount is not a number."""
        config_data = {
            'pricing': {
                'default_discount': 'ten percent'  # Should be a number
            }
        }
        with pytest.raises(ConfigError, match="pricing.default_discount must be a number"):
            config = Config(config_data)
            config._validate()

    def test_validate_pdf_paper_size(self):
        """Test PDF paper size validation."""
        # Valid paper size
        config_data = {
            'pdf': {
                'paper_size': 'A4'
            }
        }
        config = Config(config_data)
        config._validate()  # Should not raise

        # Invalid paper size
        config_data_invalid = {
            'pdf': {
                'paper_size': 'B5'  # Not in valid sizes
            }
        }
        with pytest.raises(ConfigError, match="Invalid PDF paper size"):
            config_invalid = Config(config_data_invalid)
            config_invalid._validate()

    def test_validate_pdf_orientation(self):
        """Test PDF orientation validation."""
        # Valid orientation
        config_data = {
            'pdf': {
                'orientation': 'landscape'
            }
        }
        config = Config(config_data)
        config._validate()  # Should not raise

        # Invalid orientation
        config_data_invalid = {
            'pdf': {
                'orientation': 'vertical'  # Not in valid orientations
            }
        }
        with pytest.raises(ConfigError, match="Invalid PDF orientation"):
            config_invalid = Config(config_data_invalid)
            config_invalid._validate()

    def test_validate_pdf_all_settings(self):
        """Test PDF validation with all settings."""
        config_data = {
            'pdf': {
                'paper_size': 'Letter',
                'orientation': 'portrait'
            }
        }
        config = Config(config_data)
        config._validate()  # Should not raise any errors

        assert config.get('pdf.paper_size') == 'Letter'
        assert config.get('pdf.orientation') == 'portrait'

    def test_load_config_with_non_dict_yaml(self, tmp_path):
        """Test error when YAML file contains non-dict data."""
        config_file = tmp_path / "config.yaml"

        # Write YAML that's a list instead of dict
        config_file.write_text("- item1\n- item2\n", encoding='utf-8')

        with pytest.raises(ConfigError, match="Invalid configuration file format"):
            Config.load(config_file)
