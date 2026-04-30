"""
roles/dog_wolf.py — Le Chien-Loup.
La 1ère nuit, il choisit de rejoindre les villageois ou les loups.
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


class DogWolf(BaseRole):
    name             = "Chien-Loup"
    team             = "neutre"
    description      = "1ère nuit : choisissez de rejoindre les villageois ou les loups."
    emoji            = "🐕"
    night_order      = 8   # En même temps que les loups (peut les rejoindre)
    extension        = "nouvelle_lune"
    first_night_only = True

    async def night_action(self, game: "Game", player: "Player") -> None:
        channel = player.private_text
        if not channel:
            return

        embed = discord.Embed(
            title="🐕 Le Chien-Loup se réveille…",
            description=(
                "Vous êtes à la frontière entre deux mondes.\n"
                "Choisissez votre camp pour cette partie :"
            ),
            color=0x808080,
        )

        view = DogWolfView(game, player, self)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            # Par défaut : rejoint le village
            await self._join_village(game, player)
            await channel.send("⏳ *Temps écoulé. Vous rejoignez le village par défaut.*")
        finally:
            player.action_event.clear()

    async def _join_village(self, game: "Game", player: "Player") -> None:
        self.team = "village"
        player.action_event.set()
        log.info("Chien-Loup (%s) rejoint le village", player.display_name)

    async def _join_wolves(self, game: "Game", player: "Player") -> None:
        self.team = "loups"
        if game.role_wolf:
            try:
                await player.member.add_roles(game.role_wolf)
            except discord.HTTPException:
                pass
        player.action_event.set()
        log.info("Chien-Loup (%s) rejoint les loups", player.display_name)
        # Informe les loups
        if game.wolves_text:
            await game.wolves_text.send(
                f"🐕 **{player.display_name}** (Chien-Loup) vous rejoint cette nuit !"
            )


class DogWolfView(discord.ui.View):
    def __init__(self, game, player, dog_wolf):
        super().__init__(timeout=None)
        self.game     = game
        self.player   = player
        self.dog_wolf = dog_wolf
        self._used    = False

        village_btn = discord.ui.Button(label="👨‍🌾 Rejoindre le Village", style=discord.ButtonStyle.primary)
        village_btn.callback = self._village_callback
        self.add_item(village_btn)

        wolf_btn = discord.ui.Button(label="🐺 Rejoindre les Loups", style=discord.ButtonStyle.danger)
        wolf_btn.callback = self._wolf_callback
        self.add_item(wolf_btn)

    async def _village_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.member.id or self._used:
            await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
            return
        self._used = True
        self.stop()
        await self.dog_wolf._join_village(self.game, self.player)
        await interaction.response.send_message(
            "👨‍🌾 Vous rejoignez le **village** ! Défendez-le bien.", ephemeral=True
        )

    async def _wolf_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.member.id or self._used:
            await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
            return
        self._used = True
        self.stop()
        await self.dog_wolf._join_wolves(self.game, self.player)
        await interaction.response.send_message(
            "🐺 Vous rejoignez les **loups** ! Bonne chasse…", ephemeral=True
        )
