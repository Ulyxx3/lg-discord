"""
roles/scapegoat.py — Le Bouc Émissaire.
En cas d'égalité au vote du bûcher, c'est lui qui est éliminé.
À sa mort, il choisit les joueurs qui auront le droit de voter le lendemain.
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


class Scapegoat(BaseRole):
    name        = "Bouc Émissaire"
    team        = "village"
    description = "Si égalité au bûcher, vous êtes éliminé·e. Choisissez qui peut voter demain."
    emoji       = "🐐"
    night_order = None
    extension   = "nouvelle_lune"

    def __init__(self):
        self.vote_whitelist: list[int] = []   # IDs des joueurs autorisés à voter
        self._choice_event = asyncio.Event()

    async def on_death(self, game: "Game", player: "Player") -> None:
        """Permet au Bouc Émissaire de choisir qui peut voter le lendemain."""
        channel = player.private_text
        if not channel:
            return

        alive = game.alive_players
        embed = discord.Embed(
            title="🐐 Le Bouc Émissaire tombe…",
            description=(
                "Avant de mourir, vous choisissez **qui aura le droit de voter** demain.\n"
                "*(Sélectionnez tous les joueurs que vous souhaitez autoriser, puis validez.)*\n\n"
                f"⏳ {game.game_config.night_role_timeout}s"
            ),
            color=C.COLOR_DEATH,
        )
        view = ScapegoatView(game, player, self, alive)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                self._choice_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            # Par défaut : tout le monde peut voter
            self.vote_whitelist = [p.id for p in alive]
            await channel.send("⏳ *Temps écoulé : tout le monde pourra voter demain.*")
        finally:
            self._choice_event.clear()


class ScapegoatView(discord.ui.View):
    def __init__(self, game, player, scapegoat, targets):
        super().__init__(timeout=None)
        self.game      = game
        self.player    = player
        self.scapegoat = scapegoat
        self.selected: set[int] = set()

        for target in targets:
            btn = discord.ui.Button(
                label=target.display_name, style=discord.ButtonStyle.secondary
            )
            btn.callback = self._make_toggle(target)
            self.add_item(btn)

        confirm = discord.ui.Button(label="✅ Confirmer", style=discord.ButtonStyle.success, row=4)
        confirm.callback = self._confirm
        self.add_item(confirm)

    def _make_toggle(self, target):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.member.id:
                await interaction.response.send_message("Ce n'est pas votre choix.", ephemeral=True)
                return
            if target.id in self.selected:
                self.selected.discard(target.id)
                await interaction.response.send_message(
                    f"❌ **{target.display_name}** retiré.", ephemeral=True
                )
            else:
                self.selected.add(target.id)
                await interaction.response.send_message(
                    f"✅ **{target.display_name}** ajouté.", ephemeral=True
                )
        return callback

    async def _confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.member.id:
            await interaction.response.send_message("Ce n'est pas votre choix.", ephemeral=True)
            return
        if not self.selected:
            await interaction.response.send_message(
                "Sélectionnez au moins un joueur.", ephemeral=True
            )
            return
        self.scapegoat.vote_whitelist = list(self.selected)
        self.stop()
        self.scapegoat._choice_event.set()
        await interaction.response.send_message(
            f"✅ Confirmé. {len(self.selected)} joueur(s) pourront voter demain.", ephemeral=True
        )
