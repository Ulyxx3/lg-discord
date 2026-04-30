"""
utils/embed_builder.py — Constructeur centralisé d'embeds Discord.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import discord

import config as C

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player


def build_status_embed(game: "Game") -> discord.Embed:
    """Embed de statut de la partie en cours."""
    alive = game.alive_players
    dead  = game.dead_players

    embed = discord.Embed(
        title="📊 Statut de la partie",
        color=C.COLOR_INFO,
    )
    embed.add_field(
        name=f"👥 Joueurs vivants ({len(alive)})",
        value="\n".join(f"• {p.display_name}" for p in alive) or "*aucun*",
        inline=True,
    )
    embed.add_field(
        name=f"💀 Morts ({len(dead)})",
        value="\n".join(
            f"• {p.display_name} ({p.role.name if p.role else '???'})"
            for p in dead
        ) or "*aucun*",
        inline=True,
    )
    embed.add_field(
        name="🌙 Nuit",
        value=str(game.night_count),
        inline=True,
    )
    embed.add_field(
        name="⚙️ Phase",
        value=game.phase.value,
        inline=True,
    )
    return embed


def build_player_list_embed(players: list["Player"], title: str = "Joueurs") -> discord.Embed:
    embed = discord.Embed(title=title, color=C.COLOR_INFO)
    lines = [f"{i+1}. **{p.display_name}**" for i, p in enumerate(players)]
    embed.description = "\n".join(lines) or "*aucun joueur*"
    return embed


def build_role_reveal_embed(player: "Player") -> discord.Embed:
    """Révèle le rôle d'un joueur mort (pour le village)."""
    role  = player.role
    color = C.COLOR_WOLVES if (role and role.team == "loups") else C.COLOR_DAY
    embed = discord.Embed(
        title=f"💀 {player.display_name} est mort·e",
        description=(
            f"Son rôle était : **{role.name if role else '???'}** {role.emoji if role else ''}\n"
            f"Équipe : *{role.team if role else '???'}*"
        ),
        color=color,
    )
    return embed


def build_config_embed(game: "Game") -> discord.Embed:
    """Affiche la configuration actuelle de la partie."""
    cfg   = game.game_config
    deck  = cfg.deck
    total = cfg.total_cards()

    lines = [f"• **{name}** ×{count}" for name, count in deck.items() if count > 0]
    embed = discord.Embed(
        title="⚙️ Configuration de la partie",
        color=C.COLOR_CONFIG,
    )
    embed.add_field(
        name=f"🃏 Deck ({total} cartes)",
        value="\n".join(lines) or "*vide*",
        inline=False,
    )
    embed.add_field(
        name="⏱️ Timers",
        value=(
            f"Débat : {cfg.debate_duration}s\n"
            f"Tour nocturne : {cfg.night_role_timeout}s\n"
            f"Vote loups : {cfg.wolves_timeout}s\n"
            f"Vote bûcher : {cfg.vote_timeout}s"
        ),
        inline=True,
    )
    embed.add_field(
        name="📦 Extensions",
        value="\n".join(f"• {e}" for e in cfg.enabled_extensions) or "*aucune*",
        inline=True,
    )
    return embed
