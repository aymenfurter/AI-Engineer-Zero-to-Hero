"""
Azure Resource Masking Library

This module provides automatic masking of Azure resource names and sensitive data
in print output. Import and call `install()` to override the built-in print function.

Usage:
    from secure_print import install
    install()
    
    # Now all print() calls automatically mask Azure resources
    print("Endpoint: https://myresource.cognitiveservices.azure.com")
    # Output: Endpoint: https://myr***.cognitiveservices.azure.com
"""

import builtins
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Store original print
_original_print = builtins.print
_installed = False

# Cache for compiled patterns
_compiled_patterns: list = []
_patterns_loaded = False


def _load_patterns() -> list:
    """Load Azure URL patterns from YAML file."""
    global _compiled_patterns, _patterns_loaded
    
    if _patterns_loaded:
        return _compiled_patterns
    
    patterns = []
    
    # Try to load from YAML file
    yaml_path = Path(__file__).parent / "azure_patterns.yaml"
    
    if YAML_AVAILABLE and yaml_path.exists():
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Extract hostname patterns
            if 'azure_hostnames' in data:
                for item in data['azure_hostnames']:
                    pattern = item['pattern']
                    # Escape the pattern for regex and create capture groups
                    escaped = re.escape(pattern)
                    patterns.append({
                        'type': 'hostname',
                        'suffix': pattern,
                        'regex': re.compile(
                            r'(https?://)([a-zA-Z0-9][a-zA-Z0-9\-]{0,62})(' + escaped + r')',
                            re.IGNORECASE
                        )
                    })
            
            # Extract sensitive patterns
            if 'sensitive_patterns' in data:
                for item in data['sensitive_patterns']:
                    patterns.append({
                        'type': 'sensitive',
                        'pattern': item['pattern'],
                        'mask_type': item.get('mask_type', 'default'),
                        'regex': re.compile(
                            re.escape(item['pattern']) + r'([^\s;,"\']+)',
                            re.IGNORECASE
                        )
                    })
            
            # Extract resource name patterns
            if 'resource_name_patterns' in data:
                for item in data['resource_name_patterns']:
                    patterns.append({
                        'type': 'resource',
                        'regex': re.compile(item['pattern'], re.IGNORECASE),
                        'reveal_chars': item.get('reveal_chars', 8)
                    })
                    
        except Exception as e:
            _original_print(f"Warning: Could not load azure_patterns.yaml: {e}", file=sys.stderr)
    
    # Add fallback patterns if YAML not available or failed
    if not patterns:
        patterns = _get_fallback_patterns()
    
    _compiled_patterns = patterns
    _patterns_loaded = True
    return patterns


def _get_fallback_patterns() -> list:
    """Fallback patterns if YAML is not available."""
    hostnames = [
        ".cognitiveservices.azure.com",
        ".openai.azure.com",
        ".services.ai.azure.com",
        ".blob.core.windows.net",
        ".file.core.windows.net",
        ".queue.core.windows.net",
        ".table.core.windows.net",
        ".dfs.core.windows.net",
        ".database.windows.net",
        ".documents.azure.com",
        ".mongo.cosmos.azure.com",
        ".vault.azure.net",
        ".azurewebsites.net",
        ".azure-api.net",
        ".azurecr.io",
        ".servicebus.windows.net",
        ".redis.cache.windows.net",
        ".search.windows.net",
        ".azurestaticapps.net",
        ".azurefd.net",
        ".postgres.database.azure.com",
        ".mysql.database.azure.com",
        ".azmk8s.io",
        ".azconfig.io",
        ".signalr.net",
        ".webpubsub.azure.com",
        ".communication.azure.com",
        ".ml.azure.com",
        ".inference.ml.azure.com",
        ".aifoundry.azure.com",
        ".models.ai.azure.com",
    ]
    
    patterns = []
    for hostname in hostnames:
        escaped = re.escape(hostname)
        patterns.append({
            'type': 'hostname',
            'suffix': hostname,
            'regex': re.compile(
                r'(https?://)([a-zA-Z0-9][a-zA-Z0-9\-]{0,62})(' + escaped + r')',
                re.IGNORECASE
            )
        })
    
    return patterns


