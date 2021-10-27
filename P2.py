from sly import Lexer
from sly import Parser

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class CLexer(Lexer):
    tokens = {EQUAL, LESSTHANEQUAL, GREATERTHANEQUAL, NOTEQUAL, LOGICAND, LOGICOR, ID, INTVALUE, FLOATVALUE,
              INT, VOID, RETURN}
    literals = {'=', '+', '-', '/', '*', '!', ';', ',', '(', ')', '{', '}', ','}

    # Tokens
    EQUAL = r'=='
    LESSTHANEQUAL = r'<='
    GREATERTHANEQUAL = r'>='
    NOTEQUAL = r'!='
    LOGICAND = r'&&'
    LOGICOR = r'\|\|'
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    FLOATVALUE = r'[0-9]+[.][0-9]+[f]?'
    INTVALUE = r'[0-9]+[f]?'

    ignore_space = r' '
    ignore_tabs = r'\t'
    ignore_comments = r'//.*'

    # Reserved keywords
    ID['int'] = INT
    ID['void'] = VOID
    ID['return'] = RETURN

    # Error and Indexing management
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    # Error handling rule
    def error(self, t):
        print("Illegal character '%s'" % t.value[0])
        self.index += 1


class CParser(Parser):
    tokens = CLexer.tokens
    start = 'sentence'

    symbolValue = {}
    functions = {}

    # Program structure
    @_('instruction sentence')
    def sentence(self, p):
        return p[0]

    @_('')
    def sentence(self, p):
        return

    # Assignations and basic instruction structure
    @_('type declaration ";"',
       'type declaration "," anotherDeclaration')
    def instruction(self, p):
        return p[1]

    @_('assignment ";"')
    def instruction(self, p):
        return p[0]

    @_('ID "=" assignment')
    def declaration(self, p):
        if p[0] in self.symbolValue:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + 'Redeclaration of variable ' + p[0] + ' is not allowed')
        else:
            self.symbolValue[p[0]] = p[2]
        return p[0]

    @_('ID')
    def declaration(self, p):
        if p[0] in self.symbolValue:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + 'Redeclaration of variable ' + p[0] + ' is not allowed')
        else:
            self.symbolValue[p[0]] = 0
        return p[0]

    @_('declaration "," anotherDeclaration',
       'declaration ";"')
    def anotherDeclaration(self, p):
        return p[0]

    @_('ID "=" assignment')
    def assignment(self, p):
        if p[0] in self.symbolValue:
            self.symbolValue[p[0]] = p[2]
            return self.symbolValue[p[0]]
        else:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a declared Variable')

    @_('expr')
    def assignment(self, p):
        return p[0]

    # Functions
    @_('type ID',
       'VOID ID')
    def param(self, p):
        if p[1] in self.symbolValue:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + 'Redeclaration of variable ' + p[1] + ' is not allowed')
        else:
            self.symbolValue[p[1]] = 0
        return p[1]

    @_('param "," params',
       'param')
    def params(self, p):
        return 0

    @_('type "," typeDec',
       'type')
    def typeDec(self, p):
        return 0

    @_('expr "," callParams',
       'expr')
    def callParams(self, p):
        return 0

    @_('ID "(" callParams ")"',
       'ID "(" ")"')
    def num(self, p):
        if p[0] in self.functions:
            pass
        else:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a Function')
        return 0

    @_('RETURN expr ";"')
    def retInstruction(self, p):
        return

    @_('type ID  "(" params ")"',
       'type ID "(" typeDec ")"',
       'type ID "(" ")"')
    def functionDecl(self, p):
        return p[1]

    @_('VOID ID  "(" params ")"',
       'VOID ID "(" typeDec ")"',
       'VOID ID "(" ")"')
    def voidFunctionDecl(self, p):
        return p[1]

    @_('functionDecl ";"',
       'voidFunctionDecl ";"')
    def instruction(self, p):
        if p[0] in self.functions:
            raise RuntimeError('line ' + str(p.lineno) + ': Redeclaration of function ' + p[0] + ' is not allowed')
        else:
            if p[0] in self.symbolValue:
                raise RuntimeError('line ' + str(p.lineno) + ': ' +p[0] + ' is already declared as a variable')
            else:
                self.functions[p[0]] = 0
        return 0

    @_('functionDecl "{"',
       'voidFunctionDecl "{"')
    def functDefInit(self, p):
        self.functions[p[0]] = 0
        return 0

    @_('functDefInit sentence retInstruction "}"')
    def instruction(self, p):
        return 0

    @_('functDefInit sentence "}"')
    def instruction(self, p):
        return 0

    # Logical operators
    @_('logicalOR LOGICOR logicalAND')
    def logicalOR(self, p):
        return bool(p[0] or p[2])

    @_('logicalAND LOGICAND comparison')
    def logicalAND(self, p):
        return bool(p[0] and p[2])

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

    # Arithmetic operators
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
        return int(p[0] / p[2])

    @_('term "%" fact')
    def term(self, p):
        return p[0] % p[2]

    # Unary operators

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

    # Conversion hierarchy
    # PlaceHolder type function for scalability with more types
    @_('INT')
    def type(self, p):
        return p[0]

    @_('INTVALUE',
       'FLOATVALUE')
    def num(self, p):
        return int(float(p[0].replace('f', '')))

    @_('ID')
    def num(self, p):
        if p[0] in self.symbolValue:
            return self.symbolValue[p[0]]
        else:
            if p[0] in self.functions:
                raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' must be called as a Function')
            else:
                raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a declared Symbol')

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
    def logicalAND(self, p):
        return p[0]

    @_('logicalAND')
    def logicalOR(self, p):
        return p[0]

    @_('logicalOR')
    def expr(self, p):
        return p[0]

    # Simple error management
    def error(self, p):
        if p:
            print(bcolors.BOLD, bcolors.OKCYAN, "Syntax error at token", p.type, ", line: ", p.lineno)
            # Just discard the token and tell the parser it's okay.
            # self.errok()
        else:
            print("Syntax error at EOF")


if __name__ == '__main__':
    lexer = CLexer()
    parser = CParser()

    text = open("Source2.c").read()
    tokenizedText = lexer.tokenize(text)
    print("\n =========[ Lexer ] ===========")
    for token in tokenizedText:
        print("token:", token.type, ", lexvalue:", token.value)

    print("\n =========[ Parser ] ===========")
    try:
        parser.parse(lexer.tokenize(text))
    except RuntimeError as e:
        print(bcolors.BOLD, bcolors.OKCYAN, e)
