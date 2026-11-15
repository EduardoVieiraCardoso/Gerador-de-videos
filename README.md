# Gerador de vídeos

Gera um vídeo narrado a partir de um tema, com um comando:

1. **Roteiro** — o Claude escreve o roteiro dividido em cenas.
2. **Voz** — narração em português com as vozes neurais do Edge TTS (grátis, sem chave).
3. **Imagens** — um vídeo (ou foto) de banco do Pexels para cada cena.
4. **Montagem** — o ffmpeg junta tudo com legendas sincronizadas e gera o MP4.

## Instalação

Requer Python 3.10+ e o [ffmpeg](https://ffmpeg.org/download.html) instalado.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # e preencha as chaves
```

Chaves no `.env`:

- `ANTHROPIC_API_KEY` — para o roteiro ([criar chave](https://platform.claude.com/settings/keys)).
- `PEXELS_API_KEY` — gratuita, para os vídeos de banco ([criar chave](https://www.pexels.com/api/)).
  Sem ela o vídeo sai com fundos em gradiente.

## Uso

```bash
# Vídeo vertical de 60 s (Reels, TikTok, Shorts)
python -m gerador "Três curiosidades sobre o café"

# Vídeo horizontal de 3 minutos (YouTube), com voz masculina
python -m gerador "Como funciona um buraco negro" --formato horizontal --duracao 180 --voz pt-BR-AntonioNeural
```

O resultado fica em `saida/<titulo>/`: `video.mp4`, `roteiro.json` e os arquivos de cada cena.

### Revisar o roteiro antes de renderizar

```bash
python -m gerador "Tema" --so-roteiro                      # gera só o roteiro.json
# edite saida/<titulo>/roteiro.json (texto da narração e busca de imagem de cada cena)
python -m gerador --roteiro saida/<titulo>/roteiro.json    # renderiza a partir dele
```

### Vídeos da empresa

O arquivo `marca.md` descreve a empresa (o que faz, diferenciais, público, tom e chamada
para ação). Se ele existir, todo roteiro é escrito na voz da empresa e só com os fatos
que estão ali. Edite-o à vontade; use `--sem-marca` para um vídeo genérico.

```bash
python -m gerador "O que é superfície de ataque externa e por que monitorar"
```

### Opções

| Opção | Padrão | O que faz |
|---|---|---|
| `--formato` | `vertical` | `vertical` (1080×1920) ou `horizontal` (1920×1080) |
| `--duracao` | `60` | Duração alvo, em segundos |
| `--voz` | `pt-BR-FranciscaNeural` | Voz do Edge TTS (`edge-tts --list-voices` mostra todas) |
| `--velocidade` | `+0%` | Velocidade da fala, por exemplo `+10%` |
| `--roteiro` | — | Usa um `roteiro.json` pronto em vez de gerar outro |
| `--so-roteiro` | — | Gera só o roteiro |
| `--marca` | `marca.md` | Arquivo com a descrição da empresa |
| `--sem-marca` | — | Ignora o arquivo de marca |
| `--modelo` | `claude-opus-5-5` | Modelo do Claude usado no roteiro |