def mask_azure_resources(text: str, reveal_chars: int = 3) -> str:
    """
    Mask Azure resource names in text while keeping the domain visible.
    
    Args:
        text: The text to mask
        reveal_chars: Number of characters to reveal (default: 3)
    
    Returns:
        Text with Azure resource names masked
    
    Example:
        >>> mask_azure_resources("https://myresource.cognitiveservices.azure.com")
        'https://myr***.cognitiveservices.azure.com'
    """
    if not isinstance(text, str):
        return text
    
    patterns = _load_patterns()
    result = text
    
    for pattern_info in patterns:
        if pattern_info['type'] == 'hostname':
            regex = pattern_info['regex']
            
            def mask_hostname(match):
                protocol = match.group(1)  # https:// or http://
                resource_name = match.group(2)  # the resource name
                suffix = match.group(3)  # .cognitiveservices.azure.com etc.
                
                # Keep first N chars, mask the rest
                if len(resource_name) > reveal_chars:
                    masked_name = resource_name[:reveal_chars] + "***"
                else:
                    masked_name = resource_name
                
                return f"{protocol}{masked_name}{suffix}"
            
            result = regex.sub(mask_hostname, result)
        
        elif pattern_info['type'] == 'sensitive':
            regex = pattern_info['regex']
            prefix = pattern_info['pattern']
            
            def mask_sensitive(match):
                value = match.group(1)
                if len(value) > 8:
                    masked_value = value[:4] + "***" + value[-4:]
                else:
                    masked_value = "***"
                return f"{prefix}{masked_value}"
            
            result = regex.sub(mask_sensitive, result)
        
        elif pattern_info['type'] == 'resource':
            regex = pattern_info['regex']
            chars = pattern_info.get('reveal_chars', 8)
            
            def mask_resource(match):
                full = match.group(0)
                # Find the value part and mask it
                parts = full.rsplit('/', 1)
                if len(parts) == 2:
                    prefix, value = parts
                    if len(value) > chars:
                        return f"{prefix}/{value[:chars]}***"
                return full
            
            result = regex.sub(mask_resource, result)
    
    # Also mask common API key patterns
    result = _mask_api_keys(result)
    
    return result


def _mask_api_keys(text: str) -> str:
    """Mask common API key patterns."""
    # Mask APIM keys and similar (32+ char hex/alphanumeric strings)
    key_pattern = re.compile(r'(["\']?)([a-fA-F0-9]{32,})(["\']?)')
    
    def mask_key(match):
        quote1 = match.group(1)
        key = match.group(2)
        quote2 = match.group(3)
        return f"{quote1}{key[:4]}***{key[-4:]}{quote2}"
    
    text = key_pattern.sub(mask_key, text)
    
    # Mask subscription IDs (GUID format)
    guid_pattern = re.compile(
        r'(/subscriptions/)([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
        re.IGNORECASE
    )
    
    def mask_guid(match):
        prefix = match.group(1)
        guid = match.group(2)
        return f"{prefix}{guid[:8]}***"
    
    text = guid_pattern.sub(mask_guid, text)
    
    return text


def masked_print(*args, reveal_chars: int = 3, **kwargs):
    """
    A print function that automatically masks Azure resource names.
    
    Args:
        *args: Arguments to print (will be masked)
        reveal_chars: Number of characters to reveal in resource names
        **kwargs: Standard print kwargs (sep, end, file, flush)
    """
    # Extract our custom kwarg
    rc = reveal_chars
    
    # Convert all args to strings and mask them
    masked_args = []
    for arg in args:
        str_arg = str(arg) if not isinstance(arg, str) else arg
        masked_args.append(mask_azure_resources(str_arg, reveal_chars=rc))
    
    # Call original print with masked content
    _original_print(*masked_args, **kwargs)


def install(reveal_chars: int = 3):
    """
    Install the masked print function as the global print().
    
    Args:
        reveal_chars: Number of characters to reveal in resource names (default: 3)
    
    Usage:
        from secure_print import install
        install()
        
        # Now print automatically masks Azure resources
        print("https://myresource.cognitiveservices.azure.com")
        # Output: https://myr***.cognitiveservices.azure.com
    """
    global _installed
    
    # Preload patterns
    _load_patterns()
    
    # Create a wrapper that uses the configured reveal_chars
    def configured_print(*args, **kwargs):
        masked_print(*args, reveal_chars=reveal_chars, **kwargs)
    
    builtins.print = configured_print
    _installed = True
    _original_print("secure_print: Azure resource masking enabled")


def uninstall():
    """Restore the original print function."""
    global _installed
    builtins.print = _original_print
    _installed = False
    _original_print("secure_print: Original print restored")


def is_installed() -> bool:
    """Check if secure print is currently installed."""
    return _installed


def original_print(*args, **kwargs):
    """Access the original print function without masking."""
    _original_print(*args, **kwargs)


# Convenience function for one-off masking without installing
def mask(text: str, reveal_chars: int = 3) -> str:
    """
    Mask Azure resources in text without installing the print override.
    
    Args:
        text: Text to mask
        reveal_chars: Number of characters to reveal
    
    Returns:
        Masked text
    """
    return mask_azure_resources(text, reveal_chars=reveal_chars)


# For IPython/Jupyter display integration
class MaskedStr(str):
    """A string subclass that masks Azure resources when displayed."""
    
    def __new__(cls, content, reveal_chars=3):
        masked = mask_azure_resources(str(content), reveal_chars=reveal_chars)
        instance = super().__new__(cls, masked)
        instance._original = content
        instance._reveal_chars = reveal_chars
        return instance
    
    def __repr__(self):
        return mask_azure_resources(repr(self._original), self._reveal_chars)
