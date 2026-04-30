"""
roles/cupid.py — Cupidon.
La première nuit uniquement, désigne deux amoureux.
Si l'un meurt, l'autre meurt de chagrin.
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


class Cupid(BaseRole):
    name             = "Cupidon"
    team             = "village"
    description      = "La 1ère nuit : désignez deux amoureux. Si l'un meurt, l'autre le suit."
    emoji            = "❤️"
    night_order      = 2
    extension        = "base"
    first_night_only = True

    async def night_action(self, game: "Game", player: "Player") -> None:
        channel = player.private_text
        if not channel:
            return

        alive_others = [p for p in game.alive_players if p != player]
        if len(alive_others) < 2:
            await channel.send("*Pas assez de joueurs pour créer un lien amoureux.*")
            player.action_event.set()
            return

        embed = discord.Embed(
            title="❤️ Cupidon s'éveille…",
            description=(
                "Choisissez **deux joueurs** à lier par votre flèche d'amour.\n"
                "S'ils meurent l'un sans l'autre, ils mourront ensemble de chagrin.\n"
                "*(Cliquez deux fois sur deux joueurs différents.)*\n\n"
                f"⏳ Vous avez **{game.game_config.night_role_timeout}s** pour choisir."
            ),
            color=0xff69b4,
        )

        view = CupidView(game, player, alive_others)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            await channel.send("⏳ *Cupidon s'est rendormi sans viser personne…*")
        finally:
            player.action_event.clear()


class CupidView(discord.ui.View):
    """Sélection de deux amoureux avec des boutons."""

    def __init__(self, game: "Game", cupid_player: "Player", targets: list["Player"]):
        super().__init__(timeout=None)
        self.game         = game
        self.cupid_player = cupid_player
        self.selected: list["Player"] = []
        self._done = False

        for target in targets:
            btn = discord.ui.Button(
                label=target.display_name,
                style=discord.ButtonStyle.secondary,
            )
            btn.callback = self._make_callback(target)
            self.add_item(btn)

    def _make_callback(self, target: "Player"):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.cupid_player.member.id:
                await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
                return
            if self._done:
                await interaction.response.send_message("Vous avez déjà choisi.", ephemeral=True)
                return
            if target in self.selected:
                await interaction.response.send_message(
                    "Ce joueur est déjà sélectionné.", ephemeral=True
                )
                return

            self.selected.append(target)

            if len(self.selected) == 2:
                self._done = True
                self.stop()
                # Crée le lien amoureux
                a, b = self.selected
                a.lover_id = b.id
                b.lover_id = a.id
                # Avertit les amoureux en MP privé
                await a.private_text.send(
                    embed=discord.Embed(
                        title="❤️ Vous êtes amoureux·se !",
                        description=f"Cupidon vous a lié·e à **{b.display_name}**.\nSi l'un de vous meurt, l'autre mourra de chagrin…",
                        color=0xff69b4,
                    )
                ) if a.private_text else None
                await b.private_text.send(
                    embed=discord.Embed(
                        title="❤️ Vous êtes amoureux·se !",
                        description=f"Cupidon vous a lié·e à **{a.display_name}**.\nSi l'un de vous meurt, l'autre mourra de chagrin…",
                        color=0xff69b4,
                    )
                ) if b.private_text else None
                self.cupid_player.action_event.set()
                log.info("Cupidon a lié %s et %s", a.display_name, b.display_name)
                await interaction.response.send_message(
                    f"❤️ Vous avez lié **{a.display_name}** et **{b.display_name}**.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"✅ **{target.display_name}** sélectionné. Choisissez maintenant le second amoureux.",
                    ephemeral=True,
                )
        return callback
