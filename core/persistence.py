"""
core/persistence.py — Sauvegarde et restauration de l'état du jeu via SQLite (aiosqlite).
Permet de reprendre une partie après un crash/redémarrage du bot.
"""

from __future__ import annotations

import json
import logging
from typing import Optional, TYPE_CHECKING

import aiosqlite

import config as C

if TYPE_CHECKING:
    from core.game import Game

log = logging.getLogger(__name__)


class Persistence:
    """Interface de persistance SQLite asynchrone."""

    def __init__(self, db_path: str = C.DB_PATH):
        self.db_path = db_path

    async def init_db(self) -> None:
        """Crée les tables si elles n'existent pas encore."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_state (
                    guild_id    INTEGER PRIMARY KEY,
                    phase       TEXT    NOT NULL,
                    night_count INTEGER NOT NULL DEFAULT 0,
                    config_json TEXT    NOT NULL DEFAULT '{}',
                    players_json TEXT   NOT NULL DEFAULT '[]',
                    night_state_json TEXT NOT NULL DEFAULT '{}',
                    channel_map_json TEXT NOT NULL DEFAULT '{}'
                )
            """)
            await db.commit()
        log.info("Base de données SQLite initialisée : %s", self.db_path)

    async def save(self, game: "Game") -> None:
        """Sérialise et sauvegarde l'état complet du jeu."""
        from core.state_machine import NightState

        players_data = [p.to_dict() for p in game.players.values()]
        night_state_data = {
            "wolf_victim":    game.night_state.wolf_victim.id
                              if game.night_state.wolf_victim else None,
            "witch_saved":    game.night_state.witch_saved,
            "witch_victim":   game.night_state.witch_victim.id
                              if game.night_state.witch_victim else None,
            "protected":      game.night_state.protected.id
                              if game.night_state.protected else None,
            "deaths_tonight": [p.id for p in game.night_state.deaths_tonight],
            "current_role_name": game.night_state.current_role_name,
        }
        channel_map_data = {}
        for player_id, player in game.players.items():
            channel_map_data[str(player_id)] = {
                "text":  player.private_text.id  if player.private_text  else None,
                "voice": player.private_voice.id if player.private_voice else None,
            }

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO game_state
                    (guild_id, phase, night_count, config_json, players_json,
                     night_state_json, channel_map_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    phase            = excluded.phase,
                    night_count      = excluded.night_count,
                    config_json      = excluded.config_json,
                    players_json     = excluded.players_json,
                    night_state_json = excluded.night_state_json,
                    channel_map_json = excluded.channel_map_json
            """, (
                game.guild.id,
                game.phase.value,
                game.night_count,
                json.dumps(game.game_config.to_dict()),
                json.dumps(players_data),
                json.dumps(night_state_data),
                json.dumps(channel_map_data),
            ))
            await db.commit()
        log.debug("État sauvegardé pour guild %d (phase: %s)", game.guild.id, game.phase.value)

    async def load(self, guild_id: int) -> Optional[dict]:
        """
        Charge l'état sauvegardé pour un guild.
        Retourne None s'il n'y a pas de partie en cours.
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT phase, night_count, config_json, players_json, "
                "night_state_json, channel_map_json FROM game_state WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        return {
            "phase":       row[0],
            "night_count": row[1],
            "config":      json.loads(row[2]),
            "players":     json.loads(row[3]),
            "night_state": json.loads(row[4]),
            "channel_map": json.loads(row[5]),
        }

    async def delete(self, guild_id: int) -> None:
        """Supprime l'état sauvegardé (fin de partie)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM game_state WHERE guild_id = ?", (guild_id,))
            await db.commit()
        log.info("État supprimé pour guild %d", guild_id)
