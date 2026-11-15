"""Narração com Edge TTS (vozes neurais gratuitas da Microsoft)."""

import asyncio
import subprocess
from pathlib import Path

import edge_tts

VOZ_PADRAO = "pt-BR-FranciscaNeural"  # outras: pt-BR-AntonioNeural, pt-BR-ThalitaMultilingualNeural

Palavra = tuple[float, float, str]  # início (s), fim (s), texto


async def _sintetizar(texto: str, voz: str, velocidade: str, destino: Path) -> list[Palavra]:
    fala = edge_tts.Communicate(texto, voz, rate=velocidade, boundary="WordBoundary")
    palavras: list[Palavra] = []
    with destino.open("wb") as arquivo:
        async for parte in fala.stream():
            if parte["type"] == "audio":
                arquivo.write(parte["data"])
            elif parte["type"] == "WordBoundary":
                inicio = parte["offset"] / 1e7  # unidades de 100 ns
                palavras.append((inicio, inicio + parte["duration"] / 1e7, parte["text"]))
    return palavras


def narrar(texto: str, destino: Path, voz: str = VOZ_PADRAO, velocidade: str = "+0%") -> list[Palavra]:
    """Grava o MP3 da narração e devolve o tempo de cada palavra."""
    return asyncio.run(_sintetizar(texto, voz, velocidade, destino))


def duracao(arquivo: Path) -> float:
    saida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arquivo)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(saida.strip())
