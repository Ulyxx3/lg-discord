"""
roles/witch.py — La Sorcière (rôle de référence, le plus complexe).
Possède deux potions à usage unique : vie (sauve la victime des loups) et mort (empoisonne).
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


class Witch(BaseRole):
    name        = "Sorcière"
    team        = "village"
    description = "Deux potions uniques : vie (sauve la victime des loups) et mort (empoisonne)."
    emoji       = "🧪"
    night_order = 9
    extension   = "base"

    def __init__(self):
        self.has_save_potion: bool = True
        self.has_kill_potion: bool = True

    async def night_action(self, game: "Game", player: "Player") -> None:
        """Envoie l'interface de la Sorcière dans son salon privé."""
        channel = player.private_text
        if not channel:
            return

        wolf_victim = game.night_state.wolf_victim

        embed = self._build_embed(wolf_victim, game)
        view  = WitchView(game, player, self)

        await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(
                player.action_event.wait(),
                timeout=game.game_config.night_role_timeout,
            )
        except asyncio.TimeoutError:
            await channel.send(
                "⏳ *La Sorcière s'est rendormie sans utiliser ses potions…*"
            )
        finally:
            player.action_event.clear()

    def _build_embed(self, wolf_victim: Optional["Player"], game: "Game") -> discord.Embed:
        embed = discord.Embed(
            title="🧪 La Sorcière se réveille…",
            color=C.COLOR_WITCH,
        )

        # Informe la Sorcière de la victime des loups
        if wolf_victim:
            embed.add_field(
                name="🐺 Victime des loups cette nuit",
                value=f"**{wolf_victim.display_name}** sera dévoré·e à l'aube.",
                inline=False,
            )
        else:
            embed.add_field(
                name="🐺 Victime des loups",
                value="*Les loups n'ont pas choisi de victime cette nuit.*",
                inline=False,
            )

        # État des potions
        save_status = "✅ Disponible" if self.has_save_potion else "❌ Utilisée"
        kill_status = "✅ Disponible" if self.has_kill_potion else "❌ Utilisée"
        embed.add_field(name="💊 Potion de Vie",  value=save_status, inline=True)
        embed.add_field(name="☠️ Potion de Mort", value=kill_status, inline=True)

        embed.set_footer(text=f"⏳ Vous avez {game.game_config.night_role_timeout}s pour agir.")
        return embed

    async def use_save(self, game: "Game", witch: "Player") -> str:
        """
        Utilise la potion de vie : sauve la victime des loups.
        Retourne un message de confirmation.
        """
        if not self.has_save_potion:
            raise ValueError("Vous avez déjà utilisé votre potion de vie.")
        if not game.night_state.wolf_victim:
            raise ValueError("Il n'y a pas de victime à sauver cette nuit.")
        self.has_save_potion = False
        game.night_state.witch_saved = True
        saved = game.night_state.wolf_victim
        game.night_state.wolf_victim = None  # La victime est sauvée
        witch.action_event.set()
        log.info("Sorcière sauve %s", saved.display_name)
        return f"✨ Vous avez sauvé **{saved.display_name}** des griffes des loups !"

    async def use_kill(
        self, game: "Game", witch: "Player", target: "Player"
    ) -> str:
        """
        Utilise la potion de mort : empoisonne un joueur.
        Retourne un message de confirmation.
        """
        if not self.has_kill_potion:
            raise ValueError("Vous avez déjà utilisé votre potion de mort.")
        if not target.is_alive:
            raise ValueError(f"**{target.display_name}** est déjà mort·e.")
        self.has_kill_potion = False
        game.night_state.witch_victim = target
        witch.action_event.set()
        log.info("Sorcière empoisonne %s", target.display_name)
        return f"☠️ Vous avez empoisonné **{target.display_name}**. Il mourra à l'aube."

    async def skip(self, witch: "Player") -> None:
        """La Sorcière passe sans utiliser de potion."""
        witch.action_event.set()


