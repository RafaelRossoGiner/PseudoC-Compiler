from sly import Lexer
from sly import Parser

global symbolValue


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
#

class CLexer(Lexer):
    tokens = {EQUAL, LESSTHANEQUAL, GREATERTHANEQUAL, NOTEQUAL, LOGICAND, LOGICOR, ID, INTVALUE, FLOATVALUE,
              INT, VOID, IF, ELSE, RETURN, PRINTF, SCANF, STRING}
    literals = {'=', '+', '-', '/', '*', '!', ';', ',', '(', ')', '{', '}', ',', '"', '&'}

    # Tokens

    EQUAL = r'=='
    LESSTHANEQUAL = r'<='
    GREATERTHANEQUAL = r'>='
    NOTEQUAL = r'!='
    LOGICAND = r'&&'
    LOGICOR = r'\|\|'

    @_(r'".*"')
    def STRING(self, t):
        # Remove quotation marks.
        t.value = t.value[1:-1]
        return t

    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    FLOATVALUE = r'[0-9]+[.][0-9]+[f]?'
    INTVALUE = r'[0-9]+[f]?'

    ignore_space = r' '
    ignore_tabs = r'\t'
    ignore_comments = r'//.*'

    # Reserved keywords
    ID['int'] = INT
    ID['if'] = IF
    ID['else'] = ELSE
    ID['void'] = VOID
    ID['return'] = RETURN
    ID['printf'] = PRINTF
    ID['scanf'] = SCANF

    # Error and Indexing management
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    # Error handling rule
    def error(self, t):
        print("Illegal character '%s'" % t.value[0])
        self.index += 1


