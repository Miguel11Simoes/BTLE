# Âmbito: um RISC-V reconfigurável no baseband BLE

**Estado:** rascunho. Este documento fixa o ponto de partida e as perguntas que
têm de ser respondidas **antes** de se mexer no RTL. O que está por decidir está
marcado como tal, e não deve ser decidido em código sem passar por aqui.

**Base:** tag `upstream-baseline` (`8540186`). Branch de trabalho: `risc-v-ble`.

---

## 1. O que o upstream já traz

Verificado no repositório, não assumido:

| Bloco | Ficheiros | O que faz |
|---|---|---|
| PHY | `btle_phy.v`, `btle_rx.v`, `btle_rx_core.v`, `btle_tx.v` | Cadeia de receção e transmissão |
| Modulação | `gfsk_modulation.v`, `gfsk_demodulation.v`, `gauss_filter.v`, `vco.v` | GFSK, filtro gaussiano, oscilador |
| Tratamento de bits | `crc24.v`, `crc24_core.v`, `scramble.v`, `search_unique_bit_sequence.v`, `bit_repeat_upsample.v` | CRC, whitening, deteção do access address |
| Link Layer | `btle_ll.v` | Máquina de estados do LL, com interface AXI-lite (`ll_s_axi`), RAMs de RX e contadores de evento |
| Interface de host | `btle_controller.v`, `btle_controller_wrapper.v`, `uart_frame_rx.v`, `uart_frame_tx.v` | Controlo e ligação série ao host |
| Relógios e memórias | `tx_clk_gen.v`, `rx_clk_gen.v`, `clock_domain_conversion_iq.v`, `sdpram_*.v` | Geração de relógios, travessia de domínios, RAMs |
| Fluxos | `fpga/` (ADI HDL, AntSDR, SDR Pi), `open_btle_baseband_chip/` (fluxo OpenLane até GDSII) | FPGA e ASIC |
| Software | `host/`, `firmware/`, `python/`, `matlab/` | Ferramentas de host e análise |

Duas consequências úteis:

1. A fronteira natural **já existe**: a PHY é fixa e o LL fala por AXI-lite. É
   aí que um core reconfigurável entra sem reescrever a cadeia de rádio.
2. Há um fluxo ASIC completo no `open_btle_baseband_chip`, o que dá um ponto de
   comparação de área antes e depois.

## 2. A pergunta central

**O que passa a ser software num RISC-V, e o que fica em hardware fixo?**

O candidato óbvio é o **Link Layer**: temporização de eventos, máquina de
estados de ligação, hopping, gestão de PDUs. A PHY (GFSK, CRC, whitening,
deteção de preâmbulo) tem requisitos de débito por amostra que não se satisfazem
com um core escalar, e deve ficar em hardware.

**Por decidir:**

- [ ] Que funções do `btle_ll.v` migram para software, e quais ficam.
- [ ] Que core RISC-V, e com que extensões. (Há um argumento forte para reutilizar
      o Snitch da outra linha da tese; há outro, de simplicidade, para um core
      pequeno tipo PicoRV32 ou Ibex, que o `py2hwsw` já traz como submódulos.)
- [ ] O que significa **reconfigurável** aqui: parâmetros em runtime, firmware
      substituível, ou lógica reconfigurável de facto. As três são coisas
      diferentes e implicam provas diferentes.
- [ ] Qual é a métrica que a tese vai defender: área, energia por pacote,
      latência de resposta do LL, ou flexibilidade demonstrada por um caso de uso.

## 3. Requisitos que vão ser difíceis, e que convém escrever já

- **Temporização do BLE.** O LL tem janelas apertadas (por exemplo o T_IFS de
  150 µs entre pacotes). Um core a correr software tem de as cumprir de forma
  determinística; isto é um requisito, não um detalhe de implementação.
- **Interface PHY↔core.** Tem de ser especificada: registos, interrupções,
  buffers de PDU, e quem é dono de cada memória.
- **Prova de equivalência.** Depois da mudança, o rádio tem de continuar a
  funcionar. O upstream tem testbenches (`*_tb.v`) e ferramentas em `python/` e
  `matlab/`; a prova mais forte é comparar o comportamento antes e depois com os
  mesmos estímulos.

## 4. Relação com a outra linha da tese

Esta é uma linha **separada** do `snitch_cluster_tese`. Não se misturam
repositórios. Se um dia o BLE for o transporte dos alertas do SoC de manutenção
preditiva, essa integração é um marco próprio, e só depois de cada lado se
aguentar sozinho.

## 5. Ordem de trabalho proposta

1. Fechar as decisões da secção 2, aqui, por escrito.
2. Reproduzir o upstream tal como está: simular um testbench e correr o fluxo de
   FPGA ou o do OpenLane, para ter uma referência de comportamento **e** de área.
3. Especificar a interface PHY↔core antes de escrever RTL.
4. Integrar o core, com o LL ainda em hardware, e provar que nada regrediu.
5. Só então migrar funções do LL para software, uma de cada vez, com a
   comparação da etapa 2 a servir de oráculo.

Cada passo com evidência guardada, no mesmo espírito da outra linha: o que
passou, o que não foi testado, e o que não é afirmado.
