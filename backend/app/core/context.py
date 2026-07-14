from contextvars import ContextVar
from typing import Optional

# ContextVar to hold request-scoped active model overrides
active_model_var: ContextVar[Optional[str]] = ContextVar("active_model_var", default=None)
