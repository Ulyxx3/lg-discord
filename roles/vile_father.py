"""
roles/vile_father.py — Le Village Infect (Père des Loups).
Une fois par partie, après que les loups ont choisi leur victime,
il peut la contaminer (elle devient Loup-Garou au lieu de mourir).
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


class VileFather(BaseRole):
    name        = "Village Infect"
    team        = "loups"
    description = "Une fois par partie : contaminez la victime des loups (elle devient loup)."
    emoji       = "🦠"
    night_order = 8  # Agit après le vote des loups, même tour
    extension   = "nouvelle_lune"

    def __init__(self):
        self.has_used_infection: bool = False

    async def night_action(self, game: "Game", player: "Player") -> None:
        if self.has_used_infection:
            player.action_event.set()
            return

        channel = player.private_text
        if not channel or not game.night_state.wolf_victim:
            player.action_event.set()
            return

        victim = game.night_state.wolf_victim
        embed = discord.Embed(
            title="🦠 Le Village Infect s'éveille…",
            description=(
                f"Les loups ont choisi **{victim.display_name}**.\n\n"
                "Voulez-vous utiliser votre infection ? *(Usage unique)*\n"
                "→ La victime sera convertie en Loup-Garou au lieu de mourir.\n\n"
                f"⏳ {game.game_config.night_role_timeout}s"
            ),
            color=0x00FF00,
        )

        view = VileFatherView(game, player, self, victim)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            await channel.send("⏳ *Vous n'avez pas utilisé l'infection cette nuit.*")
        finally:
            player.action_event.clear()

    async def infect(self, game: "Game", player: "Player") -> None:
        """Convertit la victime en loup au lieu de la tuer."""
        victim = game.night_state.wolf_victim
        if not victim:
            return
        self.has_used_infection = True
        game.night_state.wolf_victim = None   # Ne meurt pas
        victim.role = type(self)()            # Devient Village Infect aussi (peut être Werewolf)
        from roles.werewolf import Werewolf
        victim.role = Werewolf()
        victim.role.team = "loups"
        # Donne le rôle Discord loup
        if game.role_wolf:
            try:
                await victim.member.add_roles(game.role_wolf)
            except discord.HTTPException:
                pass
        if victim.private_text:
            await victim.private_text.send(
                embed=discord.Embed(
                    title="🦠 Vous êtes infecté·e !",
                    description="Le Village Infect vous a contaminé·e. Vous rejoignez les loups !",
                    color=0x00FF00,
                )
            )
        log.info("Village Infect : %s est converti en loup", victim.display_name)
        player.action_event.set()


class VileFatherView(discord.ui.View):
    def __init__(self, game, player, vile_father, victim):
        super().__init__(timeout=None)
        self.game       = game
        self.player     = player
        self.vile_father = vile_father
        self._used      = False

        infect_btn = discord.ui.Button(label="🦠 Infecter", style=discord.ButtonStyle.danger)
        infect_btn.callback = self._infect
        self.add_item(infect_btn)

        skip_btn = discord.ui.Button(label="Laisser mourir", style=discord.ButtonStyle.secondary)
        skip_btn.callback = self._skip
        self.add_item(skip_btn)

    async def _infect(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.member.id or self._used:
            return
        self._used = True
        self.stop()
        await self.vile_father.infect(self.game, self.player)
        await interaction.response.send_message("🦠 La victime est infectée !", ephemeral=True)

    async def _skip(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.member.id:
            return
        self._used = True
        self.stop()
        self.player.action_event.set()
        await interaction.response.send_message("La victime mourra normalement.", ephemeral=True)
