# Plano de implementação da prova de conceito: `ble-tx-poc` e `ble-rx-poc`

**Projeto:** BTLE, a tese  
**Branches a criar:** `ble-tx-poc` (a partir de `ble-tx-tag-8`) e `ble-rx-poc` (a partir da branch da gateway)  
**Data:** 2026-11-06  
**Autor:** Miguel Simões  
**Estado:** plano. A `ble-tx-poc` está implementada até à fase 4, sem placa: ver [`Senseworks/TX_POC.md`](Senseworks/TX_POC.md). A `ble-rx-poc` ainda não existe.

---

## 1. Objetivo

Demonstrar, ponta a ponta e em hardware real, o tag BLE da tese:

```
TMP100 ──I2C──► placa TX (ble-tx-poc) ~~~ 2,4 GHz ~~~► placa RX (ble-rx-poc) ──Ethernet──► PC
                 FSM sem CPU                            recetor + ARM               BCH, °C, gráfico
```

- **Placa TX:** uma FSM lê o sensor por I2C, sem processador no caminho dos dados. A temperatura vai em 8 bits num
  pacote BLE Legacy Advertising (ADV_NONCONN_IND) com paridade BCH t = 8, sempre no mesmo canal.
- **Placa RX:** recebe o pacote e passa-o ao PC. O PC corrige os erros com o BCH, converte para °C e mostra a curva.
- **O que a PoC prova:** que a aquisição sem CPU, o formato do pacote e a correção BCH funcionam numa ligação rádio
  real. A área e o consumo do tag final saem dos fluxos de ASIC (45 nm e GF180), não da placa.

A `ble-tx-poc` **não é feita só para o TMP100**. O sensor é descrito por um perfil de configuração, e o mesmo RTL
serve outros sensores I2C ou SPI e, através de um parâmetro, um ADC.

## 2. Decisões tomadas

| Tema | Decisão |
|---|---|
| Sensor da PoC | TI TMP100 (SOT-23-6 numa placa adaptadora), I2C, 2,7–5,5 V, 9 a 12 bits, ±2 °C entre −25 e +85 °C |
| ADC | parâmetro (`ADC_EN`, desligado por omissão). O TMP100 não precisa dele |
| Número de sensores | 1 (`SENSOR_BYTES = 1`). O parâmetro aceita 2 para o futuro |
| Codificação | 8 bits, passo de 0,5 °C, gama de 128 °C (−40 a +87,5 °C). Tem de ser reconfigurável |
| Correção de erros | BCH t = 8, como na `ble-tx-tag-8` |
| Canais | um só canal de advertising, guardado no perfil. O recetor nunca é um recetor BLE genérico |
| Intervalo | configurável depois de fabricar. Por omissão, 1 s na demonstração |
| Conversão para unidades | na gateway, isto é, no PC |
| Ordem | primeiro FPGA, primeiro a `ble-tx-poc` |
| Ligação RX → PC | a cadeia do upstream: recetor na PL → ARM (`btle_ll`) → Ethernet → PC (`ble_fpga_ctl`, Wireshark), mais uma app Python |
| Memória de configuração na PoC | EEPROM I2C externa 24AA02E48: o perfil fica na metade livre e o AdvA é o EUI-48 de fábrica |
| Memória de configuração no tag final | dentro do chip (OTP para o AdvA; MTP ou OTP com várias entradas para a configuração), ver § 8 |

## 3. Arquitetura

### 3.1 Placa TX (`ble-tx-poc`)

```
 breadboard                 placa SDR (Zynq-7020 + AD9361)
┌──────────────┐  SCL, SDA ┌───────────────────────────────────────────────┐
│ TMP100 0x48  │◄─────────►│ PL: tag_core                       AD9361     │
│ 24AA02E48    │ 3,3 V,GND │   arranque: perfil ← memória    ┌──────────┐  │
│ 0x50         │           │   FSM: dorme→mede→espera→lê→TX ─I/Q─►│ rádio    │──┼──► antena
└──────────────┘           │   btle_tx (SENSOR_BYTES = 1)    │ 2,4 GHz  │  │
                           │ PS (ARM): só inicializa o AD9361 └──────────┘  │
                           └───────────────────────────────────────────────┘
```

O `tag_core` é o mesmo núcleo no FPGA e no ASIC. Tem estes blocos:

