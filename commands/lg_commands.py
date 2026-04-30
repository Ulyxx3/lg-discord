"""
commands/lg_commands.py — Toutes les commandes /lg (Setup, Admin, Action).
Regroupées pour éviter les conflits de groupe de commandes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from core.game import get_game
from core.state_machine import GamePhase
from core.channel_manager import ChannelManager
from phases.setup_phase import SetupPhase, ConfigView

import config as C

if TYPE_CHECKING:
    from core.game import Game

log = logging.getLogger(__name__)


class LGCog(commands.Cog):
    """Toutes les commandes du jeu Loup-Garou."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    lg = app_commands.Group(name="lg", description="Commandes Loup-Garou")

    # ─── COMMANDES DE SETUP ───────────────────────────────────────────────────

    @lg.command(name="setup", description="[Admin] Initialise la structure du serveur pour le Loup-Garou")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_guild(self, interaction: discord.Interaction) -> None:
        """Configure le serveur : crée les rôles Discord, catégories et salons de base."""
        await interaction.response.defer(ephemeral=True)

        game           = get_game(interaction.guild, self.bot)
        channel_manager = ChannelManager(game)
        game.channel_manager = channel_manager  # type: ignore[attr-defined]

        try:
            await channel_manager.setup_guild()
            await interaction.followup.send(
                embed=discord.Embed(
                    title="✅ Serveur configuré !",
                    description=(
                        "Les salons et rôles Discord ont été créés avec succès.\n\n"
                        "**Prochaines étapes :**\n"
                        "1. `/lg config` — Configurez le deck de rôles\n"
                        "2. Demandez aux joueurs de faire `/lg join`\n"
                        "3. `/lg start` — Lancez la partie !"
                    ),
                    color=C.COLOR_CONFIG,
                ),
                ephemeral=True,
            )
            log.info("Serveur %s configuré par %s", interaction.guild.name, interaction.user)
        except Exception as e:
            log.error("Erreur setup : %s", e, exc_info=True)
            await interaction.followup.send(
                f"❌ Erreur lors du setup : `{e}`", ephemeral=True
            )

    @lg.command(name="config", description="[Admin] Configure le deck de rôles et les extensions")
    @app_commands.checks.has_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction) -> None:
        """Ouvre le panneau de configuration interactif."""
        game = get_game(interaction.guild, self.bot)

        from utils.embed_builder import build_config_embed
        embed = build_config_embed(game)
        view  = ConfigView(game)

        await interaction.response.send_message(
            embed=embed, view=view, ephemeral=True
        )

    @lg.command(name="deck", description="[Admin] Modifie la quantité d'un rôle dans le deck")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        role="Nom exact du rôle (ex: Loup-Garou, Sorcière…)",
        quantity="Nombre de cartes (0 pour retirer le rôle)",
    )
    async def deck(
        self, interaction: discord.Interaction, role: str, quantity: int
    ) -> None:
        """Ajuste le nombre de cartes d'un rôle dans le deck de la partie."""
        from roles.registry import ROLE_REGISTRY

        game = get_game(interaction.guild, self.bot)

        if role not in ROLE_REGISTRY:
            known = ", ".join(sorted(ROLE_REGISTRY.keys()))
            await interaction.response.send_message(
                f"❌ Rôle inconnu : **{role}**\n\nRôles disponibles :\n```{known}```",
                ephemeral=True,
            )
            return

        if quantity < 0:
            await interaction.response.send_message("La quantité doit être ≥ 0.", ephemeral=True)
            return

        if quantity == 0:
            game.game_config.deck.pop(role, None)
        else:
            game.game_config.deck[role] = quantity

        await game.save()
        await interaction.response.send_message(
            f"✅ **{role}** : {quantity} carte(s) dans le deck.", ephemeral=True
        )

    # ─── COMMANDES D'ADMINISTRATION ──────────────────────────────────────────

    @lg.command(name="start", description="[Admin] Lance la partie")
    @app_commands.checks.has_permissions(administrator=True)
    async def start(self, interaction: discord.Interaction) -> None:
        game = get_game(interaction.guild, self.bot)

        if game.phase not in (GamePhase.IDLE, GamePhase.WAITING):
            await interaction.response.send_message("❌ Une partie est déjà en cours.", ephemeral=True)
            return

        if game.player_count < C.MIN_PLAYERS:
            await interaction.response.send_message(
                f"❌ Il faut au moins {C.MIN_PLAYERS} joueurs pour commencer.", ephemeral=True
            )
            return

        errors = game.game_config.validate(game.player_count)
        if errors:
            await interaction.response.send_message(
                "❌ Configuration invalide :\n" + "\n".join(f"• {e}" for e in errors),
                ephemeral=True,
            )
            return

        await interaction.response.send_message("🚀 Lancement de la partie…", ephemeral=True)

        if not hasattr(game, "channel_manager") or game.channel_manager is None:
            game.channel_manager = ChannelManager(game)

        setup_phase = SetupPhase(game)
        try:
            await game.channel_manager.create_private_houses()
        except Exception as e:
            log.error("Erreur création maisons : %s", e, exc_info=True)
            await interaction.followup.send(f"❌ Erreur : `{e}`", ephemeral=True)
            return

        await setup_phase.distribute_and_notify()
        asyncio.create_task(self._game_loop(game))

        if game.village_text:
            await game.village_text.send(
                embed=discord.Embed(
                    title="🎮 La partie commence !",
                    description=f"**{game.player_count} joueurs** participent.\n🌙 *La première nuit tombe…*",
                    color=C.COLOR_NIGHT,
                )
            )

    async def _game_loop(self, game: Game) -> None:
        from phases.night_phase import NightPhase
        from phases.day_phase   import DayPhase
        from phases.vote_phase  import VotePhase
        from utils.narrator     import Narrator

        narrator    = Narrator(game)
        night_phase = NightPhase(game)
        day_phase   = DayPhase(game)
        vote_phase  = VotePhase(game)

        try:
            while True:
                await night_phase.run()
                winner = game.check_victory()
                if winner: break

                await day_phase.run()
                winner = game.check_victory()
                if winner: break

                await vote_phase.run()
                winner = game.check_victory()
                if winner: break
        except Exception as e:
            log.error("ERREUR GAME LOOP : %s", e, exc_info=True)
            if game.logs_channel: await game.logs_channel.send(f"🚨 Erreur critique : `{e}`")
        finally:
            if winner: await narrator.announce_victory(winner)
            await self._end_game(game)

    async def _end_game(self, game: Game) -> None:
        game.phase = GamePhase.GAME_OVER
        await game.save()
        for player in game.players.values():
            try:
                roles = [r for r in [game.role_player, game.role_wolf, game.role_dead] if r and r in player.member.roles]
                if roles: await player.member.remove_roles(*roles)
            except discord.HTTPException: pass

        if hasattr(game, "channel_manager") and game.channel_manager:
            await game.channel_manager.destroy_private_houses()
            await game.channel_manager.set_village_day_permissions()
            await game.channel_manager.move_all_to_village()

        await game.persistence.delete(game.guild.id)
        game.phase = GamePhase.IDLE
        game.players = {}
        game.night_count = 0

    @lg.command(name="stop", description="[Admin] Arrête la partie")
    @app_commands.checks.has_permissions(administrator=True)
    async def stop(self, interaction: discord.Interaction) -> None:
        game = get_game(interaction.guild, self.bot)
        if game.phase == GamePhase.IDLE:
            await interaction.response.send_message("Aucune partie en cours.", ephemeral=True)
            return
        await interaction.response.send_message("⛔ Partie arrêtée.", ephemeral=True)
        await self._end_game(game)

    @lg.command(name="status", description="Affiche l'état de la partie")
    async def status(self, interaction: discord.Interaction) -> None:
        game = get_game(interaction.guild, self.bot)
        from utils.embed_builder import build_status_embed
        await interaction.response.send_message(embed=build_status_embed(game), ephemeral=True)

    @lg.command(name="open", description="[Admin] Ouvre les inscriptions")
    @app_commands.checks.has_permissions(administrator=True)
    async def open_registration(self, interaction: discord.Interaction) -> None:
        game  = get_game(interaction.guild, self.bot)
        setup = SetupPhase(game)
        if not hasattr(game, "channel_manager") or game.channel_manager is None:
            game.channel_manager = ChannelManager(game)
        await setup.start_registration()
        await interaction.response.send_message("📣 Inscriptions ouvertes !", ephemeral=True)

    # ─── COMMANDES DE JOUEURS ────────────────────────────────────────────────

    @lg.command(name="join", description="Rejoindre la partie")
    async def join(self, interaction: discord.Interaction) -> None:
        game  = get_game(interaction.guild, self.bot)
        setup = SetupPhase(game)
        ok, msg = await setup.add_player(interaction.user)
        await interaction.response.send_message(msg, ephemeral=True)

    @lg.command(name="leave", description="Quitter la partie")
    async def leave(self, interaction: discord.Interaction) -> None:
        game  = get_game(interaction.guild, self.bot)
        setup = SetupPhase(game)
        ok, msg = await setup.remove_player(interaction.user)
        await interaction.response.send_message(msg, ephemeral=True)

    @lg.command(name="role", description="Voir votre rôle secret")
    async def role(self, interaction: discord.Interaction) -> None:
        game   = get_game(interaction.guild, self.bot)
        player = game.get_player(interaction.user)
        if not player or not player.role:
            await interaction.response.send_message("Vous n'avez pas de rôle.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{player.role.emoji} {player.role.name}", description=player.role.description)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @lg.command(name="players", description="Liste des joueurs vivants")
    async def players(self, interaction: discord.Interaction) -> None:
        game = get_game(interaction.guild, self.bot)
        alive = game.alive_players
        if not alive:
            await interaction.response.send_message("Personne n'est en vie.", ephemeral=True)
            return
        from utils.embed_builder import build_player_list_embed
        await interaction.response.send_message(embed=build_player_list_embed(alive), ephemeral=True)

    @lg.command(name="revote", description="[Juge Bègue] Second vote")
    async def revote(self, interaction: discord.Interaction) -> None:
        game = get_game(interaction.guild, self.bot)
        player = game.get_player(interaction.user)
        if not player or not player.role or player.role.name != "Juge Bègue":
            await interaction.response.send_message("Action impossible.", ephemeral=True)
            return
        msg = await player.role.request_revote(game, player)
        await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LGCog(bot))
