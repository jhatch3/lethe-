"""Lethe agents package.

Importing this module loads every agent file, which causes each to register
itself with the registry. To add an agent: drop a file alongside these and
add a one-line import here. To remove: delete the file and the import line.

The pipeline runner only ever talks to `registry`, never to concrete agents.
"""

# Audit agents
from agents import audit_openai     # noqa: F401  (registers "alpha")
from agents import audit_anthropic  # noqa: F401  (registers "beta")
from agents import audit_google     # noqa: F401  (registers "gamma")

# Drafter agent
from agents import drafter_anthropic  # noqa: F401  (registers drafter)