class CParser(Parser):
    global symbolValue
    symbolValue = {}
    tokens = CLexer.tokens
    start = 'sentence'

    functions = {}
    parser = 0

    # Print Error Function

    # AST Nodes
    class Node:
        def __init__(self):
            self.outputFile = "Output6.x86"
        def execute(self):
            pass

        def PrintError(self, msg, line):
            print(bcolors.BOLD, bcolors.OKGREEN, "Linea:", line, "->", msg)
            return

    class NodeDeclaration(Node):
        def __init__(self, idname, line):
            global symbolValue
            if idname not in symbolValue:
                symbolValue[idname] = 0
            else:
                super().PrintError("Symbol " + idname + " is already declared", line)

    class NodeId(Node):
        def __init__(self, idname, line):
            self.idname = idname
            self.line = line

        def execute(self):
            global symbolValue
            if self.idname in symbolValue:
                return symbolValue[self.idname]
            else:
                super().PrintError("Symbol " + self.idname + " is not declared", self.line)

    class NodeAssign(Node):
        def __init__(self, idname, value, line):
            global symbolValue
            if idname in symbolValue:
                symbolValue[idname] = value
            else:
                super().PrintError("Symbol " + idname + " is not declared", line)

    class NodeArithmBinOp(Node):
        def __init__(self, p1, p2, op):
            self.n1 = p1
            self.n2 = p2
            self.operator = op

        def execute(self):
            op = self.operator
            if op == '+':
                result = self.n1 + self.n2
            elif op == '-':
                result = self.n1 - self.n2
            elif op == '*':
                result = self.n1 * self.n2
            elif op == '/':
                result = self.n1 / self.n2
            elif op == '%':
                result = self.n1 % self.n2
            return result

    class NodeRelationalBinOp(Node):
        def __init__(self, p1, p2, op):
            self.n1 = p1
            self.n2 = p2
            self.operator = op

        def execute(self):
            op = self.operator
            if op == '>':
                result = self.n1 > self.n2
            elif op == '>=':
                result = self.n1 >= self.n2
            elif op == '<':
                result = self.n1 < self.n2
            elif op == '<=':
                result = self.n1 <= self.n2
            elif op == '==':
                result = self.n1 == self.n2
            elif op == '!=':
                result = self.n1 != self.n2
            return result

    class NodeLogicalBinOp(Node):
        def __init__(self, p1, p2, op):
            self.operator = op

            if type(p1) is not bool:
                p1 = False if p1 == 0 else True
            if type(p2) is not bool:
                p2 = False if p2 == 0 else True

            self.n1 = p1
            self.n2 = p2

        def execute(self):
            op = self.operator
            if op == '||':
                result = self.n1 or self.n2
            elif op == '&&':
                result = self.n1 and self.n2
            return result

    # Unary goes here! <----
    class NodeUnaryOp(Node):
        def __init__(self, p1, op):
            self.op = op
            self.p1 = p1

            if op == '&':
                pass
            else:
                raise RuntimeError('Invalid operation')

    class NodePrint(Node):
        def __init__(self, line, string, *values):
            if values:
                try:
                    values = list(values[0])
                except TypeError as te:
                    values = list(values)

                values = values[::-1]

                # Check number of specifiers and number of values
                if len(values) != string.count('%d'):
                    super().PrintError('Number of parameters is different from the number of specifiers', line)
                else:
                    for val in values:
                        string = string.replace('%d', str(val), 1)
                    print(string)
            else:
                if string.count('%d') > 0:
                    super().PrintError('Number of parameters is different from the number of specifiers', line)
                else:
                    print(string)
            pass

        def execute(self):
            pass

    class NodeScan(Node):
        def __init__(self, line, string, *values):
            if values:
                try:
                    values = list(values[0])
                except TypeError as te:
                    values = list(values)

                values = values[::-1]

                # Check number of specifiers and number of values
                if len(values) != string.count('%d'):
                    super().PrintError("Number of parameters is different from the number of specifiers", line)
            else:
                if string.count('%d') > 0:
                    super().PrintError("Number of parameters is different from the number of specifiers", line)
            pass

        def execute(self):
            pass

    # Program structure
    @_('instruction sentence')
    def sentence(self, p):
        return p[0]

    @_('')
    def sentence(self, p):
        return

    # Assignations
    @_('type declaration ";"',
       'type declaration "," anotherDeclaration')
    def instruction(self, p):
        return p[1]

    @_('assignment ";"')
    def instruction(self, p):
        return p[0]

    @_('ID "=" assignment')
    def declaration(self, p):
        self.NodeDeclaration(p[0], p.lineno)
        self.NodeAssign(p[0], p[2], p.lineno)

    @_('ID')
    def declaration(self, p):
        self.NodeDeclaration(p[0], p.lineno)

    @_('declaration "," anotherDeclaration',
       'declaration ";"')
    def anotherDeclaration(self, p):
        return p[0]

    @_('ID "=" assignment')
    def assignment(self, p):
        self.NodeAssign(p[0], p[2], p.lineno)

    @_('expr')
    def assignment(self, p):
        return p[0]

    # Structure control
    @_('IF "(" expr ")" "{" sentence "}"',
       'IF "(" expr ")" "{" sentence "}" ELSE "{" sentence "}"')
    def instruction(self, p):
        pass

    # Built-in Functions
    @_('PRINTF "(" STRING "," callParams ")" ";"')
    def instruction(self, p):
        self.NodePrint(p.lineno, p.STRING, p.callParams)

    @_('PRINTF "(" STRING ")" ";" ')
    def instruction(self, p):
        self.NodePrint(p.lineno, p.STRING)

    @_('SCANF "(" STRING "," scanfParams ")" ";"')
    def instruction(self, p):
        self.NodeScan(p.lineno, p.STRING, p.scanfParams)

    # User Functions
    @_('type ID',
       'VOID ID')
    def param(self, p):
        self.NodeDeclaration(p[1], p.lineno)
        return p[1]

    @_('param "," params',
       'param')
    def params(self, p):
        pass

    @_('type "," typeDec',
       'type')
    def typeDec(self, p):
        pass

    @_('expr "," callParams')
    def callParams(self, p):
        p.callParams.append(p.expr)
        return p.callParams

    @_('expr')
    def callParams(self, p):
        return [p.expr]

    @_('address "," scanfParams')
    def scanfParams(self, p):
        p.scanfParams.append(p.address)
        return p.scanfParams

    @_('address')
    def scanfParams(self, p):
        return [p.address]

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
            if p[0] in symbolValue:
                raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is already declared as a variable')
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
        node = self.NodeLogicalBinOp(p[0], p[2], '||')
        return node.execute()

    @_('logicalAND LOGICAND comparison')
    def logicalAND(self, p):
        node = self.NodeLogicalBinOp(p[0], p[2], '&&')
        return node.execute()

    @_('comparison EQUAL relation')
    def comparison(self, p):
        node = self.NodeRelationalBinOp(p[0], p[2], '==')
        return node.execute()

    @_('comparison NOTEQUAL relation')
    def comparison(self, p):
        node = self.NodeRelationalBinOp(p[0], p[2], '!=')
        return node.execute()

    @_('relation "<" arithExpr')
    def relation(self, p):
        node = self.NodeRelationalBinOp(p[0], p[2], '<')
        return node.execute()

    @_('relation LESSTHANEQUAL arithExpr')
    def relation(self, p):
        node = self.NodeRelationalBinOp(p[0], p[2], '<=')
        return node.execute()

    @_('relation ">" arithExpr')
    def relation(self, p):
        node = self.NodeRelationalBinOp(p[0], p[2], '>')
        return node.execute()

    @_('relation GREATERTHANEQUAL arithExpr')
    def relation(self, p):
        node = self.NodeRelationalBinOp(p[0], p[2], '>=')
        return node.execute()

    # Arithmetic operators
    @_('arithExpr "+" term')
    def arithExpr(self, p):
        node = self.NodeArithmBinOp(p[0], p[2], '+')
        return node.execute()

    @_('arithExpr "-" term')
    def arithExpr(self, p):
        node = self.NodeArithmBinOp(p[0], p[2], '-')
        return node.execute()

    @_('term "*" fact')
    def term(self, p):
        node = self.NodeArithmBinOp(p[0], p[2], '*')
        return node.execute()

    @_('term "/" fact')
    def term(self, p):
        node = self.NodeArithmBinOp(p[0], p[2], '/')
        return node.execute()

    @_('term "%" fact')
    def term(self, p):
        node = self.NodeArithmBinOp(p[0], p[2], '%')
        return node.execute()

    # Unary operators

    @_('"&" ID')
    def address(self, p):
        self.NodeId(p[1], p.lineno).execute()

    @_('"!" unary')
    def unary(self, p):
        return not p[1]

    @_('"-" unary')
    def num(self, p):
        return - p[1]

    # Parenthesis
    @_('"(" expr ")"')
    def num(self, p):
        return self.NodeNum

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
        node = self.NodeId(p[0], p.lineno)
        return node.execute()

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

    text = open("Source6.c").read()
    tokenizedText = lexer.tokenize(text)
    print("\n =========[ Lexer ] ===========")
    for token in tokenizedText:
        print("token:", token.type, ", lexvalue:", token.value)

    print("\n =========[ Parser ] ===========")
    try:
        parser.parse(lexer.tokenize(text))
    except RuntimeError as e:
        print(bcolors.BOLD, bcolors.OKCYAN, e)
