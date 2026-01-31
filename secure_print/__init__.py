"""
secure_print - Automatic Azure Resource Masking for Print Output

This library provides automatic masking of Azure resource names, endpoints,
and sensitive data in print output to prevent accidental exposure.

Quick Start:
    from secure_print import install
    install()
    
    # All print() calls now automatically mask Azure resources
    print("Endpoint: https://myresource.cognitiveservices.azure.com")
    # Output: Endpoint: https://myr***.cognitiveservices.azure.com

Functions:
    install(reveal_chars=3)     - Override print() with masked version
    uninstall()                 - Restore original print()
    mask(text, reveal_chars=3)  - Mask text without installing
    original_print(*args)       - Access original print when installed

Jupyter/IPython:
    from secure_print import MaskedStr
    MaskedStr("https://myresource.cognitiveservices.azure.com")
"""

from .masking import (
    install,
    uninstall,
    is_installed,
    mask,
    mask_azure_resources,
    masked_print,
    original_print,
    MaskedStr,
)

__version__ = "1.0.0"
__all__ = [
    "install",
    "uninstall", 
    "is_installed",
    "mask",
    "mask_azure_resources",
    "masked_print",
    "original_print",
    "MaskedStr",
]
