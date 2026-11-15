"""Busca de vídeos e fotos de banco no Pexels."""

import os
from pathlib import Path

import requests

API = "https://api.pexels.com"


class Pexels:
    def __init__(self, formato: str):
        self.chave = os.environ.get("PEXELS_API_KEY", "").strip()
        self.orientacao = "portrait" if formato == "vertical" else "landscape"
        self.usados: set[int] = set()

    def _get(self, caminho: str, busca: str) -> dict:
        r = requests.get(
            API + caminho,
            headers={"Authorization": self.chave},
            params={"query": busca, "orientation": self.orientacao, "per_page": 10},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def _baixar(self, url: str, destino: Path) -> Path:
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with destino.open("wb") as arquivo:
                for bloco in r.iter_content(1 << 20):
                    arquivo.write(bloco)
        return destino

    def buscar(self, busca: str, destino_sem_extensao: Path, lado_menor: int = 1080) -> Path | None:
        """Baixa um vídeo (ou, na falta, uma foto) para a busca. None se nada servir."""
        if not self.chave:
            return None
        try:
            for video in self._get("/videos/search", busca).get("videos", []):
                if video["id"] in self.usados:
                    continue
                arquivos = [a for a in video["video_files"] if a.get("file_type") == "video/mp4" and a.get("width")]
                if not arquivos:
                    continue
                # O menor arquivo que ainda cobre a resolução do vídeo; senão, o maior disponível.
                tamanho = lambda a: min(a["width"], a["height"])
                bons = [a for a in arquivos if tamanho(a) >= lado_menor]
                escolhido = min(bons, key=tamanho) if bons else max(arquivos, key=tamanho)
                self.usados.add(video["id"])
                return self._baixar(escolhido["link"], destino_sem_extensao.with_suffix(".mp4"))
            for foto in self._get("/v1/search", busca).get("photos", []):
                if foto["id"] in self.usados:
                    continue
                self.usados.add(foto["id"])
                return self._baixar(foto["src"]["large2x"], destino_sem_extensao.with_suffix(".jpg"))
        except requests.RequestException as erro:
            print(f"    aviso: Pexels falhou para '{busca}': {erro}")
        return None
