"""agentomics: accounting for metered agents.

Every action an agent takes costs tokens, failures included. This package
keeps an append-only ledger of spend and income, computes burn rate and
runway, and renders a public ledger page. The numbers are the experiment.
"""

__version__ = "0.2.4"
