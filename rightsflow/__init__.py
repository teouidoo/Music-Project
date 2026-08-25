"""rightsflow - rights-holder economics for AI-generated music, built on the Eleven Music API."""

__version__ = "0.2.0"

from .waterfall import RightsHolder, Scenario, run_waterfall  # noqa: F401
from .decision import DecisionInputs, evaluate, breakeven_cannibalization  # noqa: F401
