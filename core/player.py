"""
core/player.py — Dataclass représentant un joueur dans une partie.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import discord

if TYPE_CHECKING:
    from roles.base_role import BaseRole


@dataclass
class Player:
    """Représente un joueur dans une partie de Loup-Garou."""

    member: discord.Member
    """Le membre Discord associé."""

    role: Optional["BaseRole"] = None
    """Le rôle de jeu attribué (ex: Witch, Werewolf…)."""

    is_alive: bool = True
    """False si le joueur est mort (bûcher, loup, sorcière…)."""

    is_charmed: bool = False
    """True si le joueur est envoûté par le Joueur de Flûte."""

    lover_id: Optional[int] = None
    """ID Discord de l'amoureux (lien Cupidon), None si aucun."""

    protected_tonight: bool = False
    """True si le Salvateur l'a protégé cette nuit."""

    # Canaux Discord privés
    private_text:  Optional[discord.TextChannel]  = field(default=None, repr=False)
    private_voice: Optional[discord.VoiceChannel] = field(default=None, repr=False)

    # Événement asyncio pour synchroniser les actions nocturnes
    action_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    @property
    def id(self) -> int:
        return self.member.id

    @property
    def display_name(self) -> str:
        return self.member.display_name

    @property
    def mention(self) -> str:
        return self.member.mention

    @property
    def lover(self) -> Optional[int]:
        return self.lover_id

    def kill(self) -> None:
        """Marque le joueur comme mort."""
        self.is_alive = False

    def to_dict(self) -> dict:
        """Sérialise l'état du joueur pour la persistance SQLite."""
        return {
            "member_id":          self.member.id,
            "role":               self.role.name if self.role else None,
            "is_alive":           self.is_alive,
            "is_charmed":         self.is_charmed,
            "lover_id":           self.lover_id,
            "protected_tonight":  self.protected_tonight,
        }

    def __hash__(self) -> int:
        return hash(self.member.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Player):
            return self.member.id == other.member.id
        return False
