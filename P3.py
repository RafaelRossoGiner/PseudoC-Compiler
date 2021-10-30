from sly import Lexer

global tabla
global ta
global ind
global tokens
global tokenlist


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


class BOOLLexer(Lexer):
    tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    literals = {';', '(', ')'}

    # Tokens
    ASSIGN = ':='
    AND = r'and|AND'
    OR = r'or|OR'
    NOT = r'not|NOT'

    @_(r'true|TRUE|false|FALSE')
    def BOOLVAL(self, t):
        t.value = t.value.lower() == 'true'
        return t

    # Reserved keywords
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    ID['print'] = PRINT

    # Ignores
    ignore_space = r' '
    ignore_tabs = r'\t'
    ignore_comments = r'//.*'

    # Error and Indexing management
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    # Error handling rule
    def error(self, t):
        print("Illegal character '%s'" % t.value[0])
        self.index += 1

def yyerror(msj):
    global ta
    print("Error sintactico", msj, "linea", ta.lineno)


# fin de yyerror()

def cuadra(obj):
    global ta, ind, tokenlist
    if ta.type == obj:
        # print("cuadro ta = ", ta.value)
        ind += 1
        if ind < len(tokenlist):
            ta = tokenlist[ind]
            # print("==> nuevo ta = ", ta.value)
    else:
        yyerror("en cuadra");


# fin de cuadra()

def sentence():
    global ta, tokens
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    # tokens = {AND, ASSIGN, BOOLVAL, ID, NOT, OR, PRINT}
    if ta.type == 'PRINT' or ta.type == 'ID':
        instruction()
        sentence()
    else:
        if ind < len(tokenlist):
            yyerror("en sentence")


def instruction():
    global ta, tokens, tabla
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    if ta.type == 'PRINT':
        cuadra('PRINT')
        print("Resultado es", expr())
        cuadra(';')
    elif ta.type == 'ID':
        IDlexval = ta.value
        cuadra('ID')
        cuadra('ASSIGN')
        tabla[IDlexval] = expr()
        cuadra(';')
    else:
        yyerror("en instruction")

def unary():
    global ta, tokens
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    # tokens = {AND, ASSIGN, BOOLVAL, ID, NOT, OR, PRINT}
    if ta.type == 'NOT':
        cuadra('NOT')
        return not unary()
    elif ta.type == 'BOOLVAL' or ta.type == 'ID' or ta.type == '(':
        return bool()
    else:
        yyerror("en unary")


def logicalANDPrima():
    global ta, tokens
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    if ta.type == 'AND':
        cuadra('AND')
        logicVal = unary()
        logicVal1 = logicalORPrima()
        if logicVal1 is None:
            return logicVal
        else:
            return logicVal or logicVal1


def logicalORPrima():
    global ta, tokens
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    # tokens = {AND, ASSIGN, BOOLVAL, ID, NOT, OR, PRINT}
    if ta.type == 'OR':
        cuadra('OR')
        logicVal = logicalAND()
        logicVal1 = logicalORPrima()
        if logicVal1 is None:
            return logicVal
        else:
            return logicVal or logicVal1


def logicalAND():
    global ta, tokens
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    if ta.type == 'NOT' or ta.type == 'ID' or ta.type == 'BOOLVAL' or ta.type == '(':
        logicVal = unary()
        logicVal1 = logicalANDPrima()
        if logicVal1 is None:
            return logicVal
        else:
            return logicVal and logicVal1
    else:
        yyerror("en logicalAND")


def logicalOR():
    global ta, tokens
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    if ta.type == 'NOT' or ta.type == 'ID' or ta.type == 'BOOLVAL' or ta.type == '(':
        logicVal = logicalAND()
        logicVal1 = logicalORPrima()
        if logicVal1 is None:
            return logicVal
        else:
            return logicVal or logicVal1
    else:
        yyerror("en logicalOR")


def expr():
    global ta, tokens, ind
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    # tokens = {AND, ASSIGN, BOOLVAL, ID, NOT, OR, PRINT}
    if ta.type == 'NOT' or ta.type == 'ID' or ta.type == 'BOOLVAL' or ta.type == '(':
        return logicalOR()
    else:
        if ta.type != ';':
            yyerror("en expr")


def bool():
    global ta, tokens, tabla
    # tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    # tokens = {AND, ASSIGN, BOOLVAL, ID, NOT, OR, PRINT}
    if ta.type == '(':
        cuadra('(')
        s = expr()
        cuadra(')')
        return s
    elif ta.type == 'BOOLVAL':
        s = ta.value
        cuadra('BOOLVAL')
        return s
    elif ta.type == 'ID':
        IDlexval = ta.value
        cuadra('ID')
        return tabla[IDlexval]
    else:
        yyerror("en bool")


# fin de tipo()

if __name__ == '__main__':
    global ta, tokens, ind, tabla
    ind = 0
    tabla = {}
    lexer = BOOLLexer()
    tokens = BOOLLexer.tokens
    tokens = sorted(tokens)
    data = open("Source3.txt").read()
    tokenlist = list(lexer.tokenize(data))
    print(tokenlist)
    ta = tokenlist[ind]
    sentence()
    ind = 0
