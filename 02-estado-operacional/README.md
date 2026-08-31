# Módulo 2 — Estado operacional como dado (50 min)

## A ideia central do bootcamp

> Uma mudança só é segura se você consegue **provar** que o fabric ficou igual
> ou melhor depois dela.

Provar exige um retrato comparável, em formato de dado. Não um `show` colado
no chat da equipe.

## O que vamos aprender

| Automação | SD-WAN |
|---|---|
| Normalizar na borda | As chaves com hífen e os campos inconsistentes |
| Modelar com dataclass | `DeviceState`, `FabricSnapshot` |
| Serializar e versionar | Retrato em JSON |
| Diff com opinião | Perder BFD é regressão; ganhar, não |

## Real-time vs. banco de estatísticas

A distinção que mais separa quem automatiza bem de quem derruba o Manager:

| | `/dataservice/device/*` | `/dataservice/statistics/*` |
|---|---|---|
| Origem | Consulta o equipamento **agora**, pelo plano de controle | Lê o banco de estatísticas |
| Custo | Alto — cada chamada atravessa o fabric | Baixo |
| Frescor | Instantâneo | Minutos de atraso |
| Use para | Pré/pós-mudança | Tendência, relatório, dashboard |

Neste módulo usamos real-time, porque queremos o agora. E é exatamente por
isso que o cliente tem rate limit — e o lab é compartilhado com a turma.

## Mãos à obra

```bash
python exercicio.py --salvar snapshots/antes.json
# … alguém muda alguma coisa (ou você espera) …
python exercicio.py --salvar snapshots/depois.json
python exercicio.py --comparar snapshots/antes.json snapshots/depois.json
```

Confira a lógica do juiz sem tocar no lab:

```bash
python -m pytest ../tests/test_diff.py -q
```

## O diff é assimétrico de propósito

Ganhar sessão BFD é bom. Perder é ruim. Um `diff` de texto não sabe disso —
o seu sim. É essa opinião que permite ao pipeline do módulo 5 decidir sozinho
entre seguir em frente e fazer rollback.

## Prova de que rodou de verdade

**Qual edge tem mais sessões BFD `up`?**

## Pense nisto

O `compare()` só olha a **diferença**. Um device que já estava fora antes e
continua fora depois não gera achado nenhum. Isso é acerto ou defeito?

(A resposta está no `precheck()` do módulo 5.)