| Bloco | Função |
|---|---|
| tick de 32 kHz | um clock enable. No ASIC é um relógio de 32,768 kHz; no FPGA, o MMCM não desce aos 32 kHz |
| temporizador | intervalo + advDelay (LFSR de 8 bits com semente no AdvA) |
| carregador do perfil | no arranque lê a memória de configuração, verifica a versão, o tamanho e o CRC-8, e usa o perfil compilado na RTL se falhar. A origem é um parâmetro: `CFG_SRC = EEPROM` (PoC), `OTP` ou `MTP` (ASIC) |
| registos de configuração | flip-flops com a cópia do perfil e do AdvA |
| sequenciador | executa o programa do perfil: um programa de arranque e um por medida (escrever, esperar, ler) |
| camada de bits | I2C (SCL a 16 kHz, open-drain, com clock stretching) e SPI, escolhidos no perfil. ADC por parâmetro |
| captura | janela de bits, sinal, offset, saturação; `0xFF` quando o sensor não responde |
| modo de teste | envia um contador em vez do sensor, para a app contar pacotes perdidos |
| `btle_tx` | o da `ble-tx-tag-8`, com `SENSOR_BYTES` e o byte do sensor numa porta direta |

**Integração na placa:**
- O `tag_core` substitui o caminho TX dentro do `btle_controller`, e o AXI fica só para ler estado (contadores e
  último valor, para depuração).
- O ARM só corre a inicialização do AD9361: a frequência do canal fixo, o ganho, o FIR e a PL como fonte do DAC
  (`DAC_DDS_SEL = 2`).
- `GAUSS_TABLE = 1`, para que o filtro não precise de firmware.

### 3.2 Perfil do TMP100 (por omissão)

| Passo | I2C | Nota |
|---|---|---|
| arranque | ponteiro `0x01`, config `0x01` | shutdown, 9 bits |
| cada evento | ponteiro `0x01`, config `0x81` | uma conversão (one-shot) |
| espera | 75 ms (pior caso; 40 ms típico) | o bit OS lido dá o comparador, não o fim da conversão |
| leitura | ponteiro `0x00`, 2 bytes | `raw[15:7]` = 2·T, com sinal |
| captura | N = sat(`raw[15:7]` + 80), 0..254; `0xFF` em NACK | a gateway calcula T = −40 + N/2 |

- **Passo de 0,25 °C:** config `0xA1` (10 bits), espera de 150 ms e janela `raw[15:6]`. Muda-se só o perfil.
- **Intervalo mínimo:** ~80 ms a 9 bits, por causa da conversão.
- **A confirmar no PDF oficial antes de fixar o perfil:** os tempos máximos e o comportamento do bit OS.

### 3.3 Memória de configuração da PoC (24AA02E48)

| Endereços | Conteúdo |
|---|---|
| `0x00–0x7F` (livre) | perfil: versão, tamanho, intervalo, canal, `TxAdd`, programa do sensor, captura, modo de teste, CRC-8 |
| `0x80–0xFF` (protegida de fábrica) | o EUI-48 em `0xFA–0xFF`, usado como AdvA |

- O EUI-48 começa pelo OUI da Microchip (por exemplo `00-04-A3`), por isso os 2 bits de cima não são `11` e não
  serve de endereço aleatório estático. Vai como **endereço público, `TxAdd = 0`**.
- O CRC do perfil deteta corrupção, não alterações intencionais. O AdvA não é uma credencial: autenticar
  medições fica fora da PoC.
- O perfil é gravado com um programador USB-I2C (por exemplo CH341A).

### 3.4 Placa RX (`ble-rx-poc`)

```
antena ──► AD9361 ──► PL: recetor (branch da gateway) ──► ARM: btle_ll ──Ethernet──► PC: ble_fpga_ctl + app Python
```

O que a `ble-rx-poc` acrescenta à branch da gateway:
- A configuração fixa igual à do tag: canal, AA `0x8E89BED6`, CRC init `0x555555`.
- Os pacotes do formato de 1 byte: PDU de 21 bytes e BCH com n = 120 (k = 56: AdvA + 1 byte).
- O cabeçalho reconstruído com `TxAdd = 0`.
- Os pacotes com CRC errado entregues ao PC com a flag, para o BCH os poder corrigir.
- O comprimento conhecido do pacote, em vez do que vem no cabeçalho (um bit errado no comprimento cortaria o
  pacote).
- A app Python no PC:
  - lê os pacotes do `ble_fpga_ctl`;
  - corrige o BCH (com a galois e o `scripts/senseworks/tag_bch.py`);
  - repõe os bytes conhecidos e confirma o CRC;
  - converte com o perfil do tag, numa tabela indexada pelo AdvA;
  - grava CSV e mostra um gráfico ao vivo;
  - conta os pacotes recebidos, corrigidos e perdidos (estes no modo de teste).

