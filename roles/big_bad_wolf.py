"""
roles/big_bad_wolf.py — Le Grand Méchant Loup.
Tant que tous les rôles spéciaux du village sont vivants,
il mange une deuxième victime (en plus de celle des loups).
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

VILLAGE_SPECIALS = {
    "Voyante", "Sorcière", "Chasseur", "Cupidon", "Voleur",
    "Salvateur", "Ancien", "Idiot du Village", "Renard",
    "Montreur d'Ours", "Petite Fille", "Enfant Sauvage",
    "Juge Bègue", "Servante Rusée", "Les Deux Sœurs", "Les Trois Frères",
}


class BigBadWolf(BaseRole):
    name        = "Grand Méchant Loup"
    team        = "loups"
    description = "Tant que les rôles spéciaux village sont vivants : mange une 2ème victime chaque nuit."
    emoji       = "🦁"
    night_order = 8  # Agit en même temps que les loups
    extension   = "nouvelle_lune"

    async def night_action(self, game: "Game", player: "Player") -> None:
        """
        S'il y a encore des rôles spéciaux village en vie,
        le Grand Méchant Loup peut désigner une 2ème victime.
        """
        channel = player.private_text
        if not channel:
            return

        # Vérifie si des rôles spéciaux village sont encore en vie
        specials_alive = [
            p for p in game.alive_players
            if p.role and p.role.name in VILLAGE_SPECIALS
        ]
        if not specials_alive:
            await channel.send(
                "🦁 *Plus aucun rôle spécial villageois n'est en vie. "
                "Vous ne pouvez pas manger de deuxième victime.*"
            )
            player.action_event.set()
            return

        # Victimes éligibles : vivants, pas déjà ciblés par les loups, pas soi-même
        wolf_victim_id = game.night_state.wolf_victim.id if game.night_state.wolf_victim else None
        eligible = [
            p for p in game.alive_players
            if p != player and p.id != wolf_victim_id
            and (p.role and p.role.team != "loups")
        ]

        if not eligible:
            player.action_event.set()
            return

        embed = discord.Embed(
            title="🦁 Le Grand Méchant Loup rugit…",
            description=(
                "Des rôles spéciaux du village sont encore en vie.\n"
                "Choisissez une **deuxième victime** à dévorer cette nuit !\n"
                f"⏳ {game.game_config.night_role_timeout}s"
            ),
            color=C.COLOR_WOLVES,
        )

        view = BigBadWolfView(game, player, eligible)
        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(), timeout=game.game_config.night_role_timeout
            )
        except asyncio.TimeoutError:
            await channel.send("⏳ *Vous laissez passer la nuit sans choisir.*")
        finally:
            player.action_event.clear()


class BigBadWolfView(discord.ui.View):
    def __init__(self, game, player, targets):
        super().__init__(timeout=None)
        self.game   = game
        self.player = player
        self._used  = False

        for target in targets:
            btn = discord.ui.Button(label=target.display_name, style=discord.ButtonStyle.danger)
            btn.callback = self._make_callback(target)
            self.add_item(btn)

        skip = discord.ui.Button(label="Passer", style=discord.ButtonStyle.secondary)
        skip.callback = self._skip
        self.add_item(skip)

    def _make_callback(self, target):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.member.id or self._used:
                return
            self._used = True
            self.stop()
            # Stocke la 2ème victime dans night_state (champ dédié)
            self.game.night_state.big_bad_wolf_victim = target  # type: ignore[attr-defined]
            self.player.action_event.set()
            await interaction.response.send_message(
                f"🦁 Vous ciblez **{target.display_name}** comme deuxième victime.", ephemeral=True
            )
        return callback

    async def _skip(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.member.id:
            return
        self._used = True
        self.stop()
        self.player.action_event.set()
        await interaction.response.send_message("Vous passez.", ephemeral=True)
