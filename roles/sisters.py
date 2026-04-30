"""
roles/sisters.py — Les Deux Sœurs.
La 1ère nuit, elles se reconnaissent. Elles connaissent donc leur alliée dès le début.
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


class Sisters(BaseRole):
    name             = "Les Deux Sœurs"
    team             = "village"
    description      = "La 1ère nuit, vous vous réveillez et vous reconnaissez."
    emoji            = "👧👧"
    night_order      = 3
    extension        = "nouvelle_lune"
    first_night_only = True

    async def night_action(self, game: "Game", player: "Player") -> None:
        """Révèle aux sœurs l'identité de leur partenaire."""
        channel = player.private_text
        if not channel:
            return

        sisters = [
            p for p in game.alive_players
            if p.role and p.role.name == self.name and p != player
        ]

        if sisters:
            names = ", ".join(f"**{s.display_name}**" for s in sisters)
            embed = discord.Embed(
                title="👧 Les Sœurs se reconnaissent…",
                description=(
                    f"Votre sœur est : {names}\n"
                    "*Gardez ce secret pour vous deux.*"
                ),
                color=0xffb6c1,
            )
        else:
            embed = discord.Embed(
                title="👧 Les Sœurs…",
                description="*Vous êtes la seule sœur dans cette partie.*",
                color=0xffb6c1,
            )

        await channel.send(embed=embed)
        player.action_event.set()