Uma FSM de receção na PL só é precisa se mais tarde se quiser tirar o ARM do caminho. Na PoC, o firmware do
upstream já faz esse papel.

## 4. Fases

As fases 1 a 3 são de simulação e não precisam das placas. O caminho crítico é 0 → 4 → 5 → 6.

### Fase 0: placas e ferramentas
- Conseguir **duas placas iguais com Zynq-7020 e AD9361**. O repo já tem o fluxo de três: `antsdr`
  (ANTSDR E310), `antsdr_e200` e `sdrpi`, todas `xc7z020clg400-1`. Ver § 7.
- Confirmar os pinos livres de 3,3 V para o I2C (a ver no esquema da placa):
  - `antsdr`: tem 11 `gpio_bd` a 3,3 V no XDC;
  - `sdrpi`: tem GPIO a 2,5 V e precisaria de um conversor de níveis;
  - `antsdr_e200`: não tem nenhum no XDC.
- Instalar o Vivado 2022.2 e o IP da ADI do upstream (`fpga/build-adi-ip.sh`). As corridas do repo fora de
  contexto usaram o 2026.1.
- Preparar 2 cartões microSD com o Kuiper 2022_r2 (`fpga/README.md`).
- **Arranque com o upstream:** TX numa placa e RX na outra, até ver pacotes no Wireshark. Isto valida as placas,
  o RF e as ferramentas antes de qualquer mudança nossa. Nenhuma branch do repo correu ainda numa placa.

### Fase 1: `SENSOR_BYTES` no `btle_tx` (`ble-tx-poc`)
- Parametrizar o comprimento: cabeçalho, AD length, mensagem BCH (n = 128 ou 120) e último bit.
- **Validação:**
  - com `SENSOR_BYTES = 2`, igual à `ble-tx-tag-8` bit a bit, em todas as saídas e todos os ciclos
    (`test_tx_tag.py`);
  - com `SENSOR_BYTES = 1`, igual à `ble-tx-tag-1byte`;
  - BCH contra a galois (`check_bch_galois.py`), pacote verificado no scapy (`check_tag_scapy.py`), mutantes e
    lint.

### Fase 2: o `tag_core` em simulação
- Os blocos do § 3.1, com o TMP100 como perfil por omissão.
- **Modelos no testbench:**
  - TMP100: ponteiro, configuração, one-shot, dados de 9 a 12 bits;
  - 24AA02E48: metade de cima protegida, EUI-48;
  - um segundo sensor diferente (por exemplo SPI), para provar que é genérico.
- **Casos de teste:** NACK do sensor, perfil corrompido (passa ao perfil por omissão), saturação nos dois
  extremos, reset a meio de um evento, limites do intervalo e do advDelay, modo de teste.
- **De ponta a ponta:** modelo do sensor → FSM → amostras do `btle_tx` → descodificação em Python (scapy + BCH),
  com o valor certo.
- Mutantes, lint e cobertura dos estados da FSM.

### Fase 3: área e consumo do `tag_core` (ASIC)
- Área e fuga em 45 nm (`run_area.sh`) e layout em GF180, sem ADC.
- Duas variantes:
  - `CFG_SRC = EEPROM`: sem os 6 blocos de eFuse (−48 452 µm²), mais os flip-flops da cópia;
  - `CFG_SRC = OTP`: o AdvA continua no eFuse.
- Comparar com a `ble-tx-tag-8` (129 286 µm²) e a `ble-tx-tag-1byte` (126 983 µm²).

### Fase 4: `ble-tx-poc` na placa TX
- O `tag_core` entra no `btle_controller`. As restrições do I2C ficam no XDC (open-drain, pull-ups externos de
  4,7 kΩ), e põe-se uma ILA na FSM e no I2C.
- O script de arranque do ARM inicializa o AD9361 e não corre mais nada.
- **Validação:**
  - o anúncio aparece num telemóvel com um scanner BLE (por exemplo nRF Connect), com o byte da temperatura nos
    Manufacturer Data, porque o pacote é um anúncio normal;
  - aparece também no Wireshark da placa RX com o recetor do upstream;
  - o valor muda quando se aquece o sensor.

### Fase 5: `ble-rx-poc`
- A partir da branch da gateway: verificar que cumpre o § 3.4 e acrescentar o que faltar.
- A app Python no PC.
- **Validação:** em simulação, os pacotes do RTL da `ble-tx-poc` passam pelo recetor RTL e pela app com o valor
  certo, também com bits errados (até 8 corrigidos pelo BCH).

