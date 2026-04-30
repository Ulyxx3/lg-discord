"""
roles/werewolf.py — Le Loup-Garou.
La nuit, il se retrouve avec ses congénères dans la tanière pour voter une victime.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

from roles.base_role import BaseRole

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player

log = logging.getLogger(__name__)


class Werewolf(BaseRole):
    name        = "Loup-Garou"
    team        = "loups"
    description = "La nuit, choisissez collectivement une victime à dévorer."
    emoji       = "🐺"
    night_order = 8
    extension   = "base"

    async def night_action(self, game: "Game", player: "Player") -> None:
        """
        Le tour des loups est géré collectivement par night_phase.py.
        Cette méthode n'est pas appelée individuellement pour les loups ;
        c'est wolf_collective_vote() dans night_phase.py qui gère le groupe.
        """
        pass
