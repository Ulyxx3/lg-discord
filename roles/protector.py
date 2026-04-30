"""
roles/protector.py — Le Salvateur.
Chaque nuit, il protège un joueur des attaques des loups.
Il ne peut pas protéger la même personne deux nuits de suite.
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


class Protector(BaseRole):
    name        = "Salvateur"
    team        = "village"
    description = "Chaque nuit, protégez un joueur contre les loups (pas deux fois de suite le même)."
    emoji       = "🛡️"
    night_order = 10
    extension   = "nouvelle_lune"

    def __init__(self):
        self._last_protected_id: Optional[int] = None

    async def night_action(self, game: "Game", player: "Player") -> None:
        channel = player.private_text
        if not channel:
            return

        eligible = [
            p for p in game.alive_players
            if p.id != self._last_protected_id
        ]

        embed = discord.Embed(
            title=f"{self.emoji} Le Salvateur veille…",
            description=(
                "Choisissez un joueur à protéger cette nuit.\n"
                "*(Vous ne pouvez pas protéger la même personne deux nuits de suite.)*\n\n"
                f"⏳ {game.game_config.night_role_timeout}s"
            ),
            color=C.COLOR_INFO,
        )

        view = ProtectorView(game, player, self, eligible)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            await channel.send("⏳ *Le Salvateur s'est endormi sans protéger personne…*")
        finally:
            player.action_event.clear()

    async def protect(self, game: "Game", protector: "Player", target: "Player") -> None:
        self._last_protected_id = target.id
        game.night_state.protected = target
        target.protected_tonight = True
        protector.action_event.set()
        log.info("Salvateur protège %s", target.display_name)


class ProtectorView(discord.ui.View):
    def __init__(self, game, player, protector, targets):
        super().__init__(timeout=None)
        self.game      = game
        self.player    = player
        self.protector = protector
        self._used     = False

        for target in targets:
            btn = discord.ui.Button(
                label=f"🛡️ {target.display_name}",
                style=discord.ButtonStyle.primary,
            )
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
            await self.protector.protect(self.game, self.player, target)
            await interaction.response.send_message(
                f"🛡️ Vous protégez **{target.display_name}** cette nuit.", ephemeral=True
            )
        return callback
