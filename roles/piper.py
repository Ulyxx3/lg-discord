"""
roles/piper.py — Le Joueur de Flûte.
Chaque nuit, il envoûte 2 joueurs. Quand tous les vivants sont envoûtés, il gagne.
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


class Piper(BaseRole):
    name        = "Joueur de Flûte"
    team        = "neutre"
    description = "Chaque nuit, envoûtez 2 joueurs. Si tous les vivants sont envoûtés, vous gagnez !"
    emoji       = "🪗"
    night_order = 7
    extension   = "nouvelle_lune"

    async def night_action(self, game: "Game", player: "Player") -> None:
        channel = player.private_text
        if not channel:
            return

        not_charmed = [
            p for p in game.alive_players
            if not p.is_charmed and p != player
        ]

        if not not_charmed:
            await channel.send("🪗 *Tous les joueurs sont déjà envoûtés… Vous avez gagné !*")
            player.action_event.set()
            return

        embed = discord.Embed(
            title="🪗 Le Joueur de Flûte joue…",
            description=(
                "Choisissez **2 joueurs** à envoûter cette nuit.\n"
                f"*(Joueurs non envoûtés : {len(not_charmed)})*\n\n"
                f"⏳ {game.game_config.night_role_timeout}s"
            ),
            color=C.COLOR_NIGHT,
        )

        view = PiperView(game, player, self, not_charmed)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            # Envoûte les 2 premiers de la liste par défaut
            for target in not_charmed[:2]:
                target.is_charmed = True
                game.night_state.piper_charmed.append(target)
            await channel.send("⏳ *Temps écoulé : 2 joueurs envoûtés automatiquement.*")
        finally:
            player.action_event.clear()


class PiperView(discord.ui.View):
    def __init__(self, game, player, piper, targets):
        super().__init__(timeout=None)
        self.game      = game
        self.player    = player
        self.piper     = piper
        self.targets   = targets
        self.selected: list["Player"] = []
        self._done     = False

        for target in targets:
            btn = discord.ui.Button(label=target.display_name, style=discord.ButtonStyle.secondary)
            btn.callback = self._make_callback(target)
            self.add_item(btn)

    def _make_callback(self, target):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.member.id:
                await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
                return
            if self._done:
                return
            if target in self.selected:
                await interaction.response.send_message("Déjà sélectionné.", ephemeral=True)
                return

            self.selected.append(target)
            if len(self.selected) >= min(2, len(self.targets)):
                self._done = True
                self.stop()
                for t in self.selected:
                    t.is_charmed = True
                    self.game.night_state.piper_charmed.append(t)
                self.player.action_event.set()
                names = " et ".join(f"**{t.display_name}**" for t in self.selected)
                await interaction.response.send_message(
                    f"🪗 Vous avez envoûté {names}.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ **{target.display_name}** sélectionné. Choisissez le second.", ephemeral=True
                )
        return callback
