# Módulo 4 — Terraform, direito (45 min)

A mesma mudança do módulo 3, agora declarativa.

## O ponto da aula

Não é que Terraform seja melhor que Python. É que **Terraform só é utilizável
por quem entende o que ele está escondendo** — que é exatamente o que você
implementou na mão uma hora atrás.

| Módulo 3 (imperativo) | Módulo 4 (declarativo) |
|---|---|
| Você escreve o **como** | Você escreve o **o quê** |
| Você faz o polling | O provider faz |
| Você trata a falha | O provider trata |
| Você sabe o estado? Não | O `state` sabe |
| Funciona em qualquer endpoint | Só no que o provider cobre |

## O que vamos aprender

| Automação | SD-WAN |
|---|---|
| Declarativo vs. imperativo | Config group como código |
| State e detecção de drift | Quem mexeu na GUI depois de você |
| `plan` como revisão de mudança | O diff antes do push |
| Ler o schema do provider | Nomes de resource que mudam entre versões |

## Mãos à obra

```bash
source ../scripts/vault-env.sh     # exporta TF_VAR_*
cp terraform.tfvars.example terraform.tfvars   # ajuste o seu "aluno"

terraform init
terraform plan      # ← vai falhar. É de propósito.
```

### TODO 2.1 — o erro plantado

O `plan` vai reclamar de um atributo inexistente em
`sdwan_system_banner_feature`. **Não procure no Google.** Pergunte ao próprio
provider:

```bash
terraform providers schema -json \
  | jq '.provider_schemas
        | .["registry.terraform.io/ciscodevnet/sdwan"].resource_schemas
        | .sdwan_system_banner_feature.block.attributes | keys'
```

Ler schema de provider é a habilidade. Decorar nome de atributo não é —
esses nomes mudaram entre as versões 0.x deste provider, e vão mudar de novo.

## A descoberta desconfortável

Repare no `locals` do `main.tf`. O data source `sdwan_device` expõe
`device_id`, `hostname`, `reachability`, `serial_number`, `site_id`, `state`,
`status` e `uuid` — **e mais nada**. Não existe `personality`.

Ou seja: pelo Terraform você não consegue separar edge de controlador, coisa
que `/dataservice/device` entrega de graça.

É por isso que o toolkit em Python não vira lixo quando você adota Terraform.
O provider cobre o caminho declarativo; a API cobre o resto. **Ferramenta boa
é a que você sabe quando não usar.**

## Drift

Depois do `apply`, vá à GUI e mude o banner na mão. Volte e rode:

```bash
terraform plan
```

Ele encontra. Esse é o superpoder que o script do módulo 3 não tinha: o
Terraform sabe qual *deveria* ser o estado, então percebe quando alguém mexeu.

## E os outros?

Ansible (`cisco.catalystwan`) e Sastre resolvem o mesmo problema com outros
compromissos — o primeiro sem state, o segundo especializado em
backup/restore/migração. Ficaram de fora por causa das quatro horas, não por
demérito. Escolhemos profundidade em um em vez de um passeio por três.
