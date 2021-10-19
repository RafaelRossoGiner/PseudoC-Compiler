from sly import Lexer
from sly import Parser


class CLexer(Lexer):
    tokens = {EQUAL, LESSTHANEQUAL, GREATERTHANEQUAL, NOTEQUAL, LOGICAND, LOGICOR, ID, INTVALUE, FLOATVALUE,
              INT, VOID}
    literals = {'=', '+', '-', '/', '*', '!', ';', ',', '(', ')', '{', '}'}

    # Tokens
    EQUAL = r'=='
    LESSTHANEQUAL = r'<='
    GREATERTHANEQUAL = r'>='
    NOTEQUAL = r'!='
    LOGICAND = r'&&'
    LOGICOR = r'\|\|'
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    INTVALUE = r'[0-9]+'
    FLOATVALUE = r'[0-9]+.[0-9]+'

    ignore_space = ' '
    ignore_newline = r'\n'
    # Reserved keywords
    ID['int'] = INT
    ID['void'] = VOID


class CParser(Parser):
    tokens = CLexer.tokens


    symbolValue = {}

    # Structure
    @_('instruction sentence',
       '')
    def sentence(self, p):
        return

    @_('type ID "=" assignment ";"')
    def instruction(self, p):
        if p[1] in self.symbolValue:
            raise RuntimeError('Redeclaration of variable ' + p[1] + ' is not allowed')
        else:
            self.symbolValue[p[1]] = p[3]
        return

    @_('type ID ";"')
    def instruction(self, p):
        if p[1] in self.symbolValue:
            raise RuntimeError('Redeclaration of variable ' + p[1] + ' is not allowed')
        else:
            self.symbolValue[p[1]] = 0
        return

    @_('assignment ";"')
    def instruction(self, p):
        return

    @_('ID "=" assignment')
    def assignment(self, p):
        if p[0] in self.symbolValue:
            self.symbolValue[p[0]] = p[2]
        else:
            raise RuntimeError('Variable ' + p[0] + ' is not declared')
        return

    @_('expr')
    def assignment(self, p):
        return

    # Functions
    @_('type ID',
       '')
    def param(self, p):
        return

    @_('param "," params',
      '')
    def params(self, p):
        return

    @_('ID "(" params ")"')
    def function(self, p):
        return

    @_('type function')
    def functionHeader(self, p):
        return

    @_('functionHeader ";"')
    def instruction(self, p):
        return

    @_('functionHeader "{" sentence "}"')
    def instruction(self, p):
        return

    # Logical Operators
    @_('logical LOGICOR comparison')
    def logical(self, p):
        return p[0] or p[2]

    @_('logical LOGICAND comparison')
    def logical(self, p):
        return p[0] and p[2]

    @_('comparison EQUAL relation')
    def comparison(self, p):
        return p[0] == p[2]

    @_('comparison NOTEQUAL relation')
    def comparison(self, p):
        return p[0] != p[2]

    @_('relation "<" arithExpr')
    def relation(self, p):
        return p[0] < p[2]

    @_('relation LESSTHANEQUAL arithExpr')
    def relation(self, p):
        return p[0] <= p[2]

    @_('relation ">" arithExpr')
    def relation(self, p):
        return p[0] > p[2]

    @_('relation GREATERTHANEQUAL arithExpr')
    def relation(self, p):
        return p[0] >= p[2]

    # Arithmetic
    @_('arithExpr "+" term')
    def arithExpr(self, p):
        return p[0] + p[2]

    @_('arithExpr "-" term')
    def arithExpr(self, p):
        return p[0] - p[2]

    @_('term "*" fact')
    def term(self, p):
        return p[0] * p[2]

    @_('term "/" fact')
    def term(self, p):
        return p[0] / p[2]

    @_('term "%" fact')
    def term(self, p):
        return p[0] % p[2]

    # Unary Operators

    @_('"!" unary')
    def unary(self, p):
        return not p[1]

    @_('"-" unary')
    def num(self, p):
        return - p[1]

    # Parenthesis
    @_('"(" expr ")"')
    def num(self, p):
        return p[1]

    # Conversion Hierarchy
    @_('INT',
       'VOID',)
    def type(self, p):
        return p[0]

    @_('INTVALUE',
       'FLOATVALUE')
    def num(self, p):
        return int(p[0])

    @_('num')
    def unary(self, p):
        return p[0]

    @_('unary')
    def fact(self, p):
        return p[0]

    @_('fact')
    def term(self, p):
        return p[0]

    @_('term')
    def arithExpr(self, p):
        return p[0]

    @_('arithExpr')
    def relation(self, p):
        return p[0]

    @_('relation')
    def comparison(self, p):
        return p[0]

    @_('comparison')
    def logical(self, p):
        return p[0]

    @_('logical')
    def expr(self, p):
        return p[0]


if __name__ == '__main__':
    lexer = CLexer()
    parser = CParser()

    text = open("Source.c").read()
    tokenizedText = lexer.tokenize(text)
    for token in tokenizedText:
        print(token)
    parser.parse(lexer.tokenize(text))
