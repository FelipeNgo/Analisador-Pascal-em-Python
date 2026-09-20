# Analisador Léxico e Sintático de Pascal (Python)

Programa que lê código no estilo **Pascal / Turbo Pascal** e verifica se cada comando está na
**ordem correta** e com os **requisitos certos**, com base em um **autômato finito** desenhado
para cada comando. Para cada comando reconhecido, ele mostra o caminho percorrido no autômato
(`S0 -> S1 -> S2 ...`) e, quando há erro, o estado em que parou e o que era esperado.

Projeto de Compiladores / Linguagens Formais, implementado em um único arquivo, sem bibliotecas externas.

## Como funciona

1. **Análise léxica:** separa o texto em tokens e classifica cada um (Reservado, Tipo, Variável,
   Número, Texto, Atribuição, Pontuação, Operador). Ignora comentários (`{ }`, `(* *)`, `//`) e
   não diferencia maiúsculas de minúsculas.
2. **Análise sintática:** um analisador descendente recursivo em que cada método é um autômato
   e cada transição `Sx -> Sy` é uma chamada de função. Faz recuperação de erros, então mostra
   vários problemas de uma só vez.

## Como executar

Requer **Python 3.6 ou superior**.

```bash
# Modo interativo: digite o código linha a linha
python analisador.py

# Analisar um arquivo
python analisador.py exemplos/correto.pas
```

No modo interativo, uma linha em branco **analisa** o que foi digitado, e uma linha em branco
logo no início **encerra** o programa.

## Exemplos de saída

Código correto:

```
[OK]   linha 1  begin  S0 -> S1 -> S2 -> S1 -> S2 -> S3 -> S4
[OK]      linha 2  delay  S0 -> S1 -> S2 -> S3 -> S4 -> S5
[OK]      linha 3  gotoxy  S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S6

RESULTADO: código sintaticamente correto.
```

Código com erros:

```
[ERRO] linha 1  begin  S0 -> S1 -> S2 -> S2 -> S1 -> S3 -> S4  (parou aqui)
[ERRO]    linha 2  delay  S0 -> S1 -> S2  (parou aqui)
[OK]      linha 3  clreol  S0 -> S1
[OK]      linha 4  halt  S0 -> S1 -> S2

RESULTADO: 2 erro(s) encontrado(s):
  - Linha 2, coluna 9: [delay | S2] esperado [tempo_ms] (número, texto, variável, função ou '('), mas encontrado ';' (pontuação)
  - Linha 3, coluna 9: [begin | S2] esperado ';' ou 'end', mas encontrado 'halt' (palavra reservada) (na linha 4)
```

## Comandos verificados

| Categoria | Comandos |
|---|---|
| Estrutura | `begin ... end`, `var`, `if ... then ... else`, `for ... to/downto ... do`, `while ... do`, `repeat ... until`, `goto` |
| Sem argumentos | `clreol`, `clrscr`, `exit`, `halt`, `keypressed`, `maxavail`, `memavail`, `paramcount`, `randomize`, `readln`, `wherex`, `wherey`, `writeln` |
| Com argumentos | `delay`, `paramstr`, `sizeof`, `length`, `hi`, `lo`, `random`, `freemem`, `getmem`, `gotoxy`, `fillchar`, `move`, `inline` |
| Entrada e saída | `read`, `read(kbd, var)`, `write` |

Também são aceitos expressões (aritméticas, relacionais e lógicas), tipos (`integer`, `string[n]`,
`array [a..b] of tipo`), rótulos e atribuições (`x := 5`).

## Decisões e limitações

- A atribuição `:=` não está nos autômatos originais, mas foi incluída porque é necessária dentro de blocos e do `for`.
- `clrscr` foi tratado como comando sem argumentos.
- `writeln` e `readln` seguem o autômato e aceitam apenas a forma sem argumentos (`writeln;`).
  Para aceitar `writeln('texto');`, altere `PERMITIR_ARGUMENTOS_EM_READLN_WRITELN` para `True`.
- Verifica **apenas a sintaxe**: não checa se as variáveis foram declaradas nem os tipos dos valores.
- Chamadas a funções que não estão na lista acima são recusadas.

## Estrutura do código

`analisador.py` é dividido em três seções:

- **Léxico:** `tokenizar()` e a classe `Token`.
- **Sintático:** as classes `Parser` e `Cmd`, com um método para cada autômato e a tabela `LINEARES` para os comandos de formato fixo.
- **Programa principal:** `analisar()` e `main()`.

## Versões em outras linguagens

Este mesmo analisador também foi implementado em C# (com o lexer, o parser e o programa principal em arquivos separados).
