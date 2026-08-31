# Módulo 3 — Config Groups e o modelo assíncrono (50 min)

Aqui você escreve no fabric pela primeira vez.

## O mapa mental, vindo de templates

| Você conhece | Agora se chama |
|---|---|
| Feature template | **Parcel** (dentro de um feature profile) |
| Device template | **Config group** |
| Attach | **Associate** + **deploy** |
| CSV de variáveis | **Device variables** |

Config groups exigem Manager 20.12+ / IOS-XE 17.12+. Templates clássicos
continuam existindo e continuam sendo a realidade da maioria dos fabrics
brownfield — o `attachfeature` é o equivalente do deploy, e o modelo de tarefa
assíncrona é **idêntico** nos dois. O que você aprende aqui vale para os dois
mundos.

## O que vamos aprender

| Automação | SD-WAN |
|---|---|
| Dry-run antes de escrever | `preview` do config group |
| Modelo assíncrono e polling | `parentTaskId` → `/device/action/status/{id}` |
| Idempotência | Associate que não reassocia |
| GET → modificar → PUT | Device variables |

## A lição que importa

Escrever no Manager **não é síncrono**. O POST devolve um `id` e vai embora:

```
POST /v1/config-group/{id}/device/deploy   →  {"parentTaskId": "abc-123"}
                                                       │
GET /device/action/status/abc-123  ← polling ──────────┘
```

Script que não espera **mente**. Ele reporta sucesso quando tudo que houve foi
o Manager aceitar o pedido — antes de o fabric ter mudado, ou antes de ter
falhado.

Esperar direito são quatro coisas: intervalo entre consultas, timeout
realista, distinguir "terminou bem" de "terminou mal", e devolver contexto
suficiente para alguém debugar às 3 da manhã.

## Preview: o `terraform plan` que quase ninguém usa

`preview_device_config()` devolve a CLI que **seria** aplicada, sem aplicar.
É grátis, é seguro, e é a única resposta honesta para "o que exatamente vai
mudar?". Use sempre.

## Mãos à obra

```bash
export WS_ALUNO=07
python exercicio.py --listar     # ache o seu config group
python exercicio.py --preview    # veja antes de fazer
python exercicio.py --deploy     # faça, e espere terminar
```

Enquanto o deploy roda, abra a GUI em **Monitor → Tasks**. É a mesma tarefa
que o seu código está consultando. Esse é o momento em que a API deixa de ser
abstrata.

Confira o polling sem lab:

```bash
python -m pytest ../tests/test_tasks.py -q
```

## Namespace

O lab é compartilhado. Tudo que você criar leva `ws<NN>-`. O código levanta
`SystemExit` se `WS_ALUNO` não estiver definido — de propósito.

## Quando um payload der 400

Não adivinhe. Abra as Ferramentas de Desenvolvedor do navegador, faça a mesma
ação clicando na GUI e compare o corpo da requisição. A GUI usa exatamente a
mesma API que você. **Isso é a técnica, não a gambiarra.**