### Fase 6: demonstração e medições
- Aquecer e arrefecer o sensor e ver a curva no PC.
- PER com e sem BCH, com o modo de teste, em função da atenuação (cabo SMA com atenuadores ou distância).
  Comparar com o modelo do `TX_TAG_COMPARISON.md` § 10.
- Mudar o passo (0,5 ↔ 0,25 °C), o intervalo e o canal só regravando o perfil, com o mesmo bitstream.

### Fase 7: documentação
- A validação e as medições de cada branch, com as evidências em `results/`, como nas outras branches.

## 5. BOM

| Item | Qt. | Nota |
|---|---|---|
| TMP100 na placa adaptadora SOT-23-6 | 1 | ADD0 = ADD1 = GND → endereço `0x48` |
| Placa SDR com Zynq-7020 + AD9361 | 2 | iguais; ver § 7 |
| EEPROM 24AA02E48 + adaptador | 1 | perfil + AdvA |
| Programador USB-I2C (por exemplo CH341A) | 1 | para gravar o perfil |
| Resistências de 4,7 kΩ (pull-ups), condensador de 100 nF, fios, breadboard | — | |
| Antenas de 2,4 GHz | 2 | ou cabo SMA + atenuadores de 30–40 dB, para medições repetíveis |
| Cartões microSD | 2 | Kuiper 2022_r2 |
| Fontes de alimentação | 2 | |
| Cabo USB | 1–2 | consola, JTAG |
| Cabo Ethernet (ou adaptador USB-Ethernet) | 1–2 | ligação ao PC na cadeia do upstream; cópia de ficheiros por ssh/scp |
| Conversor de níveis | 0–1 | só se os pinos livres não forem de 3,3 V |
| PC | 1 | Vivado 2022.2, Python, Wireshark |

## 6. Divisão do trabalho

- **Claude:** o RTL, os testbenches, os modelos, os scripts (fluxos, app Python), os documentos e as corridas de
  simulação, ASIC e Vivado no PC.
- **Miguel:** as placas, as ligações, a gravação dos cartões e da EEPROM, os testes em placa e as medições, com
  os passos e os scripts preparados.

## 7. Em aberto

1. **As placas.** A lista de máquinas do laboratório não tem nenhuma placa com AD9361. A única Zynq-7020 é uma
   ZedBoard (na `sofia`), que só teria rádio com uma placa FMC com AD9361 (por exemplo AD-FMCOMMS3). Seria só uma,
   e o repo não tem o fluxo da ZedBoard. Falta decidir que duas placas se usam.
2. **A branch da gateway.** Não existe em nenhum repositório local (`Desktop\Tese`) nem no `origin`. É preciso
   saber onde está antes da fase 5.
3. **O processo do tag final** (§ 8): o GF180 do PDK aberto só tem eFuse. Outro processo pode ter MTP ou OTP
   antifuse.
4. **"Alimentado pelo ar":** a potência disponível e a distância ao emissor, porque determinam o orçamento de
   energia por evento.

## 8. O tag final (ASIC), depois da PoC

O tag final é superfino, sem bateria, barato e fabricado em grande quantidade. Por isso a memória de configuração
da PoC (EEPROM externa) não serve para o produto:

- **Um só die:** lógica digital, rádio, captação de energia e memória não volátil. Vários dies no mesmo
  encapsulamento (SiP) aumentam o custo por unidade e a espessura.
- **O AdvA em OTP dentro do chip,** de preferência antifuse. Os 8 075 µm² por byte medidos são do bloco de eFuse
  de 8 bits do PDK aberto.
- **A configuração reduzida ao mínimo e dentro do chip:** MTP, se a foundry a tiver, ou OTP com 2 a 4 entradas,
  em que cada configuração nova vai para a entrada seguinte e o chip usa a última válida.
- **Sem EEPROM externa nem flip-flops como memória principal.** Sem bateria, a energia falta muitas vezes. Reler
  uma EEPROM em cada arranque (~10 ms de I2C) pode gastar mais do que o próprio pacote (232 µs de rádio); é uma
  estimativa, ainda por medir.
- **Um sensor de temperatura dentro do chip** (oscilador ou transístor bipolar). Gasta nW a µW e dispensa o I2C.
  O TMP100 gasta ~45 µA durante 40 ms por medida.

O `tag_core` está pensado para isto. A origem da configuração é um parâmetro (`CFG_SRC`), e a interface I2C ou SPI
fica como opção para sensores externos.
