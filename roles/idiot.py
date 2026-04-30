"""
roles/idiot.py — L'Idiot du Village.
S'il est désigné au bûcher, il est révélé mais reste en vie (sans pouvoir voter ensuite).
"""

from __future__ import annotations

from roles.base_role import BaseRole


class Idiot(BaseRole):
    name        = "Idiot du Village"
    team        = "village"
    description = "Si désigné au bûcher, vous êtes révélé mais survivez (et ne pouvez plus voter)."
    emoji       = "🤡"
    night_order = None
    extension   = "nouvelle_lune"

    def __init__(self):
        self.revealed: bool  = False  # A-t-il déjà survécu au bûcher ?
        self.can_vote: bool  = True

    def survive_vote(self) -> None:
        """Déclenché par vote_phase quand l'Idiot est désigné au bûcher."""
        self.revealed = True
        self.can_vote = False
