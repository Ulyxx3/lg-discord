"""
roles/stuttering_judge.py — Le Juge Bègue.
Une fois par partie, il peut provoquer un second vote du bûcher dans la même journée.
Il communique ce souhait via un signe secret au MJ (le bot).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

from roles.base_role import BaseRole
import config as C

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player

log = logging.getLogger(__name__)


class StutteringJudge(BaseRole):
    name        = "Juge Bègue"
    team        = "village"
    description = "Une fois par partie : provoquez un second vote du bûcher le même jour."
    emoji       = "⚖️"
    night_order = None
    extension   = "nouvelle_lune"

    def __init__(self):
        self.has_used_power: bool = False
        self.wants_revote:   bool = False  # Lu par vote_phase après le 1er vote

    # La commande /lg revote déclenche wants_revote = True
    async def request_revote(self, game: "Game", player: "Player") -> str:
        if self.has_used_power:
            return "❌ Vous avez déjà utilisé votre pouvoir de rejugement."
        if game.phase.value != "day_vote":
            return "❌ Vous ne pouvez utiliser ce pouvoir que pendant le vote du bûcher."
        self.has_used_power = True
        self.wants_revote   = True
        log.info("Juge Bègue (%s) demande un second vote", player.display_name)
        return "⚖️ Votre demande de second vote a été transmise au Maître du Jeu…"
