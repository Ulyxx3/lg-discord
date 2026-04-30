"""
phases/setup_phase.py — Phase de configuration et d'inscription.
Gère /lg config (configuration du deck) et /lg join (inscription des joueurs).
"""

from __future__ import annotations

import logging
import random
from typing import Optional, TYPE_CHECKING

import discord

from core.state_machine import GamePhase
from core.game_config import ROLES_BY_EXTENSION, EXTENSIONS

import config as C

if TYPE_CHECKING:
    from core.game import Game

log = logging.getLogger(__name__)


class SetupPhase:
    """Phase d'attente et de configuration avant le lancement."""

    def __init__(self, game: "Game"):
        self.game = game

    async def start_registration(self) -> None:
        """Passe en mode inscription dans le salon lobby."""
        game = self.game
        game.phase = GamePhase.WAITING
        await game.save()

        if not game.lobby_text:
            return

        embed = discord.Embed(
            title="🐺 Loup-Garou de Thiercelieux",
            description=(
                "Une nouvelle partie est en préparation !\n\n"
                "Pour rejoindre la partie, tapez `/lg join`\n"
                "L'admin peut configurer le deck avec `/lg config`\n"
                "Lorsque tout le monde est prêt : `/lg start`\n\n"
                f"*Joueurs : 0 / {C.MAX_PLAYERS}*"
            ),
            color=C.COLOR_NIGHT,
        )
        embed.set_footer(text="Connectez-vous au salon vocal 🔊・Le Village pour participer.")
        await game.lobby_text.send(embed=embed)

    async def add_player(self, member: discord.Member) -> tuple[bool, str]:
        """
        Ajoute un joueur à la partie.
        Retourne (succès, message).
        """
        game = self.game

        if game.phase not in (GamePhase.WAITING, GamePhase.IDLE):
            return False, "Une partie est déjà en cours. Attendez la prochaine."

        if game.get_player(member) is not None:
            return False, "Vous êtes déjà inscrit·e dans cette partie."

        if game.player_count >= C.MAX_PLAYERS:
            return False, f"La partie est complète ({C.MAX_PLAYERS} joueurs max)."

        player = game.add_player(member)

        # Donne le rôle Discord "Joueur LG"
        if game.role_player:
            try:
                await member.add_roles(game.role_player)
            except discord.HTTPException:
                pass

        log.info("%s a rejoint la partie (%d joueurs)", member.display_name, game.player_count)
        await game.save()
        return True, f"✅ Vous avez rejoint la partie ! ({game.player_count} joueur(s) inscrit(s))"

    async def remove_player(self, member: discord.Member) -> tuple[bool, str]:
        """Retire un joueur de la phase d'inscription."""
        game = self.game
        if game.phase not in (GamePhase.WAITING,):
            return False, "Impossible de quitter une partie en cours."
        if game.get_player(member) is None:
            return False, "Vous n'êtes pas inscrit·e."

        game.remove_player(member.id)
        if game.role_player and game.role_player in member.roles:
            try:
                await member.remove_roles(game.role_player)
            except discord.HTTPException:
                pass

        await game.save()
        return True, "Vous avez quitté la partie."

    async def distribute_and_notify(self) -> None:
        """Distribue les rôles et notifie chaque joueur dans son salon privé."""
        game    = self.game
        players = game.distribute_roles()

        for player in players:
            if not player.private_text or not player.role:
                continue

            role       = player.role
            color      = C.COLOR_WOLVES if role.team == "loups" else C.COLOR_DAY
            if role.team == "neutre":
                color = C.COLOR_NIGHT

            embed = discord.Embed(
                title=f"{role.emoji} Votre rôle secret",
                description=(
                    f"**{role.name}**\n\n"
                    f"{role.description}\n\n"
                    f"*Équipe : {'⚔️ Loups' if role.team == 'loups' else '🏘️ Village' if role.team == 'village' else '🎭 Solitaire'}*"
                ),
                color=color,
            )
            embed.set_footer(text="Ne révélez jamais votre rôle ! Le bot garantit votre anonymat.")

            try:
                await player.private_text.send(embed=embed)
            except discord.HTTPException as e:
                log.warning("Impossible d'envoyer le rôle à %s : %s", player.display_name, e)

        log.info("Rôles distribués et notifiés à tous les joueurs.")


class ConfigView(discord.ui.View):
    """
    Interface de configuration du deck avant la partie.
    Sélection des extensions et ajustement des quantités par rôle.
    """

    def __init__(self, game: "Game"):
        super().__init__(timeout=300)
        self.game = game
        self._build_extension_buttons()

    def _build_extension_buttons(self) -> None:
        for ext_id, ext_name in EXTENSIONS.items():
            enabled = ext_id in self.game.game_config.enabled_extensions
            btn = discord.ui.Button(
                label=f"{'✅' if enabled else '❌'} {ext_name}",
                style=discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary,
                custom_id=f"ext_{ext_id}",
            )
            btn.callback = self._make_ext_callback(ext_id, ext_name)
            self.add_item(btn)

        # Bouton pour ouvrir le sélecteur de rôles détaillé
        detail_btn = discord.ui.Button(
            label="🃏 Ajuster le deck de rôles",
            style=discord.ButtonStyle.primary,
            row=1,
        )
        detail_btn.callback = self._open_deck_editor
        self.add_item(detail_btn)

    def _make_ext_callback(self, ext_id: str, ext_name: str):
        async def callback(interaction: discord.Interaction):
            cfg = self.game.game_config
            if ext_id in cfg.enabled_extensions:
                cfg.enabled_extensions.discard(ext_id)
                await interaction.response.send_message(
                    f"❌ Extension **{ext_name}** désactivée.", ephemeral=True
                )
            else:
                cfg.enabled_extensions.add(ext_id)
                await interaction.response.send_message(
                    f"✅ Extension **{ext_name}** activée.", ephemeral=True
                )
            # Recharge les défauts du deck
            cfg._load_defaults()
            await self.game.save()
        return callback

    async def _open_deck_editor(self, interaction: discord.Interaction) -> None:
        """Affiche un résumé du deck actuel avec instructions pour le modifier."""
        deck  = self.game.game_config.deck
        total = self.game.game_config.total_cards()
        lines = [f"**{name}** : {count}" for name, count in deck.items() if count > 0]
        embed = discord.Embed(
            title="🃏 Deck actuel",
            description="\n".join(lines) or "*Deck vide*",
            color=C.COLOR_CONFIG,
        )
        embed.set_footer(
            text=f"Total : {total} cartes | "
                 "Utilisez /lg deck <rôle> <quantité> pour ajuster."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
