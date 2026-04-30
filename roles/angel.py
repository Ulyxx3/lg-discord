"""
roles/angel.py — L'Ange.
Équipe solitaire : son objectif est d'être éliminé·e lors du premier vote du village.
S'il réussit : il gagne seul. Sinon, il devient Villageois.
"""

from __future__ import annotations

from roles.base_role import BaseRole


class Angel(BaseRole):
    name        = "Ange"
    team        = "neutre"
    description = "Objectif solitaire : être éliminé·e lors du 1er vote du village. Sinon, vous devenez Villageois."
    emoji       = "😇"
    night_order = None
    extension   = "nouvelle_lune"

    def __init__(self):
        self.first_vote_passed: bool = False

    def fail_angel_objective(self) -> None:
        """
        Appelé par vote_phase après le 1er vote si l'Ange n'a pas été éliminé.
        Il devient Villageois.
        """
        from roles.villager import Villager
        self.__class__ = Villager
        self.name  = "Villageois"
        self.team  = "village"
        self.emoji = "👨‍🌾"
        self.first_vote_passed = True
