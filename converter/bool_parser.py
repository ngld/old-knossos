## Copyright 2014 Knossos authors, see NOTICE file
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

import os
from ply import lex, yacc


class Lexer(object):
    tokens = ('ID', 'AND', 'OR', 'NEGATE', 'LPAREN', 'RPAREN')

    t_ID = r'[a-zA-Z0-9\_]+'
    t_AND = '&&'
    t_OR = r'\|\|'
    t_NEGATE = '!'
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    
    t_ignore = ' \r\t\n'

    def t_error(self, t):
        raise SyntaxError('Unexpected token! (%s)' % t.value)


class Parser(object):
    _lexer = None
    _parser = None

    def __init__(self):
        path = os.path.dirname(__file__)
        self._lexer = lex.lex(module=Lexer(), optimize=1, lextab='converter.bool_lextab', outputdir=path)
        self._parser = yacc.yacc(module=self, debug=0, tabmodule='converter.bool_parsetab', outputdir=path)

    tokens = Lexer.tokens
    precedence = (
        ('left', 'AND', 'OR'),
        ('right', 'NEGATE')
    )
    start = 'expression'

    def p_expr_bin(self, p):
        """
        expression : expression AND expression
                   | expression OR expression
        """

        p[0] = (p.slice[2].type.lower(), p[1], p[3])

    def p_expr_neg(self, p):
        "expression : NEGATE expression"

        p[0] = ('not', p[2])

    def p_expr_parens(self, p):
        "expression : LPAREN expression RPAREN"

        p[0] = p[2]

    def p_expr_id(self, p):
        "expression : ID"

        p[0] = ('var', p[1])

    def p_error(self, p):
        raise SyntaxError('Unexpected token! (%s)' % (p))

    def parse(self, data):
        self._lexer.input(data)
        return self._parser.parse(lexer=self._lexer)


_p = Parser()
parse = _p.parse


def solve(expr, vars):
    if expr[0] == 'var':
        return vars.get(expr[1])
    elif expr[0] == 'not':
        return not solve(expr[1], vars)
    elif expr[0] == 'and':
        return solve(expr[1], vars) and solve(expr[2], vars)
    elif expr[0] == 'or':
        return solve(expr[1], vars) or solve(expr[2], vars)
    else:
        raise Exception('Unknown operation %s! (%s)' % (expr[0], expr))
