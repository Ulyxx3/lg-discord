"""
roles/wild_child.py — L'Enfant Sauvage.
La 1ère nuit, il choisit un modèle. Si le modèle meurt, l'Enfant Sauvage devient Loup-Garou.
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


class WildChild(BaseRole):
    name             = "Enfant Sauvage"
    team             = "village"
    description      = "1ère nuit : choisissez un modèle. S'il meurt, vous devenez Loup-Garou !"
    emoji            = "🧒"
    night_order      = 0   # Avant tous les autres (début de 1ère nuit)
    extension        = "nouvelle_lune"
    first_night_only = True

    def __init__(self):
        self.model_id: Optional[int] = None
        self._transformed: bool      = False

    async def night_action(self, game: "Game", player: "Player") -> None:
        channel = player.private_text
        if not channel:
            return

        others = [p for p in game.alive_players if p != player]
        embed = discord.Embed(
            title="🧒 L'Enfant Sauvage s'éveille…",
            description=(
                "Choisissez votre **modèle**.\n"
                "Tant qu'il est en vie, vous êtes du côté du village.\n"
                "**S'il meurt, vous devenez un Loup-Garou !**\n\n"
                f"⏳ {game.game_config.night_role_timeout}s"
            ),
            color=C.COLOR_INFO,
        )
        view = WildChildView(game, player, self, others)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            # Choisit aléatoirement si timeout
            import random
            if others:
                self.model_id = random.choice(others).id
            player.action_event.set()
        finally:
            player.action_event.clear()

    async def check_model_death(self, game: "Game", player: "Player") -> None:
        """
        Appelé par game.kill_player() si la victime est le modèle de l'Enfant Sauvage.
        L'Enfant Sauvage rejoint les loups.
        """
        if self._transformed or not player.is_alive:
            return
        self._transformed = True
        self.team = "loups"
        # Donne l'accès aux salons loups
        if game.role_wolf:
            try:
                await player.member.add_roles(game.role_wolf)
            except discord.HTTPException:
                pass
        if player.private_text:
            await player.private_text.send(
                embed=discord.Embed(
                    title="🐺 Vous rejoignez les loups !",
                    description=(
                        "Votre modèle est mort… La bête en vous se réveille.\n"
                        "**Vous êtes maintenant un Loup-Garou !**\n"
                        "Accédez au salon des loups dès ce soir."
                    ),
                    color=C.COLOR_WOLVES,
                )
            )
        # Ajoute aux loups visibles pour le bot
        log.info("Enfant Sauvage %s devient Loup-Garou !", player.display_name)


class WildChildView(discord.ui.View):
    def __init__(self, game, player, wild_child, targets):
        super().__init__(timeout=None)
        self.game       = game
        self.player     = player
        self.wild_child = wild_child
        self._used      = False

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
            self.wild_child.model_id = target.id
            self.player.action_event.set()
            await interaction.response.send_message(
                f"🧒 **{target.display_name}** est votre modèle. Protégez-le !",
                ephemeral=True,
            )
        return callback
