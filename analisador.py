#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisador léxico e sintático (Pascal / Turbo Pascal) baseado nos autômatos do diagrama.

Uso:
    python analisador.py                 -> modo interativo (digite o código linha a linha)
    python analisador.py meucodigo.pas   -> analisa um arquivo
"""
import os
import sys

# =====================================================================================
#  LÉXICO
# =====================================================================================

TIPOS = {
    "integer", "byte", "word", "longint", "shortint", "real", "single",
    "double", "extended", "comp", "boolean", "char", "string", "pointer", "text",
}

RESERVADAS = {
    # estrutura
    "begin", "end", "var", "if", "then", "else", "for", "to", "downto", "do",
    "while", "repeat", "until", "goto", "of", "array", "kbd",
    # operadores e constantes em forma de palavra
    "div", "mod", "and", "or", "not", "xor", "shl", "shr", "true", "false", "nil",
    # comandos / funções do autômato
    "clreol", "clrscr", "delay", "exit", "fillchar", "freemem", "getmem", "gotoxy",
    "halt", "hi", "inline", "keypressed", "length", "lo", "maxavail", "memavail",
    "move", "paramcount", "paramstr", "random", "randomize", "read", "readln",
    "sizeof", "wherex", "wherey", "write", "writeln",
}

# tipos de token
RESERVADO, TIPO, VARIAVEL, NUMERO, TEXTO = "Reservado", "Tipo", "Variável", "Número", "Texto"
ATRIBUICAO, PONTUACAO, OPERADOR, FIM = "Atribuição", "Pontuação", "Operador", "Fim"

# nome usado nas mensagens de erro ("encontrado 'x' (palavra reservada)")
DESCRICAO_CLASSE = {
    RESERVADO: "palavra reservada", TIPO: "tipo", VARIAVEL: "identificador",
    NUMERO: "número", TEXTO: "texto", ATRIBUICAO: "atribuição",
    PONTUACAO: "pontuação", OPERADOR: "operador",
}


class Token:
    def __init__(self, valor, tipo, linha, coluna):
        self.valor = valor
        self.lower = valor.lower()
        self.tipo = tipo
        self.linha = linha
        self.coluna = coluna

    def __str__(self):
        return '"%s" - Linha: %d | %s' % (self.valor, self.linha, self.tipo)


def eh_letra(c):
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"


def eh_digito(c):
    return "0" <= c <= "9"


def eh_hex(c):
    return eh_digito(c) or ("a" <= c <= "f") or ("A" <= c <= "F")


def tokenizar(linhas, erros):
    """Transforma as linhas de código em tokens. Erros léxicos vão para 'erros'."""
    tokens = []
    em_chave = em_paren = False
    coment_linha = coment_col = 0

    for n, s in enumerate(linhas):
        L = n + 1
        i = 0
        while i < len(s):
            if em_chave:
                j = s.find("}", i)
                if j < 0:
                    i = len(s)
                else:
                    i, em_chave = j + 1, False
                continue
            if em_paren:
                j = s.find("*)", i)
                if j < 0:
                    i = len(s)
                else:
                    i, em_paren = j + 2, False
                continue

            ch = s[i]
            col = i + 1

            if ch.isspace():
                i += 1
                continue
            if ch == "{":
                em_chave, coment_linha, coment_col = True, L, col
                i += 1
                continue
            if ch == "(" and s[i + 1:i + 2] == "*":
                em_paren, coment_linha, coment_col = True, L, col
                i += 2
                continue
            if ch == "/" and s[i + 1:i + 2] == "/":
                break

            # identificador / palavra reservada / tipo
            if eh_letra(ch):
                ini = i
                while i < len(s) and (eh_letra(s[i]) or eh_digito(s[i])):
                    i += 1
                v = s[ini:i]
                low = v.lower()
                tp = VARIAVEL
                if low in TIPOS:
                    tp = TIPO
                elif low in RESERVADAS:
                    tp = RESERVADO
                tokens.append(Token(v, tp, L, col))
                continue

            # número (inteiro, real, hexadecimal $FF)
            if eh_digito(ch):
                ini = i
                while i < len(s) and eh_digito(s[i]):
                    i += 1
                if i + 1 < len(s) and s[i] == "." and eh_digito(s[i + 1]):
                    i += 1
                    while i < len(s) and eh_digito(s[i]):
                        i += 1
                if i < len(s) and s[i] in "eE":
                    k = i + 1
                    if k < len(s) and s[k] in "+-":
                        k += 1
                    if k < len(s) and eh_digito(s[k]):
                        i = k
                        while i < len(s) and eh_digito(s[i]):
                            i += 1
                tokens.append(Token(s[ini:i], NUMERO, L, col))
                continue
            if ch == "$" and i + 1 < len(s) and eh_hex(s[i + 1]):
                ini = i
                i += 1
                while i < len(s) and eh_hex(s[i]):
                    i += 1
                tokens.append(Token(s[ini:i], NUMERO, L, col))
                continue

            # texto 'abc' (com '' como aspa escapada) e #65
            if ch == "'":
                ini = i
                i += 1
                fechou = False
                while i < len(s):
                    if s[i] == "'":
                        if s[i + 1:i + 2] == "'":
                            i += 2
                            continue
                        i += 1
                        fechou = True
                        break
                    i += 1
                if not fechou:
                    erros.append("Linha %d, coluna %d: texto não foi fechado (falta o apóstrofo final)" % (L, col))
                    continue
                tokens.append(Token(s[ini:i], TEXTO, L, col))
                continue
            if ch == "#" and i + 1 < len(s) and eh_digito(s[i + 1]):
                ini = i
                i += 1
                while i < len(s) and eh_digito(s[i]):
                    i += 1
                tokens.append(Token(s[ini:i], TEXTO, L, col))
                continue

            # símbolos de dois caracteres
            dois = s[i:i + 2]
            if dois == ":=":
                tokens.append(Token(dois, ATRIBUICAO, L, col))
                i += 2
                continue
            if dois in ("<=", ">=", "<>"):
                tokens.append(Token(dois, OPERADOR, L, col))
                i += 2
                continue
            if dois == "..":
                tokens.append(Token(dois, PONTUACAO, L, col))
                i += 2
                continue

            # símbolos de um caractere
            if ch in ";,.()[]:":
                tokens.append(Token(ch, PONTUACAO, L, col))
                i += 1
                continue
            if ch in "+-*/=<>^@":
                tokens.append(Token(ch, OPERADOR, L, col))
                i += 1
                continue

            erros.append("Linha %d, coluna %d: caractere inválido '%s'" % (L, col, ch))
            i += 1

    if em_chave or em_paren:
        erros.append("Linha %d, coluna %d: comentário não foi fechado" % (coment_linha, coment_col))

    ultima = len(linhas) if linhas else 1
    tokens.append(Token("", FIM, ultima, 1))
    return tokens


# =====================================================================================
#  SINTÁTICO
# =====================================================================================

# O autômato de writeln/readln só aceita "writeln;". Em Pascal real também existe
# "writeln('texto');". Mude para True para aceitar também essa forma (usa o autômato read/write).
PERMITIR_ARGUMENTOS_EM_READLN_WRITELN = False

# Comandos "lineares": palavra + sequência fixa de símbolos/slots + ';'
#   "@tipo:nome" = slot (não terminal); qualquer outra coisa = símbolo literal
LINEARES = {
    "clreol": [], "clrscr": [], "exit": [], "halt": [], "keypressed": [],
    "maxavail": [], "memavail": [], "paramcount": [], "randomize": [],
    "readln": [], "wherex": [], "wherey": [], "writeln": [],

    "delay":    ["(", "@expr:tempo_ms", ")"],
    "paramstr": ["(", "@expr:indice_n", ")"],
    "sizeof":   ["(", "@vartipo:var_ou_tipo", ")"],
    "length":   ["(", "@expr:exp_string", ")"],
    "hi":       ["(", "@expr:exp_inteira", ")"],
    "lo":       ["(", "@expr:exp_inteira", ")"],
    "freemem":  ["(", "@var:ponteiro", ",", "@expr:tamanho", ")"],
    "getmem":   ["(", "@var:ponteiro", ",", "@expr:tamanho", ")"],
    "gotoxy":   ["(", "@expr:pos_x", ",", "@expr:pos_y", ")"],
    "fillchar": ["(", "@var:var", ",", "@expr:tamanho", ",", "@expr:valor", ")"],
    "move":     ["(", "@var:origem", ",", "@var:destino", ",", "@expr:tamanho", ")"],
    "inline":   ["(", "@expr:bytes_ou_opcodes", ")"],
    "goto":     ["@rotulo:identificador_ou_rotulo"],
}

# Palavras que podem aparecer dentro de expressões (funções internas)
FUNCOES_EXPR = {
    "keypressed", "maxavail", "memavail", "paramcount", "wherex", "wherey",
    "random", "sizeof", "length", "hi", "lo", "paramstr",
}

# Palavras que iniciam um comando (usado para se recuperar de erros)
INICIO_COMANDO = {"begin", "var", "if", "for", "while", "repeat", "random", "read", "write"} | set(LINEARES)


class ErroSintatico(Exception):
    def __init__(self, msg, linha, coluna):
        super().__init__(msg)
        self.msg = msg
        self.linha = linha
        self.coluna = coluna


class Cmd:
    """Registro de um comando reconhecido: guarda o caminho percorrido no autômato."""

    def __init__(self, nome, final, linha, profundidade):
        self.nome = nome
        self.final = final            # estado final do autômato (o que vem depois do ';')
        self.linha = linha
        self.profundidade = profundidade
        self.fechado = False          # o ';' (ou '.') final já foi consumido
        self.completo = False         # o comando foi lido até o fim sem erro
        self.falhou = False           # um erro ocorreu neste autômato
        self.estados = [0]

    def fechar(self):
        if self.fechado:
            return
        self.estados.append(self.final)
        self.fechado = True

    def caminho(self):
        return " -> ".join("S%d" % e for e in self.estados)


class Parser:
    """
    Analisador descendente recursivo. Cada método corresponde a um autômato do diagrama
    e cada chamada a go / go_kw / go_slot corresponde a uma transição Sx -> Sy.
    """

    def __init__(self, tokens):
        self.t = tokens          # o último token é sempre FIM
        self.p = 0
        self.profundidade = 0
        self.ctx = None          # comando (autômato) em andamento, usado nas mensagens de erro
        self.slot = None         # nome do slot em andamento, ex.: "tempo_ms"
        self.erros = []
        self.comandos = []

    # ------------------------------------------------------------------ utilidades

    @property
    def peek(self):
        return self.t[self.p]

    def peek_n(self, n):
        return self.t[min(self.p + n, len(self.t) - 1)]

    @staticmethod
    def eh(tok, v):
        return tok.tipo != FIM and tok.lower == v

    def is_(self, v):
        return self.eh(self.peek, v)

    @property
    def eh_fim(self):
        return self.peek.tipo == FIM

    def novo(self, nome, final):
        c = Cmd(nome, final, self.peek.linha, self.profundidade)
        self.comandos.append(c)
        return c

    @staticmethod
    def desc(tok):
        if tok.tipo == FIM:
            return "o fim do código"
        return "'%s' (%s)" % (tok.valor, DESCRICAO_CLASSE.get(tok.tipo, "símbolo"))

    @staticmethod
    def erro_msg(tok, msg):
        return ErroSintatico(msg, tok.linha, tok.coluna)

    def erro(self, c, esperado, tok):
        """Monta o erro "esperado X, mas encontrado Y" para o token atual."""
        prefixo = ""
        if c is not None:
            c.falhou = True
            prefixo = "[%s | S%d] " % (c.nome, c.estados[-1])

        linha, col, extra = tok.linha, tok.coluna, ""
        ant = self.t[self.p - 1] if self.p > 0 else None
        if ant is not None and (tok.tipo == FIM or ant.linha < tok.linha):
            # o que faltou deveria estar no fim da linha anterior
            linha = ant.linha
            col = ant.coluna + len(ant.valor)
            if tok.tipo != FIM:
                extra = " (na linha %d)" % tok.linha

        return ErroSintatico(
            "%sesperado %s, mas encontrado %s%s" % (prefixo, esperado, self.desc(tok), extra),
            linha, col)

    # ------------------------------------------------------------------ transições

    def go(self, c, to, esperado, ok):
        """Transição por um token que satisfaz 'ok'. Vai para o estado 'to'."""
        tk = self.peek
        if not ok(tk):
            raise self.erro(c, esperado, tk)
        self.p += 1
        c.estados.append(to)
        return tk

    def go_kw(self, c, to, kw, esperado=None):
        """Transição por uma palavra/símbolo exato."""
        self.go(c, to, esperado or "'%s'" % kw, lambda k: self.eh(k, kw))

    def go_slot(self, c, to, nome_slot, analisar):
        """Transição por um não terminal (expressão, variável, comando...)."""
        self.ctx = c
        self.slot = nome_slot
        analisar()
        c.estados.append(to)

    def corpo(self, c, to, nome_slot):
        """Transição por um comando aninhado (corpo de if/for/while)."""
        self.ctx = c
        self.slot = nome_slot
        self.profundidade += 1
        try:
            self.parse_statement()
        finally:
            self.profundidade -= 1
        c.estados.append(to)

    def terminar(self, c, permite_ponto):
        if self.is_(";"):
            self.p += 1
            c.fechar()
            return False
        if permite_ponto and self.is_("."):
            self.p += 1
            c.fechar()
            return True
        raise self.erro(c, "';' ou '.'" if permite_ponto else "';'", self.peek)

    # ------------------------------------------------------------------ programa

    def analisar(self):
        while not self.eh_fim:
            inicio = self.p
            self.ctx = self.slot = None
            self.profundidade = 0
            try:
                c = self.parse_statement()
                if not c.fechado:
                    ponto = self.terminar(c, c.nome == "begin")
                    if ponto:
                        if not self.eh_fim:
                            self.reportar(self.erro_msg(
                                self.peek, "código encontrado depois do '.' que encerra o programa"))
                        break
            except ErroSintatico as e:
                self.reportar(e)
                self.sincronizar(inicio)

    def reportar(self, e):
        m = "Linha %d, coluna %d: %s" % (e.linha, e.coluna, e.msg)
        if m not in self.erros:
            self.erros.append(m)

    def sincronizar(self, inicio):
        """Recuperação de erro: pula até o próximo ';', 'end'/'until' ou início de comando em nova linha."""
        while not self.eh_fim:
            if self.is_(";"):
                self.p += 1
                break
            if self.is_("end") or self.is_("until"):
                break
            if (self.p > inicio and self.peek.linha > self.t[self.p - 1].linha
                    and self.peek.tipo == RESERVADO and self.peek.lower in INICIO_COMANDO):
                break
            self.p += 1
        if self.p == inicio and not self.eh_fim:
            self.p += 1   # garante progresso

    # ------------------------------------------------------------------ comandos

    def parse_statement(self):
        c = self.despachar()
        c.completo = True
        return c

    def despachar(self):
        tk = self.peek
        ctx0, slot0 = self.ctx, self.slot

        if tk.tipo == VARIAVEL:
            nx = self.peek_n(1)
            if self.eh(nx, ":"):
                return self.rotulo()
            if any(self.eh(nx, s) for s in (":=", "[", "^", ".")):
                return self.atribuicao()
            raise self.erro_msg(
                tk, "comando desconhecido: '%s' não é um comando reservado nem o início de uma "
                    "atribuição (variável := expressão)" % tk.valor)

        if tk.tipo == RESERVADO:
            k = tk.lower
            if k == "begin":
                return self.parse_begin()
            if k == "var":
                if self.profundidade > 0:
                    raise self.erro_msg(tk, "'var' só pode ser usado fora de blocos (antes do 'begin' principal)")
                return self.parse_var()
            if k == "if":
                return self.parse_if()
            if k == "for":
                return self.parse_for()
            if k == "while":
                return self.parse_while()
            if k == "repeat":
                return self.parse_repeat()
            if k == "random":
                return self.parse_random()
            if k in ("read", "write"):
                return self.parse_read_write(k)
            if k in ("readln", "writeln") and PERMITIR_ARGUMENTOS_EM_READLN_WRITELN \
                    and self.eh(self.peek_n(1), "("):
                return self.parse_read_write(k)
            if k in LINEARES:
                return self.linear(k)

        if tk.tipo == RESERVADO and tk.lower in ("end", "until"):
            raise self.erro_msg(
                tk, "'%s' inesperado: não há 'begin'/'repeat' aberto para ser fechado aqui" % tk.valor)

        esp = "[%s] (um comando válido)" % slot0 if slot0 else "um comando válido"
        raise self.erro(ctx0, esp, tk)

    # begin [instruções] end
    def parse_begin(self):
        c = self.novo("begin", 4)
        self.go_kw(c, 1, "begin")
        self.bloco(c, "end")
        self.go_kw(c, 3, "end")
        return c

    def bloco(self, c, fim):
        """Lista de instruções separadas por ';' até a palavra 'fim' (end / until).
           S1 -[instruções]-> S2 ; S2 -';'-> S1 ; S2 -fim-> S3 ; S1 -fim-> S3 (bloco vazio)"""
        self.profundidade += 1
        try:
            while True:
                if self.is_(fim):
                    return
                if self.eh_fim:
                    raise self.erro(c, "'%s' (o '%s' da linha %d não foi fechado)" % (fim, c.nome, c.linha), self.peek)

                inicio = self.p
                try:
                    self.ctx, self.slot = c, "instrucoes"
                    interno = self.parse_statement()
                    c.estados.append(2)
                    if self.is_(";"):
                        self.p += 1
                        c.estados.append(1)
                        interno.fechar()
                    elif not self.is_(fim):
                        raise self.erro(c, "';' ou '%s'" % fim, self.peek)
                except ErroSintatico as e:
                    self.reportar(e)
                    self.sincronizar(inicio)
        finally:
            self.profundidade -= 1

    # var id {, id} : tipo ; (repete para mais declarações)
    def parse_var(self):
        c = self.novo("var", 5)
        self.go_kw(c, 1, "var")
        while True:
            while True:
                self.go(c, 2, "[identificador]", lambda k: k.tipo == VARIAVEL)
                if self.is_(","):
                    self.go_kw(c, 1, ",")
                    continue
                break
            self.go_kw(c, 3, ":", "',' ou ':'")
            self.go_slot(c, 4, "tipo", self.tipo)
            self.go_kw(c, 5, ";")
            c.fechado = True

            if self.peek.tipo == VARIAVEL:      # S5 -> S1
                c.estados.append(1)
                continue
            break
        return c

    # if [condicao] then [comando_1] ( ; | else [comando_2] ; )
    def parse_if(self):
        c = self.novo("if", 7)
        self.go_kw(c, 1, "if")
        self.go_slot(c, 2, "condicao", self.expr)
        self.go_kw(c, 3, "then")
        self.corpo(c, 4, "comando_1")
        if self.is_("else"):
            self.go_kw(c, 5, "else")
            self.corpo(c, 6, "comando_2")
        return c

    # for var_ctrl := exp_ini (to|downto) exp_fim do comando ;
    def parse_for(self):
        c = self.novo("for", 9)
        self.go_kw(c, 1, "for")
        self.go_slot(c, 2, "var_ctrl", lambda: self.slot_tipo("id"))
        self.go_kw(c, 3, ":=")
        self.go_slot(c, 4, "exp_ini", self.expr)
        self.go(c, 5, "'to' ou 'downto'", lambda k: self.eh(k, "to") or self.eh(k, "downto"))
        self.go_slot(c, 6, "exp_fim", self.expr)
        self.go_kw(c, 7, "do")
        self.corpo(c, 8, "comando")
        return c

    # while cond_bool do comando ;
    def parse_while(self):
        c = self.novo("while", 5)
        self.go_kw(c, 1, "while")
        self.go_slot(c, 2, "cond_bool", self.expr)
        self.go_kw(c, 3, "do")
        self.corpo(c, 4, "comando")
        return c

    # repeat [instrucao {; instrucao}] until condicao ;
    def parse_repeat(self):
        c = self.novo("repeat", 5)
        self.go_kw(c, 1, "repeat")
        self.bloco(c, "until")
        self.go_kw(c, 3, "until")
        self.go_slot(c, 4, "condicao", self.expr)
        return c

    # random | random ( limite )     -> S1 pode ir direto para S4
    def parse_random(self):
        c = self.novo("random", 5)
        self.go_kw(c, 1, "random")
        if self.is_("("):
            self.go_kw(c, 2, "(")
            self.go_slot(c, 3, "limite", self.expr)
            self.go_kw(c, 4, ")")
        else:
            c.estados.append(4)
        return c

    # read/write ( var|exp {, var|exp} )   e   read ( kbd , var_char )
    def parse_read_write(self, nome):
        leitura = nome in ("read", "readln")
        c = self.novo(nome, 5)
        self.go_kw(c, 1, nome)
        self.go_kw(c, 2, "(")

        if nome == "read" and self.is_("kbd"):
            c.final = 7
            self.go_kw(c, 3, "kbd")
            self.go_kw(c, 4, ",")
            self.go_slot(c, 5, "var_char", lambda: self.slot_tipo("var"))
            self.go_kw(c, 6, ")")
            return c

        while True:
            if leitura:
                self.go_slot(c, 3, "var", lambda: self.slot_tipo("var"))
            else:
                self.go_slot(c, 3, "exp", self.expr)
            if self.is_(","):
                self.go_kw(c, 2, ",")
                continue
            break
        self.go_kw(c, 4, ")", "',' ou ')'")
        return c

    # comandos lineares descritos na tabela LINEARES
    def linear(self, nome):
        spec = LINEARES[nome]
        c = self.novo(nome, len(spec) + 2)
        self.go_kw(c, 1, nome)
        estado = 2
        for item in spec:
            if item[0] == "@":
                tipo_slot, nome_slot = item[1:].split(":")
                self.go_slot(c, estado, nome_slot, lambda ts=tipo_slot: self.slot_tipo(ts))
            else:
                self.go_kw(c, estado, item)
            estado += 1
        return c

    # rotulo : comando
    def rotulo(self):
        c = self.novo("rótulo", 2)
        self.go(c, 1, "[identificador]", lambda k: k.tipo == VARIAVEL)
        self.go_kw(c, 2, ":")
        c.completo = True
        c.fechado = True
        self.ctx, self.slot = c, "comando"
        return self.parse_statement()

    # variavel := expressao   (não está no diagrama, mas é necessária dentro de blocos e do 'for')
    def atribuicao(self):
        c = self.novo("atribuição", 4)
        self.go_slot(c, 1, "variavel", lambda: self.slot_tipo("var"))
        self.go_kw(c, 2, ":=")
        self.go_slot(c, 3, "expressao", self.expr)
        return c

    # ------------------------------------------------------------------ slots

    def slot_tipo(self, tipo):
        tk = self.peek
        if tipo == "expr":
            self.expr()
        elif tipo == "var":
            self.variavel()
        elif tipo == "id":
            if tk.tipo != VARIAVEL:
                raise self.erro(self.ctx, "[%s] (identificador)" % self.slot, tk)
            self.p += 1
        elif tipo == "vartipo":
            if tk.tipo == TIPO:
                self.p += 1
            else:
                self.variavel()
        elif tipo == "rotulo":
            if tk.tipo not in (VARIAVEL, NUMERO):
                raise self.erro(self.ctx, "[%s] (identificador ou número do rótulo)" % self.slot, tk)
            self.p += 1

    def variavel(self):
        """identificador com seletores opcionais: a[i], p^, r.campo"""
        tk = self.peek
        if tk.tipo != VARIAVEL:
            raise self.erro(self.ctx, "[%s] (identificador de variável)" % self.slot, tk)
        self.p += 1
        self.seletores()

    def seletores(self):
        while True:
            if self.is_("["):
                self.p += 1
                self.expr()
                while self.is_(","):
                    self.p += 1
                    self.expr()
                self.fecha("]")
            elif self.is_("^"):
                self.p += 1
            elif self.is_(".") and self.peek_n(1).tipo == VARIAVEL:
                self.p += 2
            else:
                break

    def fecha(self, s):
        if not self.is_(s):
            raise self.erro(self.ctx, "'%s'" % s, self.peek)
        self.p += 1

    def tipo(self):
        """tipo: integer | string[n] | array [a..b] of tipo"""
        tk = self.peek
        if tk.tipo == TIPO:
            self.p += 1
            if tk.lower == "string" and self.is_("["):
                self.p += 1
                self.expr()
                self.fecha("]")
            return
        if self.is_("array"):
            self.p += 1
            self.fecha("[")
            self.expr()
            self.fecha("..")
            self.expr()
            self.fecha("]")
            if not self.is_("of"):
                raise self.erro(self.ctx, "'of'", self.peek)
            self.p += 1
            self.tipo()
            return
        raise self.erro(self.ctx, "[%s] (um tipo: integer, byte, real, char, string, boolean...)" % self.slot, tk)

    # ------------------------------------------------------------------ expressões

    def expr(self):
        """expr := simples [ (= | <> | < | > | <= | >=) simples ]"""
        self.simples()
        tk = self.peek
        if tk.tipo == OPERADOR and tk.lower in ("=", "<>", "<", ">", "<=", ">="):
            self.p += 1
            self.simples()

    def simples(self):
        """simples := [+|-] termo { (+|-|or|xor) termo }"""
        if self.is_("+") or self.is_("-"):
            self.p += 1
        self.termo()
        while self.is_("+") or self.is_("-") or self.is_("or") or self.is_("xor"):
            self.p += 1
            self.termo()

    def termo(self):
        """termo := fator { (*|/|div|mod|and|shl|shr) fator }"""
        self.fator()
        while any(self.is_(o) for o in ("*", "/", "div", "mod", "and", "shl", "shr")):
            self.p += 1
            self.fator()

    def fator(self):
        tk = self.peek
        if tk.tipo in (NUMERO, TEXTO):
            self.p += 1
            return
        if tk.tipo == VARIAVEL:
            if self.eh(self.peek_n(1), "("):
                raise self.erro_msg(tk, "'%s' não é uma função conhecida" % tk.valor)
            self.p += 1
            self.seletores()
            return
        if tk.tipo == RESERVADO:
            if tk.lower in ("true", "false", "nil"):
                self.p += 1
                return
            if tk.lower == "not":
                self.p += 1
                self.fator()
                return
            if tk.lower in FUNCOES_EXPR:
                self.funcao_expr()
                return
        elif tk.tipo == PONTUACAO and tk.lower == "(":
            self.p += 1
            self.expr()
            self.fecha(")")
            return
        elif tk.tipo == OPERADOR and tk.lower == "@":
            self.p += 1
            self.variavel()
            return

        raise self.erro(self.ctx, "[%s] (número, texto, variável, função ou '(')" % self.slot, tk)

    def funcao_expr(self):
        nome = self.peek.lower
        self.p += 1
        if nome == "random":
            if self.is_("("):
                self.p += 1
                self.expr()
                self.fecha(")")
        elif nome == "sizeof":
            self.abre_paren(nome)
            if self.peek.tipo == TIPO:
                self.p += 1
            else:
                self.variavel()
            self.fecha(")")
        elif nome in ("length", "hi", "lo", "paramstr"):
            self.abre_paren(nome)
            self.expr()
            self.fecha(")")
        # keypressed, maxavail, memavail, paramcount, wherex, wherey: sem argumentos

    def abre_paren(self, nome):
        if not self.is_("("):
            raise self.erro(self.ctx, "'(' depois de '%s'" % nome, self.peek)
        self.p += 1


# =====================================================================================
#  PROGRAMA PRINCIPAL
# =====================================================================================

def analisar(linhas):
    erros_lexicos = []
    tokens = tokenizar(linhas, erros_lexicos)

    # ---------- 1) tabela de tokens (análise léxica)
    print()
    print("--- valores lidos ---")
    for tk in tokens:
        if tk.tipo != FIM:
            print(tk)

    # ---------- 2) análise sintática (autômatos)
    parser = Parser(tokens)
    parser.analisar()

    print()
    print("--- comandos verificados no autômato ---")
    if not parser.comandos:
        print("(nenhum comando reconhecido)")
    for c in parser.comandos:
        ok = c.completo and not c.falhou
        recuo = " " * (c.profundidade * 3)
        print(("[OK]   " if ok else "[ERRO] ") + recuo + "linha %d  %s  %s%s" %
              (c.linha, c.nome, c.caminho(), "" if ok else "  (parou aqui)"))

    # ---------- 3) resultado
    todos = erros_lexicos + parser.erros
    print()
    if not todos:
        print("RESULTADO: código sintaticamente correto.")
    else:
        print("RESULTADO: %d erro(s) encontrado(s):" % len(todos))
        for e in todos:
            print("  - " + e)


def main():
    # garante acentos corretos no terminal do Windows
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # Modo arquivo:  python analisador.py meucodigo.pas
    if len(sys.argv) > 1:
        if not os.path.isfile(sys.argv[1]):
            print("arquivo não encontrado: " + sys.argv[1])
            return
        with open(sys.argv[1], encoding="utf-8-sig") as f:
            analisar(f.read().splitlines())
        return

    # Modo interativo
    print("=== Analisador léxico e sintático ===")
    print("Digite o código linha a linha (pode ser um comando por linha ou várias instruções).")
    print("Linha em branco = analisar. Linha em branco logo no início = encerrar o programa.")

    while True:
        linhas = []
        print()
        while True:
            try:
                valor = input("linha %d: " % (len(linhas) + 1))
            except EOFError:
                valor = ""
            if not valor.strip():
                break
            linhas.append(valor)

        if not linhas:
            break
        analisar(linhas)


if __name__ == "__main__":
    main()
