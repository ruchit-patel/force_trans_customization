__version__ = "0.0.1"

# Import patches to apply them
try:
    from .patches import communication_mixin_patch, communication_make_patch
except ImportError:
    pass
