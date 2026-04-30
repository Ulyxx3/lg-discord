"""
roles/thief.py — Le Voleur.
La première nuit, il peut échanger son rôle avec l'une des 2 cartes réservées.
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


class Thief(BaseRole):
    name             = "Voleur"
    team             = "village"
    description      = "1ère nuit : échangez votre rôle avec l'une des 2 cartes réservées (ou gardez le vôtre)."
    emoji            = "🃏"
    night_order      = 1
    extension        = "base"
    first_night_only = True

    def __init__(self):
        self.reserve_cards: list[str] = []   # Rempli par game.distribute_roles()

    async def night_action(self, game: "Game", player: "Player") -> None:
        channel = player.private_text
        if not channel:
            return

        if not self.reserve_cards:
            await channel.send("*Aucune carte de réserve n'est disponible.*")
            player.action_event.set()
            return

        embed = discord.Embed(
            title="🃏 Le Voleur se réveille…",
            description=(
                "Deux cartes ont été mises de côté.\n"
                "Vous pouvez **échanger votre rôle** avec l'une d'elles, ou **garder le vôtre**.\n\n"
                f"⏳ Vous avez **{game.game_config.night_role_timeout}s** pour décider."
            ),
            color=C.COLOR_INFO,
        )

        view = ThiefView(game, player, self)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            # Règle officielle : s'il y a deux loups dans la réserve, le Voleur DOIT changer
            if all(c in ("Loup-Garou", "Grand Méchant Loup", "Village Infect") for c in self.reserve_cards):
                new_role_name = self.reserve_cards[0]
                await self._exchange(game, player, new_role_name)
                await channel.send(
                    "⏳ *Temps écoulé. Les deux cartes étant des Loups-Garous, vous devez en prendre une !*\n"
                    f"**Nouveau rôle : {new_role_name}**"
                )
            else:
                await channel.send("⏳ *Le Voleur garde son rôle actuel.*")
        finally:
            player.action_event.clear()

    async def _exchange(self, game: "Game", player: "Player", role_name: str) -> None:
        """Effectue l'échange de rôle."""
        from roles.registry import ROLE_REGISTRY
        role_cls = ROLE_REGISTRY.get(role_name)
        if role_cls:
            player.role = role_cls()
            log.info("Voleur (%s) a pris le rôle : %s", player.display_name, role_name)


class ThiefView(discord.ui.View):
    def __init__(self, game: "Game", player: "Player", thief: "Thief"):
        super().__init__(timeout=None)
        self.game   = game
        self.player = player
        self.thief  = thief
        self._used  = False

        for i, card_name in enumerate(thief.reserve_cards):
            btn = discord.ui.Button(
                label=f"Prendre : {card_name}",
                style=discord.ButtonStyle.primary,
            )
            btn.callback = self._make_callback(card_name)
            self.add_item(btn)

        keep_btn = discord.ui.Button(label="Garder mon rôle", style=discord.ButtonStyle.secondary)
        keep_btn.callback = self._keep_callback
        self.add_item(keep_btn)

    def _make_callback(self, role_name: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.member.id:
                await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
                return
            if self._used:
                await interaction.response.send_message("Vous avez déjà choisi.", ephemeral=True)
                return
            self._used = True
            self.stop()
            await self.thief._exchange(self.game, self.player, role_name)
            self.player.action_event.set()
            await interaction.response.send_message(
                f"🃏 Vous avez pris le rôle **{role_name}** !\n"
                "*Votre nouveau destin commence…*",
                ephemeral=True,
            )
        return callback

    async def _keep_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.member.id:
            await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
            return
        if self._used:
            await interaction.response.send_message("Vous avez déjà choisi.", ephemeral=True)
            return
        # Règle : ne peut garder que si au moins un des cartes n'est pas loup
        wolves_cards = {"Loup-Garou", "Grand Méchant Loup", "Village Infect"}
        all_wolves   = all(c in wolves_cards for c in self.thief.reserve_cards)
        if all_wolves:
            await interaction.response.send_message(
                "❌ Les deux cartes de réserve sont des Loups-Garous. Vous devez en prendre une !",
                ephemeral=True,
            )
            return
        self._used = True
        self.stop()
        self.player.action_event.set()
        await interaction.response.send_message(
            "🃏 Vous gardez votre rôle actuel.", ephemeral=True
        )
