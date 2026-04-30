"""
config.py — Constantes globales du bot Loup-Garou.
Toutes les valeurs configurables sont ici pour éviter les "magic numbers".
"""

from __future__ import annotations

# ─── Timers (en secondes) ──────────────────────────────────────────────────────
PHASE_TIMEOUT_NIGHT_ROLE    = 90    # Temps max pour un rôle spécial la nuit
PHASE_TIMEOUT_WOLVES        = 120   # Temps max pour le vote des loups
PHASE_TIMEOUT_DAY_DEBATE    = 300   # Durée du débat de jour (5 min)
PHASE_TIMEOUT_DAY_VOTE      = 120   # Temps max pour le vote du bûcher
PHASE_COUNTDOWN_INTERVAL    = 30    # Rappel de temps restant toutes les X secondes

# ─── Rate-limit mitigation ────────────────────────────────────────────────────
MOVE_DELAY_SECONDS = 0.6            # Délai entre chaque déplacement vocal
MAX_PLAYERS        = 25             # Limite absolue de joueurs

# ─── Limites de joueurs ───────────────────────────────────────────────────────
MIN_PLAYERS = 6

# ─── Couleurs des embeds Discord ─────────────────────────────────────────────
COLOR_NIGHT      = 0x1a1a2e   # Bleu nuit profond
COLOR_DAY        = 0xf5c518   # Jaune soleil
COLOR_WOLVES     = 0x8b0000   # Rouge sang
COLOR_SEER       = 0x9b59b6   # Violet voyante
COLOR_WITCH      = 0x2ecc71   # Vert sorcière
COLOR_DEATH      = 0x2c2c2c   # Gris mort
COLOR_VICTORY    = 0xffd700   # Or victoire
COLOR_INFO       = 0x3498db   # Bleu info
COLOR_ERROR      = 0xe74c3c   # Rouge erreur
COLOR_CONFIG     = 0x1abc9c   # Turquoise configuration

# ─── Emojis ───────────────────────────────────────────────────────────────────
EMOJI_MOON       = "🌙"
EMOJI_SUN        = "☀️"
EMOJI_WOLF       = "🐺"
EMOJI_VILLAGER   = "👨‍🌾"
EMOJI_SKULL      = "💀"
EMOJI_HEART      = "❤️"
EMOJI_STAR       = "⭐"
EMOJI_HOURGLASS  = "⏳"
EMOJI_LOCK       = "🔒"
EMOJI_FIRE       = "🔥"
EMOJI_POTION     = "🧪"
EMOJI_EYE        = "👁️"
EMOJI_ARROW      = "🏹"
EMOJI_MUSIC      = "🎵"
EMOJI_SHIELD     = "🛡️"
EMOJI_FEATHER    = "🪶"
EMOJI_BEAR       = "🐻"
EMOJI_FOX        = "🦊"
EMOJI_CROWN      = "👑"
EMOJI_FLUTE      = "🪗"
EMOJI_VOTE       = "🗳️"
EMOJI_CHECK      = "✅"
EMOJI_CROSS      = "❌"

# ─── Noms des catégories/salons créés par /lg setup ──────────────────────────
CATEGORY_VILLAGE   = "🏡 Le Village"
CATEGORY_WOLVES    = "🐺 Tanière des Loups"
CATEGORY_HOUSES    = "🏠 Maisons"
CATEGORY_ADMIN     = "📋 Administration MDJ"

CHANNEL_VILLAGE_TEXT  = "village-débat"
CHANNEL_VILLAGE_VOICE = "🔊・Le Village"
CHANNEL_WOLVES_TEXT   = "loups-garous"
CHANNEL_WOLVES_VOICE  = "🔊・Tanière"
CHANNEL_LOBBY         = "salle-dattente"
CHANNEL_LOGS          = "logs-mdj"

# ─── Noms des rôles Discord créés par le bot ─────────────────────────────────
DISCORD_ROLE_PLAYER    = "🐾 Joueur LG"
DISCORD_ROLE_WOLF      = "🐺 Loup-Garou"
DISCORD_ROLE_DEAD      = "💀 Mort"
DISCORD_ROLE_SPECTATOR = "👁 Spectateur"

# ─── Extensions disponibles ───────────────────────────────────────────────────
EXTENSIONS = {
    "base":          "Jeu de Base",
    "nouvelle_lune": "Nouvelle Lune",
    "village":       "Le Village",
    "personnages":   "Les Personnages",
}

# ─── Fichier de persistance SQLite ────────────────────────────────────────────
DB_PATH = "lg_state.db"
