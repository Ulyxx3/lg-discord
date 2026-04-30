"""
bot.py — Point d'entrée du bot Loup-Garou de Thiercelieux.
Initialisation, chargement des cogs, sync des slash commands.
"""

from __future__ import annotations

import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.persistence import Persistence

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bot")

# ─── Configuration ────────────────────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError(
        "DISCORD_TOKEN manquant. Copiez .env.example en .env et ajoutez votre token."
    )

# ─── Intents ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members      = True   # Nécessaire pour gérer les rôles et déplacements
intents.voice_states = True   # Nécessaire pour move_to()
intents.message_content = True

# ─── Bot ──────────────────────────────────────────────────────────────────────
class LGBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",   # Préfixe de secours (non utilisé en prod)
            intents=intents,
            help_command=None,
        )
        self.persistence = Persistence()

    async def setup_hook(self) -> None:
        """Appelé avant le login — charge les cogs et synce les slash commands."""
        # Initialise la base de données SQLite
        await self.persistence.init_db()

        # Charge les cogs
        cogs = [
            "commands.lg_commands",
        ]
        for cog_path in cogs:
            try:
                await self.load_extension(cog_path)
                log.info("Cog chargé : %s", cog_path)
            except Exception as e:
                log.error("Erreur chargement cog %s : %s", cog_path, e, exc_info=True)

        # Sync des slash commands globalement
        # En développement, remplacer par sync(guild=discord.Object(id=GUILD_ID))
        # pour une synchronisation instantanée.
        synced = await self.tree.sync()
        log.info("Slash commands synchronisées : %d commande(s)", len(synced))

    async def on_ready(self) -> None:
        log.info("Bot connecté : %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="🐺 Loup-Garou de Thiercelieux",
            )
        )

        # Tentative de reprise des parties en cours après un crash
        await self._resume_active_games()

    async def _resume_active_games(self) -> None:
        """
        Tente de reprendre les parties sauvegardées dans SQLite.
        Pour chaque guild où une partie était en cours, restaure l'état.
        """
        import aiosqlite
        import config as C

        try:
            async with aiosqlite.connect(C.DB_PATH) as db:
                async with db.execute(
                    "SELECT guild_id, phase FROM game_state"
                ) as cursor:
                    rows = await cursor.fetchall()
        except Exception:
            return  # DB peut ne pas encore exister

        for guild_id, phase in rows:
            guild = self.get_guild(guild_id)
            if not guild:
                continue
            log.info(
                "Tentative de reprise de la partie sur %s (phase: %s)",
                guild.name, phase
            )
            # La reprise complète nécessite une reconstruction du Game depuis la DB
            # C'est une opération complexe — ici on notifie simplement le channel de logs
            from core.game import get_game
            game = get_game(guild, self)
            saved = await game.persistence.load(guild_id)
            if saved:
                if game.logs_channel:
                    await game.logs_channel.send(
                        "⚠️ Le bot a redémarré. Une partie était en cours. "
                        "Utilisez `/lg status` pour vérifier l'état."
                    )

    async def on_member_remove(self, member: discord.Member) -> None:
        """Si un joueur quitte le serveur pendant une partie, il est marqué mort."""
        from core.game import get_game_by_id
        from core.state_machine import GamePhase

        game = get_game_by_id(member.guild.id)
        if not game or game.phase == GamePhase.IDLE:
            return

        player = game.get_player(member)
        if player and player.is_alive:
            log.info("%s a quitté le serveur — mort automatique", member.display_name)
            await game.kill_player(player, reason="quitte_serveur")
            if game.village_text:
                await game.village_text.send(
                    f"💨 **{member.display_name}** a quitté le serveur…"
                )

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ) -> None:
        """Gestionnaire global des erreurs de slash commands."""
        if isinstance(error, discord.app_commands.MissingPermissions):
            msg = "❌ Vous n'avez pas les permissions nécessaires."
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            msg = f"⏳ Commande en cooldown. Réessayez dans {error.retry_after:.1f}s."
        else:
            log.error("Erreur slash command : %s", error, exc_info=True)
            msg = f"❌ Une erreur s'est produite : `{error}`"

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass


# ─── Lancement ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot = LGBot()
    asyncio.run(bot.start(TOKEN))
