"""Le noyau : les décisions.

Ce paquet ne parle à personne. Aucun import de httpx, requests, aiohttp,
subprocess, socket ni asyncio n'y est autorisé, et aucun fichier n'y est
ouvert — c'est un interdit contrôlé par /verify (AGENTS.md §2).

La raison est dans ARCHITECTURE.md §1.1 : une radio est une machine à décider
dans le temps, et une émission qu'on ne peut pas rejouer ne peut pas être
testée.
"""
