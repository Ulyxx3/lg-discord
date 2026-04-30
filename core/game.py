"""
core/game.py — Classe Game : chef d'orchestre central.
Point d'accès global à l'état d'une partie en cours.
"""

from __future__ import annotations

import logging
import random
from typing import Optional

import discord

from core.game_config import GameConfig
from core.player import Player
from core.state_machine import GamePhase, NightState
from core.persistence import Persistence

log = logging.getLogger(__name__)


class Game:
    """
    Représente une partie de Loup-Garou en cours sur un serveur Discord.
    Une seule instance par guild (serveur).
    """

    def __init__(self, guild: discord.Guild, bot: discord.Client):
        self.guild     = guild
        self.bot       = bot
        self.phase     = GamePhase.IDLE
        self.game_config = GameConfig()
        self.players: dict[int, Player] = {}  # member_id → Player
        self.night_state  = NightState()
        self.night_count  = 0
        self.persistence  = Persistence()

        # Références aux salons structurels (créés par /lg setup)
        self.village_text:  Optional[discord.TextChannel]  = None
        self.village_voice: Optional[discord.VoiceChannel] = None
        self.wolves_text:   Optional[discord.TextChannel]  = None
        self.wolves_voice:  Optional[discord.VoiceChannel] = None
        self.lobby_text:    Optional[discord.TextChannel]  = None
        self.logs_channel:  Optional[discord.TextChannel]  = None

        # Rôles Discord créés dynamiquement
        self.role_player:    Optional[discord.Role] = None
        self.role_wolf:      Optional[discord.Role] = None
        self.role_dead:      Optional[discord.Role] = None
        self.role_spectator: Optional[discord.Role] = None

    # ── Accès aux joueurs ───────────────────────────────────────────────────

    def get_player(self, member: discord.Member) -> Optional[Player]:
        return self.players.get(member.id)

    def get_player_by_id(self, member_id: int) -> Optional[Player]:
        return self.players.get(member_id)

    def add_player(self, member: discord.Member) -> Player:
        player = Player(member=member)
        self.players[member.id] = player
        return player

    def remove_player(self, member_id: int) -> None:
        self.players.pop(member_id, None)

    @property
    def alive_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_alive]

    @property
    def dead_players(self) -> list[Player]:
        return [p for p in self.players.values() if not p.is_alive]

    @property
    def werewolves(self) -> list[Player]:
        return [
            p for p in self.alive_players
            if p.role and p.role.team == "loups"
        ]

    @property
    def player_count(self) -> int:
        return len(self.players)

    # ── Distribution des rôles ──────────────────────────────────────────────

    def distribute_roles(self) -> list[Player]:
        """
        Pioche les rôles depuis le deck de la config et les distribue aléatoirement.
        Pour le Voleur : met 2 cartes de côté sans les attribuer.
        Retourne la liste des joueurs avec leurs rôles.
        """
        from roles.registry import ROLE_REGISTRY

        # Construction du pool de cartes
        card_pool: list[str] = []
        for role_name, count in self.game_config.deck.items():
            # Les Deux Sœurs = 2 instances du rôle, Les Trois Frères = 3
            if role_name == "Les Deux Sœurs":
                card_pool.extend(["Les Deux Sœurs"] * (2 * count))
            elif role_name == "Les Trois Frères":
                card_pool.extend(["Les Trois Frères"] * (3 * count))
            else:
                card_pool.extend([role_name] * count)

        random.shuffle(card_pool)

        player_list = list(self.players.values())
        random.shuffle(player_list)

        # Cartes réservées pour le Voleur (2 cartes non attribuées)
        thief_cards: list[str] = []
        thief_in_deck = self.game_config.deck.get("Voleur", 0) > 0
        if thief_in_deck and len(card_pool) > len(player_list):
            thief_cards = card_pool[len(player_list):]
            card_pool   = card_pool[:len(player_list)]

        for player, role_name in zip(player_list, card_pool):
            role_cls = ROLE_REGISTRY.get(role_name)
            if role_cls is None:
                log.warning("Rôle inconnu dans le registre : %s", role_name)
                from roles.villager import Villager
                role_cls = Villager
            player.role = role_cls()

        # Communiquer les cartes réservées au Voleur si présent
        for player in player_list:
            if player.role and player.role.name == "Voleur":
                player.role.reserve_cards = thief_cards  # type: ignore[attr-defined]

        log.info("Rôles distribués : %s", {p.display_name: p.role.name for p in player_list})
        return player_list

    # ── Vérification de fin de partie ──────────────────────────────────────

    def check_victory(self) -> Optional[str]:
        """
        Vérifie si une condition de victoire est atteinte.
        Retourne le nom de l'équipe gagnante ou None.
        """
        alive = self.alive_players
        wolves  = [p for p in alive if p.role and p.role.team == "loups"]
        village = [p for p in alive if p.role and p.role.team == "village"]
        neutral = [p for p in alive if p.role and p.role.team == "neutre"]

        # Victoire des loups : ils sont majoritaires (≥ village)
        if len(wolves) >= len(village) and len(wolves) > 0:
            return "loups"

        # Victoire du Joueur de Flûte : tous les vivants sont envoûtés
        piper_alive = any(p.role and p.role.name == "Joueur de Flûte" for p in alive)
        if piper_alive and all(p.is_charmed for p in alive
                               if p.role and p.role.name != "Joueur de Flûte"):
            return "joueur_de_flute"

        # Victoire du village : plus aucun loup
        if len(wolves) == 0:
            # Vérifie l'Ange (victoire solo si éliminé 1ère nuit/1er jour)
            return "village"

        return None

    # ── Mort d'un joueur ───────────────────────────────────────────────────

    async def kill_player(self, player: Player, reason: str = "") -> None:
        """
        Tue un joueur, gère les effets en chaîne (lien amoureux, Chasseur…).
        """
        if not player.is_alive:
            return

        player.kill()
        log.info("Joueur mort : %s (raison: %s)", player.display_name, reason or "non précisée")

        # Retirer le rôle Discord "Joueur" et ajouter "Mort"
        try:
            if self.role_player and self.role_player in player.member.roles:
                await player.member.remove_roles(self.role_player)
            if self.role_dead:
                await player.member.add_roles(self.role_dead)
        except discord.HTTPException as e:
            log.warning("Impossible de modifier les rôles Discord de %s : %s", player.display_name, e)

        # Lien amoureux (Cupidon) : l'amoureux suit dans la mort
        if player.lover_id:
            lover = self.get_player_by_id(player.lover_id)
            if lover and lover.is_alive:
                log.info("Mort par amour : %s suit %s", lover.display_name, player.display_name)
                await self.kill_player(lover, reason="mort_par_amour")

        await self.persistence.save(self)

    # ── Persistance ────────────────────────────────────────────────────────

    async def save(self) -> None:
        await self.persistence.save(self)

    async def log(self, message: str) -> None:
        """Envoie un message dans le salon de logs admin."""
        if self.logs_channel:
            try:
                await self.logs_channel.send(f"📋 {message}")
            except discord.HTTPException:
                pass
        log.info("[GAME LOG] %s", message)


# ── Registre global des parties (une par guild) ─────────────────────────────
_games: dict[int, Game] = {}


def get_game(guild: discord.Guild, bot: discord.Client) -> Game:
    """Retourne (ou crée) l'instance Game pour ce serveur."""
    if guild.id not in _games:
        _games[guild.id] = Game(guild, bot)
    return _games[guild.id]


def get_game_by_id(guild_id: int) -> Optional[Game]:
    return _games.get(guild_id)
