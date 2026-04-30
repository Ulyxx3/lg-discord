"""
core/channel_manager.py — Création, configuration et suppression des salons Discord.
Gère les permissions pour garantir l'anonymat des rôles.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord

import config as C
from utils.move_queue import MoveQueue

log = logging.getLogger(__name__)


class ChannelManager:
    """
    Gère l'ensemble des salons Discord pour une partie de Loup-Garou.
    Appelé par /lg setup (initialisation du serveur) et pendant le jeu
    (création des maisons privées, gestion des permissions).
    """

    def __init__(self, game):
        from core.game import Game
        self.game: "Game" = game
        self.guild = game.guild
        self.move_queue = MoveQueue()

    # ─────────────────────────────────────────────────────────────────────────
    # SETUP : Initialisation de la structure du serveur (/lg setup)
    # ─────────────────────────────────────────────────────────────────────────

    async def setup_guild(self) -> None:
        """
        Configure la structure complète du serveur Discord.
        Crée les rôles Discord et les catégories/salons de base.
        Doit être appelé une seule fois par /lg setup.
        """
        log.info("Initialisation du serveur %s…", self.guild.name)

        await self._create_discord_roles()
        await self._create_village_channels()
        await self._create_wolves_channels()
        await self._create_admin_channels()

        log.info("Serveur configuré avec succès.")

    async def _create_discord_roles(self) -> None:
        """Crée les rôles Discord nécessaires au bot."""
        existing = {r.name: r for r in self.guild.roles}

        async def get_or_create(name: str, **kwargs) -> discord.Role:
            if name in existing:
                return existing[name]
            return await self.guild.create_role(name=name, **kwargs)

        self.game.role_player    = await get_or_create(C.DISCORD_ROLE_PLAYER,    color=discord.Color.blurple(),    mentionable=True)
        self.game.role_wolf      = await get_or_create(C.DISCORD_ROLE_WOLF,      color=discord.Color.dark_red(),   mentionable=False)
        self.game.role_dead      = await get_or_create(C.DISCORD_ROLE_DEAD,      color=discord.Color.dark_gray(),  mentionable=False)
        self.game.role_spectator = await get_or_create(C.DISCORD_ROLE_SPECTATOR, color=discord.Color.light_gray(), mentionable=False)

        log.info("Rôles Discord créés/vérifiés.")

    async def _create_village_channels(self) -> None:
        """Crée la catégorie Village avec salon textuel + vocal."""
        everyone = self.guild.default_role

        # Permissions : tout le monde peut voir et parler
        village_overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            everyone: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                speak=True,
                connect=True,
            ),
            self.guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                manage_channels=True, move_members=True,
                speak=True, connect=True,
            ),
        }

        # Pendant la nuit, on mute @everyone — géré dynamiquement par night_phase
        cat = await self._get_or_create_category(C.CATEGORY_VILLAGE, village_overwrites)

        self.game.village_text  = await self._get_or_create_text(
            C.CHANNEL_VILLAGE_TEXT, cat, village_overwrites
        )
        self.game.village_voice = await self._get_or_create_voice(
            C.CHANNEL_VILLAGE_VOICE, cat, village_overwrites
        )

        # Salon d'attente / lobby
        self.game.lobby_text = await self._get_or_create_text(
            C.CHANNEL_LOBBY, cat, village_overwrites
        )

    async def _create_wolves_channels(self) -> None:
        """
        Crée la catégorie des Loups-Garous.
        Invisible pour @everyone, visible uniquement pour le rôle Loup-Garou et le bot.
        """
        everyone = self.guild.default_role
        wolf_role = self.game.role_wolf

        wolf_overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            everyone: discord.PermissionOverwrite(view_channel=False),
            self.guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                manage_channels=True, move_members=True,
                speak=True, connect=True,
            ),
        }
        if wolf_role:
            wolf_overwrites[wolf_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, speak=True, connect=True,
            )

        cat = await self._get_or_create_category(C.CATEGORY_WOLVES, wolf_overwrites)
        self.game.wolves_text  = await self._get_or_create_text(
            C.CHANNEL_WOLVES_TEXT, cat, wolf_overwrites
        )
        self.game.wolves_voice = await self._get_or_create_voice(
            C.CHANNEL_WOLVES_VOICE, cat, wolf_overwrites
        )

    async def _create_admin_channels(self) -> None:
        """Crée le salon de logs admin, visible uniquement par les administrateurs."""
        everyone = self.guild.default_role
        admin_overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            everyone: discord.PermissionOverwrite(view_channel=False),
            self.guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True,
            ),
        }
        # Donne accès aux membres avec permission Administrateur
        for role in self.guild.roles:
            if role.permissions.administrator and role != everyone:
                admin_overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True,
                )

        cat = await self._get_or_create_category(C.CATEGORY_ADMIN, admin_overwrites)
        self.game.logs_channel = await self._get_or_create_text(
            C.CHANNEL_LOGS, cat, admin_overwrites
        )

    # ─────────────────────────────────────────────────────────────────────────
    # MAISONS PRIVÉES : Créées au début de chaque partie
    # ─────────────────────────────────────────────────────────────────────────

    async def create_private_houses(self) -> None:
        """
        Crée un salon textuel ET vocal privé pour chaque joueur.
        Garantit l'anonymat : seuls le joueur concerné et le bot ont accès.
        """
        everyone  = self.guild.default_role
        bot_member = self.guild.me

        # Récupère ou crée la catégorie Maisons
        house_cat_overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            everyone:   discord.PermissionOverwrite(view_channel=False),
            bot_member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                manage_channels=True, move_members=True,
            ),
        }
        cat = await self._get_or_create_category(C.CATEGORY_HOUSES, house_cat_overwrites)

        for player in self.game.players.values():
            member    = player.member
            safe_name = self._safe_channel_name(member.display_name)

            per_player_overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True,
                    manage_channels=True, move_members=True, speak=True, connect=True,
                ),
                member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True,
                    speak=True, connect=True,
                ),
            }

            text_ch  = await self.guild.create_text_channel(
                f"maison-{safe_name}", category=cat, overwrites=per_player_overwrites,
                topic=f"Salon privé de {member.display_name} 🏠"
            )
            voice_ch = await self.guild.create_voice_channel(
                f"🏠・{member.display_name}", category=cat, overwrites=per_player_overwrites,
            )

            player.private_text  = text_ch
            player.private_voice = voice_ch
            log.debug("Maison créée pour %s", member.display_name)
            await asyncio.sleep(0.3)  # Rate-limit prudence lors de la création

    async def destroy_private_houses(self) -> None:
        """Supprime toutes les maisons privées à la fin de la partie."""
        for player in self.game.players.values():
            try:
                if player.private_text:
                    await player.private_text.delete(reason="Fin de partie LG")
                    player.private_text = None
                if player.private_voice:
                    await player.private_voice.delete(reason="Fin de partie LG")
                    player.private_voice = None
            except discord.HTTPException as e:
                log.warning("Impossible de supprimer la maison de %s : %s",
                            player.display_name, e)
            await asyncio.sleep(0.3)

    # ─────────────────────────────────────────────────────────────────────────
    # PERMISSIONS DYNAMIQUES (Jour / Nuit)
    # ─────────────────────────────────────────────────────────────────────────

    async def set_village_night_permissions(self) -> None:
        """Rend le village muet la nuit (désactive send_messages + speak pour @everyone)."""
        everyone = self.guild.default_role
        try:
            await self.game.village_text.set_permissions(
                everyone, send_messages=False, view_channel=True
            )
            await self.game.village_voice.set_permissions(
                everyone, speak=False, connect=True, view_channel=True
            )
        except (discord.HTTPException, AttributeError) as e:
            log.warning("Erreur permissions nuit village : %s", e)

    async def set_village_day_permissions(self) -> None:
        """Réouvre le village pour les débats de jour."""
        everyone = self.guild.default_role
        try:
            await self.game.village_text.set_permissions(
                everyone, send_messages=True, view_channel=True
            )
            await self.game.village_voice.set_permissions(
                everyone, speak=True, connect=True, view_channel=True
            )
        except (discord.HTTPException, AttributeError) as e:
            log.warning("Erreur permissions jour village : %s", e)

    # ─────────────────────────────────────────────────────────────────────────
    # DÉPLACEMENTS VOCAUX (via MoveQueue)
    # ─────────────────────────────────────────────────────────────────────────

    async def move_all_to_village(self) -> None:
        """Déplace tous les joueurs vivants vers le salon vocal du village."""
        members_in_voice = [
            p.member for p in self.game.alive_players
            if p.member.voice is not None
        ]
        if members_in_voice and self.game.village_voice:
            await self.move_queue.move(members_in_voice, self.game.village_voice)

    async def move_all_to_houses(self) -> None:
        """
        Déplace chaque joueur vivant dans son salon vocal privé.
        Les loups-garous sont déplacés dans la tanière à la place.
        """
        mapping: dict[discord.Member, Optional[discord.VoiceChannel]] = {}

        for player in self.game.alive_players:
            if player.member.voice is None:
                continue
            if player.role and player.role.team == "loups":
                mapping[player.member] = self.game.wolves_voice
            elif player.private_voice:
                mapping[player.member] = player.private_voice

        if mapping:
            await self.move_queue.move_each(mapping)

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    async def _get_or_create_category(
        self,
        name: str,
        overwrites: dict,
    ) -> discord.CategoryChannel:
        existing = discord.utils.get(self.guild.categories, name=name)
        if existing:
            return existing
        return await self.guild.create_category(name, overwrites=overwrites)

    async def _get_or_create_text(
        self,
        name: str,
        category: discord.CategoryChannel,
        overwrites: dict,
    ) -> discord.TextChannel:
        existing = discord.utils.get(category.text_channels, name=name)
        if existing:
            return existing
        return await self.guild.create_text_channel(name, category=category, overwrites=overwrites)

    async def _get_or_create_voice(
        self,
        name: str,
        category: discord.CategoryChannel,
        overwrites: dict,
    ) -> discord.VoiceChannel:
        existing = discord.utils.get(category.voice_channels, name=name)
        if existing:
            return existing
        return await self.guild.create_voice_channel(name, category=category, overwrites=overwrites)

    @staticmethod
    def _safe_channel_name(name: str) -> str:
        """Transforme un pseudo en nom de salon Discord valide (alphanumérique + tirets)."""
        import re
        safe = re.sub(r"[^\w\-]", "-", name.lower().strip())
        safe = re.sub(r"-{2,}", "-", safe).strip("-")
        return safe[:32] or "joueur"
