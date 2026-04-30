"""
roles/rust_maid.py — La Servante Rusée.
Quand un joueur meurt le soir, la Servante Rusée peut révéler son identité
et prendre son rôle (si elle est encore en vie).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

import discord

from roles.base_role import BaseRole
import config as C

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player

log = logging.getLogger(__name__)


class RustMaid(BaseRole):
    name        = "Servante Rusée"
    team        = "village"
    description = "Quand quelqu'un meurt au bûcher, vous pouvez révéler son rôle et le prendre."
    emoji       = "🧹"
    night_order = None
    extension   = "nouvelle_lune"

    def __init__(self):
        self.has_used: bool = False

    async def offer_role_swap(
        self, game: "Game", maid: "Player", victim: "Player"
    ) -> None:
        """
        Proposé par vote_phase après chaque mort au bûcher.
        La Servante Rusée peut prendre le rôle de la victime.
        """
        if self.has_used or not maid.is_alive:
            return

        channel = maid.private_text
        if not channel:
            return

        embed = discord.Embed(
            title="🧹 La Servante Rusée s'avance…",
            description=(
                f"**{victim.display_name}** vient de mourir.\n"
                f"Son rôle était : **{victim.role.name if victim.role else '???'}**\n\n"
                "Voulez-vous révéler votre identité et prendre son rôle ?\n"
                "*(Si vous acceptez, votre ancien rôle de Servante Rusée est révélé.)*"
            ),
            color=C.COLOR_INFO,
        )

        view = RustMaidView(game, maid, victim, self)
        await channel.send(embed=embed, view=view)
        # Attend 30 secondes max
        await asyncio.sleep(30)


class RustMaidView(discord.ui.View):
    def __init__(self, game, maid, victim, rust_maid_role):
        super().__init__(timeout=30)
        self.game           = game
        self.maid           = maid
        self.victim         = victim
        self.rust_maid_role = rust_maid_role

        accept = discord.ui.Button(label="✅ Prendre le rôle", style=discord.ButtonStyle.success)
        accept.callback = self._accept
        self.add_item(accept)

        decline = discord.ui.Button(label="❌ Refuser", style=discord.ButtonStyle.secondary)
        decline.callback = self._decline
        self.add_item(decline)

    async def _accept(self, interaction: discord.Interaction):
        if interaction.user.id != self.maid.member.id:
            await interaction.response.send_message("Ce n'est pas votre choix.", ephemeral=True)
            return
        self.rust_maid_role.has_used = True
        old_role_name = self.victim.role.name if self.victim.role else "???"
        self.maid.role = self.victim.role  # Échange de rôle
        self.stop()
        # Annonce publique
        if self.game.village_text:
            await self.game.village_text.send(
                embed=discord.Embed(
                    title="🧹 La Servante Rusée se dévoile !",
                    description=(
                        f"**{self.maid.display_name}** était la Servante Rusée.\n"
                        f"Elle prend le rôle de **{old_role_name}** et continue la partie !"
                    ),
                    color=C.COLOR_INFO,
                )
            )
        log.info("Servante Rusée prend le rôle de %s", old_role_name)
        await interaction.response.send_message(
            f"✅ Vous êtes maintenant **{old_role_name}**.", ephemeral=True
        )

    async def _decline(self, interaction: discord.Interaction):
        if interaction.user.id != self.maid.member.id:
            await interaction.response.send_message("Ce n'est pas votre choix.", ephemeral=True)
            return
        self.stop()
        await interaction.response.send_message("Vous gardez votre rôle.", ephemeral=True)
