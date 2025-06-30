from dataclasses import dataclass
from typing import Optional
from dataclasses import dataclass, field
from typing import (
    List, Callable, Optional, Dict, Any
)


@dataclass
class ReduceOperation:
    # ── required (no defaults) ──────────────────────────────────
    success: bool
    js_method_needed: bool
    total_char: int
    total_token: int
    raw_data: str

    # ── optional (have defaults) ────────────────────────────────
    reduced_data: Optional[str] = None
    reduced_total_char: Optional[int] = None
    reduced_total_token: Optional[int] = None
    token_reducement_percentage: Optional[float] = None
    error: Optional[str] = None
    reducement_details: Dict[str, Dict[str, int]] = field(default_factory=dict)



# @dataclass
# class ReduceOperation:
#     """
#     Holds the result of a single HTML‐reduction run.
#     """
#     success: bool                  # Did we complete the reduction (vs. abort for JS shell)?
#     total_char: int                # Original character count
#     total_token: int               # Original token count

#     reduced_total_char: Optional[int] = None
#     reduced_total_token: Optional[int] = None

    
#     token_reducement_percentage: Optional[float] = None





#     raw_data: str                  # The input HTML
#     reduced_data: Optional[str]    # The final HTML (None if aborted or on error)
#     js_method_needed: bool         # True if we detected an SPA shell and should switch to JS
#     error: Optional[str] = None    # An error message, if something went wrong
#     reducement_details: Dict[str, Dict[str, int]] = field(default_factory=dict)
