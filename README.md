# jbr-reels

Gerador do Reels das notícias-bomba do Jornal Belford Roxo (jornalbelfordroxo.com.br).
O robô do jornal dispara o workflow `reels` com a notícia; o vídeo (1080x1920, ~40 s, narração em voz sintética) sai como release `reels-<Nº>`.

Fontes: Anton e Montserrat (SIL Open Font License).

## Arte do post (workflow `arte`)

Desde 21/10/2026 a arte do post sai daqui, não mais do Google Slides:
- Modelo **B** (claro, cara de jornal) nas notícias normais.
- Modelo **A** (manchete escura) na bomba.

Como funciona:
- O robô dispara `repository_dispatch` tipo `arte` com `{n, modelo, foto, titulo (*destaque*), editoria, data}`.
- O `arte.py` abre `arte/arte.html` no Chrome do runner e sobe `arte-<Nº>-<modelo>.jpg` no release `artes`. Leva uns 15 s.
- Se a arte não ficar pronta em ~2 min, o robô usa o modelo antigo do Slides.
- Se a notícia vira bomba (N 3) e a arte estava no B, o robô pede a A e espera até 8 min antes de postar.
