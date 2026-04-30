"""
roles/seer.py — La Voyante.
La nuit, elle peut regarder l'identité secrète d'un joueur.
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


class Seer(BaseRole):
    name        = "Voyante"
    team        = "village"
    description = "Chaque nuit, regardez secrètement le rôle d'un joueur."
    emoji       = "👁️"
    night_order = 5
    extension   = "base"

    async def night_action(self, game: "Game", player: "Player") -> None:
        """Envoie le message d'action dans le salon privé de la Voyante."""
        channel = player.private_text
        if not channel:
            return

        alive_others = [p for p in game.alive_players if p != player]
        if not alive_others:
            await channel.send("*Il n'y a plus personne à observer…*")
            return

        # Construit la liste des joueurs comme boutons
        view = SeerView(game, player, alive_others)
        embed = discord.Embed(
            title=f"{self.emoji} La Voyante se réveille…",
            description=(
                "Vous ouvrez les yeux et scrutez les âmes du village.\n"
                "Choisissez un joueur dont vous souhaitez révéler le rôle.\n\n"
                f"⏳ Vous avez **{game.game_config.night_role_timeout}s** pour agir."
            ),
            color=C.COLOR_SEER,
        )
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(player.action_event.wait(), timeout=game.game_config.night_role_timeout)
        except asyncio.TimeoutError:
            await channel.send("⏳ *Vos visions se dissipent… Vous n'avez pas observé de joueur cette nuit.*")
        finally:
            player.action_event.clear()

    async def reveal(self, game: "Game", seer: "Player", target: "Player") -> None:
        """Révèle le rôle d'un joueur à la Voyante."""
        channel = seer.private_text
        if not channel:
            return

        role = target.role
        color = C.COLOR_WOLVES if (role and role.team == "loups") else C.COLOR_DAY

        embed = discord.Embed(
            title="🔮 Vision révélée",
            color=color,
        )
        if role and role.team == "loups":
            embed.description = (
                f"Vous observez **{target.display_name}**…\n\n"
                f"🐺 **C'est un Loup-Garou !** ({role.name})\n"
                f"*Méfiez-vous de lui au village.*"
            )
        else:
            embed.description = (
                f"Vous observez **{target.display_name}**…\n\n"
                f"☀️ **Il appartient au village.** ({role.name if role else 'Inconnu'})\n"
                f"*Vous pouvez lui faire confiance.*"
            )

        game.night_state.seer_revealed = target
        await channel.send(embed=embed)
        seer.action_event.set()


class SeerView(discord.ui.View):
    """Interface boutons pour la Voyante : sélectionne une cible parmi les vivants."""

    def __init__(self, game: "Game", seer: "Player", targets: list["Player"]):
        super().__init__(timeout=None)
        self.game   = game
        self.seer   = seer
        self._used  = False

        for target in targets:
            btn = discord.ui.Button(
                label=target.display_name,
                style=discord.ButtonStyle.secondary,
                custom_id=f"seer_{target.id}",
            )
            btn.callback = self._make_callback(target)
            self.add_item(btn)

    def _make_callback(self, target: "Player"):
        async def callback(interaction: discord.Interaction):
            if self._used:
                await interaction.response.send_message(
                    "Vous avez déjà utilisé votre vision cette nuit.", ephemeral=True
                )
                return
            if interaction.user.id != self.seer.member.id:
                await interaction.response.send_message(
                    "Ce n'est pas votre tour.", ephemeral=True
                )
                return
            self._used = True
            self.stop()
            await interaction.response.defer()
            await self.seer.role.reveal(self.game, self.seer, target)  # type: ignore[attr-defined]
        return callback
