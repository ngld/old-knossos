import re
from collections import deque

WHITE_RE = re.compile(r'\s')
IDENT_RE = re.compile(r'[a-z0-9_-]+')


def tokenize(data):
    stack = deque()
    context = deque()

    data = WHITE_RE.sub('', data)
    pos = 0
    dlen = len(data)
    while pos < dlen:
        if data[pos] == '(':
            stack.append(context)
            context = deque()
            pos += 1
        elif data[pos] == ')':
            if not stack:
                raise Exception('Unbalanced parens!')

            parctx = stack.pop()
            parctx.append(('tsub', context))
            context = parctx
            pos += 1
        elif data[pos] == '!':
            context.append(('tnot',))
            pos += 1
        elif data[pos:pos + 2] == '&&':
            context.append(('tand',))
            pos += 2
        elif data[pos:pos + 2] == '||':
            context.append(('tor',))
            pos += 2
        else:
            ident = IDENT_RE.match(data[pos:])
            if not ident:
                raise Exception('Expected identifier, found "%s"!' % data[pos:])

            iname = ident.group(0)
            context.append(('ident', iname))
            pos += len(iname)

    assert len(stack) == 0, 'Unbalanced parens!'
    return context


def parse(stack):
    queue = None

    try:
        changed = True
        while changed:
            changed = False
            queue = stack
            stack = deque()

            while queue:
                el = queue.popleft()
                if el[0] == 'tsub':
                    stack.append(parse(el[1]))
                    changed = True
                    continue

                if queue and queue[0][0][0] != 't':
                    if el[0] == 'tnot':
                        stack.append(('not', queue.popleft()))
                        changed = True
                        continue

                    if stack and stack[-1][0][0] != 't':
                        if el[0] == 'tand':
                            a = stack.pop()
                            b = queue.pop()
                            stack.append(('and', a, b))
                            changed = True
                            continue
                        elif el[0] == 'tor':
                            a = stack.pop()
                            b = queue.pop()
                            stack.append(('or', a, b))
                            changed = True
                            continue

                stack.append(el)
    except Exception:
        print('stack', stack)
        print('queue', queue)
        raise

    assert len(stack) == 1, 'Unprocessed tokens! (%r)' % stack
    return stack[0]


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
    return eval_expr(parse(tokenize(data)), values)


if __name__ == '__main__':
    src = '!(a || !b) || (!z)'
    values = {'a': True, 'z': True}

    for i in range(1000):
        print(eval_string(src, values))
