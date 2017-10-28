from ply import lex, yacc

tokens = ('LPARENS', 'RPARENS', 'AND', 'OR', 'NOT', 'VAR')

t_LPARENS = r'\('
t_RPARENS = r'\)'
t_AND = r'&&'
t_OR = r'\|\|'
t_NOT = r'!'
t_VAR = '[a-zA-Z_0-9]+'

t_ignore = ' \t\n\r'


def t_error(t):
    raise Exception('Invalid character %s!' % t.value[0])


precedence = (
    ('left', 'AND', 'OR'),
    ('right', 'NOT')
)


def p_expr_var(t):
    'expr : VAR'
    t[0] = ('ident', t[1])


def p_expr_parens(t):
    'expr : LPARENS expr RPARENS'
    t[0] = t[2]


def p_expr_not(t):
    'expr : NOT expr'
    t[0] = ('not', t[2])


def p_expr_op(t):
    """expr : expr AND expr
            | expr OR  expr"""

    t[0] = ('and' if t[2] == '&&' else 'or', t[1], t[3])


lexer = lex.lex()
parser = yacc.yacc()


def eval_expr(expr, values):
    if expr[0] == 'ident':
        return values.get(expr[1], False)
    elif expr[0] == 'not':
        return not eval_expr(expr[1], values)
    elif expr[0] == 'and':
        return eval_expr(expr[1], values) and eval_expr(expr[2], values)
    elif expr[0] == 'or':
        return eval_expr(expr[1], values) or eval_expr(expr[2], values)
    else:
        raise Exception('Invalid operation "%s" encountered!' % expr[0])


def eval_string(data, values):
    return eval_expr(parser.parse(data), values)


if __name__ == '__main__':
    import sys
    import json
    print(eval_string(sys.argv[1], json.loads(sys.argv[2])))