# ─── Interface Discord : boutons de la Sorcière ──────────────────────────────

class WitchView(discord.ui.View):
    """
    Interface boutons pour la Sorcière.
    - Bouton "Sauver" (si potion disponible ET victime existe)
    - Bouton "Empoisonner" (si potion disponible) → ouvre un sélecteur de cible
    - Bouton "Passer"
    """

    def __init__(self, game: "Game", player: "Player", witch: "Witch"):
        super().__init__(timeout=None)
        self.game   = game
        self.player = player
        self.witch  = witch
        self._used  = False

        # Bouton Sauver
        has_victim  = game.night_state.wolf_victim is not None
        save_btn    = discord.ui.Button(
            label="💊 Sauver la victime",
            style=discord.ButtonStyle.success,
            disabled=not (witch.has_save_potion and has_victim),
        )
        save_btn.callback = self._save_callback
        self.add_item(save_btn)

        # Bouton Empoisonner
        kill_btn = discord.ui.Button(
            label="☠️ Empoisonner un joueur",
            style=discord.ButtonStyle.danger,
            disabled=not witch.has_kill_potion,
        )
        kill_btn.callback = self._kill_callback
        self.add_item(kill_btn)

        # Bouton Passer
        skip_btn = discord.ui.Button(
            label="😴 Passer cette nuit",
            style=discord.ButtonStyle.secondary,
        )
        skip_btn.callback = self._skip_callback
        self.add_item(skip_btn)

    def _check_author(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.player.member.id

    async def _save_callback(self, interaction: discord.Interaction):
        if not self._check_author(interaction):
            await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
            return
        if self._used:
            await interaction.response.send_message("Vous avez déjà agi.", ephemeral=True)
            return
        try:
            msg = await self.witch.use_save(self.game, self.player)
            self._used = True
            self.stop()
            await interaction.response.send_message(msg, ephemeral=True)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)

    async def _kill_callback(self, interaction: discord.Interaction):
        if not self._check_author(interaction):
            await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
            return
        if self._used:
            await interaction.response.send_message("Vous avez déjà agi.", ephemeral=True)
            return
        # Affiche le sélecteur de cible
        alive_targets = [p for p in self.game.alive_players if p != self.player]
        select_view   = WitchKillSelect(self.game, self.player, self.witch, alive_targets, self)
        await interaction.response.send_message(
            "☠️ Choisissez votre victime :", view=select_view, ephemeral=True
        )

    async def _skip_callback(self, interaction: discord.Interaction):
        if not self._check_author(interaction):
            await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
            return
        self._used = True
        self.stop()
        await self.witch.skip(self.player)
        await interaction.response.send_message(
            "😴 Vous vous rendormez sans agir.", ephemeral=True
        )


class WitchKillSelect(discord.ui.View):
    """Sélecteur de cible pour la potion de mort."""

    def __init__(
        self,
        game: "Game",
        player: "Player",
        witch: "Witch",
        targets: list["Player"],
        parent_view: WitchView,
    ):
        super().__init__(timeout=None)
        self.game        = game
        self.player      = player
        self.witch       = witch
        self.parent_view = parent_view

        for target in targets:
            btn = discord.ui.Button(
                label=target.display_name,
                style=discord.ButtonStyle.danger,
            )
            btn.callback = self._make_callback(target)
            self.add_item(btn)

        cancel_btn = discord.ui.Button(label="Annuler", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self._cancel
        self.add_item(cancel_btn)

    def _make_callback(self, target: "Player"):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.member.id:
                await interaction.response.send_message("Ce n'est pas votre tour.", ephemeral=True)
                return
            try:
                msg = await self.witch.use_kill(self.game, self.player, target)
                self.parent_view._used = True
                self.parent_view.stop()
                self.stop()
                await interaction.response.send_message(msg, ephemeral=True)
            except ValueError as e:
                await interaction.response.send_message(str(e), ephemeral=True)
        return callback

    async def _cancel(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_message("Action annulée.", ephemeral=True)
