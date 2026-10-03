"""factory-boy factories, one module per app. Import from here in tests."""

from .accounts import UserFactory

__all__ = ["UserFactory"]
