from backend.app.adapters.base import BaseApaarAdapter, VerificationResult
from backend.app.adapters.mock_apaar import MockApaarAdapter

_default_adapter: BaseApaarAdapter = MockApaarAdapter()

def get_apaar_adapter() -> BaseApaarAdapter:
    """Return the active APAAR verification provider adapter."""
    return _default_adapter

__all__ = ["BaseApaarAdapter", "VerificationResult", "MockApaarAdapter", "get_apaar_adapter"]
