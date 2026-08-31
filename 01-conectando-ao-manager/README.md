# Módulo 1 — Conectando ao Manager (45 min)

## O que você já sabe

Você loga na GUI do Manager todo dia. O que você talvez não tenha visto é que
aquele login é uma **sessão Java EE**, não uma API REST moderna. Isso explica
tudo que vem a seguir.

## O que vamos aprender

| Automação | SD-WAN |
|---|---|
| Sessões HTTP e cookie jar | `j_security_check` e `JSESSIONID` |
| Proteção CSRF | `X-XSRF-TOKEN` (obrigatório desde 19.2) |
| Segredo fora do código | Vault |
| Falhar alto, cedo e com contexto | A armadilha do HTTP 200 |

## O handshake

```
1.  POST /j_security_check              →  cookie JSESSIONID
    corpo: j_username=…&j_password=…       (form-encoded, não JSON)

2.  GET  /dataservice/client/token      →  o valor do X-XSRF-TOKEN
                                            (texto puro, sem envelope)
```

> [!WARNING]
> **A armadilha que pega todo mundo.** Senha errada não devolve `401`.
> Devolve **`200 OK` com o HTML da tela de login**. Se o seu código não
> testa isso, você vai debugar um `KeyError: 'data'` por uma hora quando a
> resposta correta era "sua senha está errada".

## Mãos à obra

```bash
export VAULT_TOKEN=hvs.xxxx
python exercicio.py
```

Quatro TODOs em `autenticar()`, um em `listar_dispositivos()`, um em `main()`.

## Prova de que rodou de verdade

O instrutor vai perguntar: **quantos WAN Edges estão `reachable` agora?**

Essa resposta não está em lugar nenhum do repositório. Só o fabric sabe.

## Se travar

- `CredentialsError` → o `VAULT_TOKEN` não está exportado, ou expirou.
- `SSLError` → falta `session.verify = False` (lab tem certificado self-signed).
- `KeyError: 'data'` → você caiu na armadilha do HTTP 200. Volte ao TODO 1.2.
- `403` num POST → faltou o `X-XSRF-TOKEN`. Volte ao TODO 1.4.

## Depois

Abra `sdwan_toolkit/client.py`. É o mesmo handshake que você acabou de
escrever, mais rate limit, tratamento de erro e o desembrulho do `data`.
A partir do módulo 2 você usa ele — mas agora sabendo o que tem dentro.
