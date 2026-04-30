"""
roles/fox.py — Le Renard.
Chaque nuit, il désigne un groupe de 3 joueurs adjacents. Si au moins un est un loup,
il conserve son pouvoir. Sinon, il le perd définitivement.
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


class Fox(BaseRole):
    name        = "Renard"
    team        = "village"
    description = "Chaque nuit : sniffez un groupe de 3 joueurs. Si aucun loup → perdez votre pouvoir."
    emoji       = "🦊"
    night_order = 6
    extension   = "nouvelle_lune"

    def __init__(self):
        self._has_power = True

    async def night_action(self, game: "Game", player: "Player") -> None:
        if not self._has_power:
            player.action_event.set()
            return

        channel = player.private_text
        if not channel:
            return

        alive = game.alive_players
        embed = discord.Embed(
            title="🦊 Le Renard renifle…",
            description=(
                "Choisissez un joueur. Vous saurez si lui ou ses voisins immédiats "
                "cachent un Loup-Garou.\n"
                f"⏳ {game.game_config.night_role_timeout}s"
            ),
            color=0xFF6600,
        )
        view = FoxView(game, player, self, alive)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            await channel.send("⏳ *Le Renard ne renifle rien cette nuit…*")
        finally:
            player.action_event.clear()

    async def sniff(self, game: "Game", fox_player: "Player", target: "Player") -> None:
        """Renifle la cible et ses voisins dans la liste des vivants."""
        alive = game.alive_players
        idx   = alive.index(target) if target in alive else 0
        group = [
            alive[(idx - 1) % len(alive)],
            alive[idx],
            alive[(idx + 1) % len(alive)],
        ]
        # Retire les doublons si < 3 joueurs vivants
        group = list(dict.fromkeys(group))

        has_wolf = any(
            p.role and p.role.team == "loups" for p in group
        )
        channel = fox_player.private_text
        if channel:
            if has_wolf:
                await channel.send(
                    f"🐺 *Vous sentez une odeur de loup parmi "
                    f"{', '.join(p.display_name for p in group)}… Méfiance !*"
                )
            else:
                await channel.send(
                    f"✅ *Aucune odeur de loup parmi "
                    f"{', '.join(p.display_name for p in group)}. "
                    f"Mais vous perdez votre flair…*"
                )
                self._has_power = False
                self.night_order = None

        fox_player.action_event.set()


class FoxView(discord.ui.View):
    def __init__(self, game, player, fox, targets):
        super().__init__(timeout=None)
        self.game   = game
        self.player = player
        self.fox    = fox
        self._used  = False

        for target in targets:
            btn = discord.ui.Button(label=target.display_name, style=discord.ButtonStyle.secondary)
            btn.callback = self._make_callback(target)
            self.add_item(btn)

    def _make_callback(self, target):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.member.id:
                await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
                return
            if self._used:
                return
            self._used = True
            self.stop()
            await interaction.response.defer()
            await self.fox.sniff(self.game, self.player, target)
        return callback
