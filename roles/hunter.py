"""
roles/hunter.py — Le Chasseur.
Quand il meurt (à n'importe quel moment), il peut tirer sur un joueur de son choix.
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


class Hunter(BaseRole):
    name        = "Chasseur"
    team        = "village"
    description = "À votre mort, vous tirez une dernière flèche sur un joueur de votre choix."
    emoji       = "🏹"
    night_order = None  # Pas de tour nocturne (réactif à la mort)
    extension   = "base"

    def __init__(self):
        self._shot_event = asyncio.Event()

    async def on_death(self, game: "Game", player: "Player") -> None:
        """Déclenché quand le Chasseur meurt. Il doit choisir une cible."""
        channel = player.private_text
        if not channel:
            return

        alive_targets = [p for p in game.alive_players if p != player]
        if not alive_targets:
            return

        embed = discord.Embed(
            title="🏹 Le Chasseur tombe…",
            description=(
                "En tombant, vous saisissez votre arbalète.\n"
                "**Choisissez un joueur à emporter avec vous !**\n\n"
                f"⏳ Vous avez **{game.game_config.night_role_timeout}s** pour viser."
            ),
            color=C.COLOR_NIGHT,
        )

        view = HunterView(game, player, self, alive_targets)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(self._shot_event.wait(), timeout=game.game_config.night_role_timeout)
        except asyncio.TimeoutError:
            await channel.send("💨 *Votre flèche part dans le vide… personne n'est touché.*")
        finally:
            self._shot_event.clear()

        # Annonce dans le village
        if game.night_state.hunter_shot:
            target = game.night_state.hunter_shot
            if game.village_text:
                await game.village_text.send(
                    embed=discord.Embed(
                        title="🏹 Le Chasseur tire !",
                        description=(
                            f"En mourant, **{player.display_name}** tire une dernière flèche\n"
                            f"et touche **{target.display_name}** !"
                        ),
                        color=C.COLOR_DEATH,
                    )
                )
            await game.kill_player(target, reason="chasseur")

    async def shoot(self, game: "Game", hunter: "Player", target: "Player") -> None:
        """Enregistre la cible du Chasseur et déclenche l'événement."""
        game.night_state.hunter_shot = target
        self._shot_event.set()


class HunterView(discord.ui.View):
    def __init__(
        self,
        game: "Game",
        player: "Player",
        hunter: "Hunter",
        targets: list["Player"],
    ):
        super().__init__(timeout=None)
        self.game   = game
        self.player = player
        self.hunter = hunter
        self._used  = False

        for target in targets:
            btn = discord.ui.Button(
                label=f"🎯 {target.display_name}",
                style=discord.ButtonStyle.danger,
            )
            btn.callback = self._make_callback(target)
            self.add_item(btn)

    def _make_callback(self, target: "Player"):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.member.id:
                await interaction.response.send_message("Ce n'est pas votre choix.", ephemeral=True)
                return
            if self._used:
                await interaction.response.send_message("Vous avez déjà tiré.", ephemeral=True)
                return
            self._used = True
            self.stop()
            await self.hunter.shoot(self.game, self.player, target)
            await interaction.response.send_message(
                f"🏹 Vous visez **{target.display_name}**… *Flèche lancée !*", ephemeral=True
            )
        return callback
