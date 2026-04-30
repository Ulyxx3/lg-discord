"""
roles/actor.py — L'Acteur.
Chaque nuit, il peut revêtir temporairement le rôle d'un autre personnage
parmi 3 cartes tirées au sort, et utiliser ses pouvoirs.
Usage unique par rôle.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING

import discord

from roles.base_role import BaseRole
import config as C

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player

log = logging.getLogger(__name__)

# Rôles que l'Acteur peut imiter (rôles avec actions nocturnes intéressantes)
ACTOR_AVAILABLE_ROLES = [
    "Voyante", "Sorcière", "Chasseur", "Salvateur", "Renard",
    "Idiot du Village", "Montreur d'Ours", "Juge Bègue",
]


class Actor(BaseRole):
    name        = "Acteur"
    team        = "village"
    description = "3× par partie : jouez le rôle d'un personnage tiré au sort et utilisez ses pouvoirs."
    emoji       = "🎭"
    night_order = 0
    extension   = "nouvelle_lune"

    def __init__(self):
        self.remaining_uses:  int       = 3
        self.used_roles:      set[str]  = set()
        self._available_cards: list[str] = []

    async def night_action(self, game: "Game", player: "Player") -> None:
        if self.remaining_uses <= 0:
            player.action_event.set()
            return

        channel = player.private_text
        if not channel:
            return

        # Tire 3 rôles au hasard parmi ceux non encore utilisés
        pool = [r for r in ACTOR_AVAILABLE_ROLES if r not in self.used_roles]
        cards = random.sample(pool, min(3, len(pool))) if pool else []

        if not cards:
            await channel.send("🎭 *Vous n'avez plus de rôles disponibles à imiter.*")
            player.action_event.set()
            return

        embed = discord.Embed(
            title="🎭 L'Acteur se prépare…",
            description=(
                f"Il vous reste **{self.remaining_uses}** utilisation(s).\n"
                "Choisissez un rôle à jouer cette nuit, ou passez :\n\n"
                + "\n".join(f"• **{c}**" for c in cards)
            ),
            color=C.COLOR_INFO,
        )

        view = ActorView(game, player, self, cards)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            await channel.send("⏳ *L'Acteur reste dans les coulisses cette nuit.*")
        finally:
            player.action_event.clear()

    async def play_as(self, game: "Game", player: "Player", role_name: str) -> None:
        """Joue le tour du rôle choisi."""
        from roles.registry import ROLE_REGISTRY
        role_cls = ROLE_REGISTRY.get(role_name)
        if not role_cls:
            return
        temp_role = role_cls()
        self.remaining_uses -= 1
        self.used_roles.add(role_name)
        log.info("Acteur (%s) joue le rôle : %s", player.display_name, role_name)
        # Exécute l'action nocturne du rôle imité
        await temp_role.night_action(game, player)
        player.action_event.set()


class ActorView(discord.ui.View):
    def __init__(self, game, player, actor, cards):
        super().__init__(timeout=None)
        self.game   = game
        self.player = player
        self.actor  = actor
        self._used  = False

        for card in cards:
            btn = discord.ui.Button(label=f"🎭 {card}", style=discord.ButtonStyle.primary)
            btn.callback = self._make_callback(card)
            self.add_item(btn)

        skip = discord.ui.Button(label="Passer", style=discord.ButtonStyle.secondary)
        skip.callback = self._skip
        self.add_item(skip)

    def _make_callback(self, role_name: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.member.id or self._used:
                return
            self._used = True
            self.stop()
            await interaction.response.defer()
            await self.actor.play_as(self.game, self.player, role_name)
        return callback

    async def _skip(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.member.id:
            return
        self._used = True
        self.stop()
        self.player.action_event.set()
        await interaction.response.send_message("Vous passez cette nuit.", ephemeral=True)
