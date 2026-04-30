"""
utils/move_queue.py — File d'attente pour les déplacements vocaux de masse.
Évite les rate limits Discord lors du déplacement de 25 joueurs simultanément.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord

import config as C

log = logging.getLogger(__name__)


class MoveQueue:
    """
    File d'attente FIFO pour les déplacements vocaux.
    Traite les déplacements séquentiellement avec un délai entre chaque
    pour respecter les rate limits de l'API Discord.
    """

    def __init__(self, delay: float = C.MOVE_DELAY_SECONDS):
        self._delay = delay
        self._queue: asyncio.Queue[tuple[discord.Member, Optional[discord.VoiceChannel]]] = \
            asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._done_event = asyncio.Event()

    async def _worker(self) -> None:
        """Consomme la file d'attente un déplacement à la fois."""
        while not self._queue.empty():
            member, channel = await self._queue.get()
            try:
                if channel is None:
                    # Déconnecte du salon vocal
                    await member.move_to(None)
                else:
                    await member.move_to(channel)
                log.debug("Déplacé %s → %s", member.display_name,
                          channel.name if channel else "déconnecté")
            except discord.HTTPException as e:
                log.warning("Impossible de déplacer %s : %s", member.display_name, e)
            finally:
                self._queue.task_done()
                if not self._queue.empty():
                    await asyncio.sleep(self._delay)
        self._done_event.set()

    async def move(
        self,
        members: list[discord.Member],
        channel: Optional[discord.VoiceChannel],
    ) -> None:
        """
        Enfile les déplacements et attend leur complétion.

        :param members: Liste des membres à déplacer.
        :param channel: Salon de destination (None = déconnecter).
        """
        self._done_event.clear()

        for member in members:
            await self._queue.put((member, channel))

        # Démarre (ou relance) le worker
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker())

        # Attend que tous les déplacements soient traités
        await self._done_event.wait()

    async def move_each(
        self,
        mapping: dict[discord.Member, Optional[discord.VoiceChannel]],
    ) -> None:
        """
        Déplace chaque membre vers son propre salon (mapping individuel).
        Utilisé la nuit pour envoyer chacun dans sa maison privée.
        """
        self._done_event.clear()

        for member, channel in mapping.items():
            await self._queue.put((member, channel))

        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker())

        await self._done_event.wait()
