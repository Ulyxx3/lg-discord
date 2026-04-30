"""
roles/brothers.py — Les Trois Frères.
La 1ère nuit (et toutes les 2 nuits suivantes selon variante), ils se reconnaissent.
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


class Brothers(BaseRole):
    name             = "Les Trois Frères"
    team             = "village"
    description      = "La 1ère nuit, vous vous réveillez et vous reconnaissez tous les trois."
    emoji            = "👦👦👦"
    night_order      = 4
    extension        = "nouvelle_lune"
    first_night_only = True

    async def night_action(self, game: "Game", player: "Player") -> None:
        channel = player.private_text
        if not channel:
            return

        brothers = [
            p for p in game.alive_players
            if p.role and p.role.name == self.name and p != player
        ]

        if brothers:
            names = ", ".join(f"**{b.display_name}**" for b in brothers)
            embed = discord.Embed(
                title="👦 Les Frères se reconnaissent…",
                description=f"Vos frères sont : {names}\n*Restez unis.*",
                color=0x8B4513,
            )
        else:
            embed = discord.Embed(
                title="👦 Les Frères…",
                description="*Vous êtes le seul frère dans cette partie.*",
                color=0x8B4513,
            )

        await channel.send(embed=embed)
        player.action_event.set()
