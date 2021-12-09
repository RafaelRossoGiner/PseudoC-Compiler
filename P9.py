from sly import Lexer
from sly import Parser

global symbolEBPoffset, offsetEBP, contador, strings


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
              INT, VOID, IF, ELSE, WHILE, RETURN, PRINTF, SCANF, STRING}
    literals = {'=', '+', '-', '/', '*', '%', '!', ';', ',', '(', ')', '{', '}', ',', '"', '&', '<', '>'}

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
    ID['while'] = WHILE
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


def newLabelID():
    global contador
    contador += 1
    return contador


# AST Nodes
class Node:
    outputFilename = ""

    @staticmethod
    def PrintError(msg, line):
        print(bcolors.BOLD, bcolors.OKGREEN, "Linea:", line, "->", msg)
        return

    @staticmethod
    def Write(line, comment=None):
        with open(Node.outputFilename, 'a') as output:
            if comment is None:
                output.write("\t" + line + "\n")
            else:
                output.write("\t" + line + " #" + comment + "\n")

    @staticmethod
    def WriteLabel(label):
        with open(Node.outputFilename, 'a') as output:
            output.write(label + ':\n')


class NodeDeclaration(Node):
    def __init__(self, idname, line):
        global symbolEBPoffset, offsetEBP
        if idname not in symbolEBPoffset:
            symbolEBPoffset[idname] = str(offsetEBP)
            offsetEBP = offsetEBP - 4
        else:
            super().PrintError("Symbol " + idname + " is already declared", line)


class NodeId(Node):
    def __init__(self, idname, line):
        global symbolEBPoffset
        self.offset = symbolEBPoffset[idname]
        if idname not in symbolEBPoffset:
            super().PrintError("Symbol " + idname + " is not declared", line)


class NodeNum(Node):
    def __init__(self, number, line):
        self.number = str(number)
        try:
            int(float(number.replace('f', '')))
        except ValueError:
            super().PrintError("Error parsing number value!", line)


class NodeAssign(Node):
    def __init__(self, idname, value, line):
        global symbolEBPoffset
        if idname in symbolEBPoffset:
            pass
            # symbolEBPoffset[idname] = value
        else:
            super().PrintError("Symbol " + idname + " is not declared", line)


class NodeArithmBinOp(Node):
    def __init__(self, p1, p2, op):
        # Operand 2
        if isinstance(p2, NodeId):
            super().Write("movl " + p2.offset + "(%ebp)" + ", %ebx")
            p2str = "%ebx"
        elif isinstance(p2, NodeNum):
            p2str = "$" + p2.number
        else:
            super().Write("popl " + "%ebx")
            p2str = "%ebx"

        # Operand 1
        if isinstance(p1, NodeId):
            super().Write("movl " + p1.offset + "(%ebp)" + ", %eax")
        elif isinstance(p1, NodeNum):
            super().Write("movl $" + p1.number + ", %eax")
        else:
            super().Write("popl " + "%eax")

        # Operation
        if op == '+':
            super().Write("addl " + p2str + ', %eax')
            super().Write("pushl %eax")
        elif op == '-':
            super().Write("subl " + p2str + ', %eax')
            super().Write("pushl %eax")
        elif op == '*':
            super().Write("imull " + p2str + ', %eax')
            super().Write("pushl %eax")
        elif op == '/':
            super().Write("cdq")
            super().Write("idivl " + p2str)
            super().Write("pushl %eax")
        elif op == '%':
            super().Write("cdq")
            super().Write("idivl " + p2str)
            super().Write("pushl %ebx")


class NodeRelationalBinOp(Node):
    def __init__(self, p1, p2, op):
        self.ID = newLabelID()
        # Operand 2
        if isinstance(p2, NodeId):
            super().Write("movl " + p2.offset + "(%ebp)" + ", %ebx")
            p2str = "%ebx"
        elif isinstance(p2, NodeNum):
            p2str = "$" + p2.number
        else:
            super().Write("popl " + "%ebx")
            p2str = "%ebx"

        # Operand 1
        if isinstance(p1, NodeId):
            p1str = p1.offset + "(%ebp)"
        elif isinstance(p1, NodeNum):
            p1str = "$" + p1.number
        else:
            super().Write("popl " + "%eax")
            p1str = "%eax"

        # Operation
        super().Write("movl $1, %eax #assume true")
        super().Write("cmp " + p1str + ", " + p2str)
        if op == '>':
            super().Write("jg condTrue" + str(self.ID))
        elif op == '>=':
            super().Write("jge condTrue" + str(self.ID))
        elif op == '<':
            super().Write("jl condTrue" + str(self.ID))
        elif op == '<=':
            super().Write("jle condTrue" + str(self.ID))
        elif op == '==':
            super().Write("je condTrue" + str(self.ID))
        elif op == '!=':
            super().Write("jne condTrue" + str(self.ID))

        super().Write("movl $0, %eax")
        super().WriteLabel("condTrue" + str(self.ID))
        super().Write("pushl %eax")


class NodeLogical(Node):
    def __init__(self, op):
        self.op = op
        self.ID = newLabelID()

    def firstOperand(self, p):
        if isinstance(p, NodeId):
            super().Write("movl " + p.offset + "(%ebp)" + ", %eax")
            operand = "%eax"
        elif isinstance(p, NodeNum):
            operand = "$" + p.number
        else:
            super().Write("popl " + "%eax")
            operand = "%eax"

        super().Write("cmpl " + "$0, " + operand, "check if op1 is false")
        if self.op == '&&':
            super().Write("pushl $0", "assume result is False")
            super().Write("je shortcut" + str(self.ID), "if op1 is false, don't check op2")
        elif self.op == '||':
            super().Write("pushl $1", "assume result is True")
            super().Write("jne shortcut" + str(self.ID), "if op1 is true, don't check op2")

    def secondOperand(self, p):
        if isinstance(p, NodeId):
            super().Write("movl " + p.offset + "(%ebp)" + ", %eax")
            operand = "%eax"
        elif isinstance(p, NodeNum):
            operand = "$" + p.number
        else:
            super().Write("popl " + "%eax")
            operand = "%eax"

        super().Write("cmpl " + "$0, " + operand, "check if op2 is false")
        if self.op == '&&':
            super().Write("movl $0, %eax", "assume result is False")
            super().Write("je shortcut" + str(self.ID), "if op2 is False, jump")
            super().Write("movl $1, %eax", "negate assumption")
        elif self.op == '||':
            super().Write("movl $1, %eax", "assume result is True")
            super().Write("jne shortcut" + str(self.ID), "if op2 is True, jump")
            super().Write("movl $0, %eax", "negate assumption")
        super().Write("popl %ebx", "Remove result of op1")
        super().Write("pushl %eax", "Push final operator result")
        super().WriteLabel("shortcut" + str(self.ID))


class NodeUnaryOp(Node):
    def __init__(self, p1, op):
        self.op = op
        self.p1 = p1

        if op == '&':
            pass
        elif op == '-':
            # Operand
            if isinstance(p1, NodeId):
                super().Write("movl " + p1.offset + "(%ebp)" + ", %eax")
            elif isinstance(p1, NodeNum):
                super().Write("movl $" + p1.number + ", %eax")
            else:
                super().Write("popl " + "%eax")

            super().Write("imul $-1")
            super().Write("pushl %eax")
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


class NodeIf(Node):
    def __init__(self, ID):
        self.ID = ID

    def compare(self):
        super().Write('popl %eax')
        super().Write('cmpl $0, %eax')
        super().Write('je false' + str(self.ID))

    def finalJump(self):
        super().Write('jmp final' + str(self.ID))

    def falseLabel(self):
        super().WriteLabel('false' + str(self.ID))

    def finalLabel(self):
        super().WriteLabel('final' + str(self.ID))


class NodeWhile(Node):
    def __init__(self, ID):
        self.ID = ID

    def startLabel(self):
        super().WriteLabel('start' + str(self.ID))

    def compare(self):
        super().Write('popl %eax')
        super().Write('cmpl $0, %eax')
        super().Write('jne final' + str(self.ID))

    def jumpStart(self):
        super().Write('jmp start' + str(self.ID))

    def falseLabel(self):
        super().WriteLabel('false' + str(self.ID))

    def finalLabel(self):
        super().WriteLabel('final' + str(self.ID))


class NodeFunctionPrologue(Node):
    def __init__(self, name):
        super().WriteLabel(name)
        super().Write('pushl %ebp')
        super().Write('movl %esp, %ebp')

class NodeFunctionEpilogue(Node):
    def __init__(self):
        super().Write('movl %ebp, %esp')
        super().Write('popl %ebp')
        super().Write('ret')

class NodeFunctionCall(Node):
    def __init__(self, name, argc):
        super().Write('call ' + name)
        if argc > 0:
            super().Write('addl $' + str(argc*4) + ', %esp')

class NodeFunctionParam(Node):
    def __init__(self, arg):
        if isinstance(arg, NodeId):
            super().Write('pushl ' + arg.offset + '(%ebp)')
        elif isinstance(arg, NodeNum):
            super().Write('pushl $' + arg.number)
        elif isinstance(arg, NodeFunctionCall) or isinstance(arg, NodeUnaryOp) or isinstance(arg, NodeArithmBinOp):
            super().Write('pushl %eax')
        else:
            raise RuntimeError('Invalid node type')

class NodeReturn(Node):
    def __init__(self):
        super().Write('movl something, %eax')

class CParser(Parser):
    tokens = CLexer.tokens
    start = 'sentence'

    functions = {}
    parser = 0

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
        NodeDeclaration(p[0], p.lineno)
        NodeAssign(p[0], p[2], p.lineno)

    @_('ID')
    def declaration(self, p):
        NodeDeclaration(p[0], p.lineno)

    @_('declaration "," anotherDeclaration',
       'declaration ";"')
    def anotherDeclaration(self, p):
        return p[0]

    @_('ID "=" assignment')
    def assignment(self, p):
        NodeAssign(p[0], p[2], p.lineno)

    @_('expr')
    def assignment(self, p):
        return p[0]

    # Structure control
    @_('IFcondition "{" sentence "}"')
    def instruction(self, p):
        node = p[0]
        node.falseLabel()

    @_('IFcondition "{" sentence "}" jumpFinal ELSE "{" sentence "}"')
    def instruction(self, p):
        node = p[0]
        node.finalLabel()

    @_('')
    def jumpFinal(self, p):
        node = p[-4]
        node.finalJump()
        node.falseLabel()

    @_('IF "(" expr ")"')
    def IFcondition(self, p):
        ID = newLabelID()
        node = NodeIf(ID)
        node.compare()
        return node

    @_('WHILEcondition "{" sentence "}"')
    def instruction(self, p):
        node = p[0]
        node.jumpStart()
        node.finalLabel()

    @_('startWhile WHILE "(" expr ")"')
    def WHILEcondition(self, p):
        node = p[0]
        node.compare()
        return node

    @_('')
    def startWhile(self, p):
        ID = newLabelID()
        node = NodeWhile(ID)
        node.startLabel()
        return node

    # Built-in Functions
    @_('PRINTF "(" STRING "," callParams ")" ";"')
    def instruction(self, p):
        NodePrint(p.lineno, p.STRING, p.callParams)

    @_('PRINTF "(" STRING ")" ";" ')
    def instruction(self, p):
        NodePrint(p.lineno, p.STRING)

    @_('SCANF "(" STRING "," scanfParams ")" ";"')
    def instruction(self, p):
        NodeScan(p.lineno, p.STRING, p.scanfParams)

    # User Functions
    @_('type ID',
       'VOID ID')
    def param(self, p):
        NodeDeclaration(p[1], p.lineno)
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
        NodeFunctionParam(p.expr)
        p.callParams.append(p.expr)
        return p.callParams

    @_('expr')
    def callParams(self, p):
        NodeFunctionParam(p.expr)
        return [p.expr]

    @_('address "," scanfParams')
    def scanfParams(self, p):
        p.scanfParams.append(p.address)
        return p.scanfParams

    @_('address')
    def scanfParams(self, p):
        return [p.address]

    @_('ID "(" callParams ")"')
    def num(self, p):
        if p[0] in self.functions:
            return NodeFunctionCall(p[0], len(p[2]))
        else:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a Function')

    @_('ID "(" ")"')
    def num(self, p):
        if p[0] in self.functions:
            return NodeFunctionCall(p[0], 0)
        else:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a Function')

    @_('RETURN expr ";"')
    def retInstruction(self, p):
        NodeReturn()
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
            if p[0] in symbolEBPoffset:
                raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is already declared as a variable')
            else:
                self.functions[p[0]] = 0
        return 0

    @_('functionDecl "{"')
    def functDefInit(self, p):
        self.functions[p[0]] = 0
        NodeFunctionPrologue(p[0])
        # Añadir la declaracion de variables
        return 0

    @_('voidFunctionDecl "{"')
    def voidfunctDefInit(self, p):
        self.functions[p[0]] = 0
        NodeFunctionPrologue(p[0])
        # Añadir la declaracion de variables
        return 0

    @_('functDefInit sentence retInstruction "}"')
    def instruction(self, p):
        NodeFunctionEpilogue()
        return 0

    @_('voidfunctDefInit sentence "}"')
    def instruction(self, p):
        NodeFunctionEpilogue()
        return 0

    # Logical operators
    @_('logicalOR LOGICOR')
    def logicalORFirst(self, p):
        node = NodeLogical('||')
        node.firstOperand(p[0])
        return node

    @_('logicalORFirst logicalAND')
    def logicalOR(self, p):
        p[0].secondOperand(p[1])
        return p[0]

    @_('logicalAND LOGICAND')
    def logicalANDFirst(self, p):
        node = NodeLogical('&&')
        node.firstOperand(p[0])
        return node

    @_('logicalANDFirst comparison')
    def logicalAND(self, p):
        p[0].secondOperand(p[1])
        return p[0]

    @_('comparison EQUAL relation')
    def comparison(self, p):
        return NodeRelationalBinOp(p[0], p[2], '==')

    @_('comparison NOTEQUAL relation')
    def comparison(self, p):
        return NodeRelationalBinOp(p[0], p[2], '!=')

    @_('relation "<" arithExpr')
    def relation(self, p):
        return NodeRelationalBinOp(p[0], p[2], '<')

    @_('relation LESSTHANEQUAL arithExpr')
    def relation(self, p):
        return NodeRelationalBinOp(p[0], p[2], '<=')

    @_('relation ">" arithExpr')
    def relation(self, p):
        return NodeRelationalBinOp(p[0], p[2], '>')

    @_('relation GREATERTHANEQUAL arithExpr')
    def relation(self, p):
        return NodeRelationalBinOp(p[0], p[2], '>=')

    # Arithmetic operators
    @_('arithExpr "+" term')
    def arithExpr(self, p):
        return NodeArithmBinOp(p[0], p[2], '+')

    @_('arithExpr "-" term')
    def arithExpr(self, p):
        pass
        return NodeArithmBinOp(p[0], p[2], '-')

    @_('term "*" fact')
    def term(self, p):
        return NodeArithmBinOp(p[0], p[2], '*')

    @_('term "/" fact')
    def term(self, p):
        return NodeArithmBinOp(p[0], p[2], '/')

    @_('term "%" fact')
    def term(self, p):
        return NodeArithmBinOp(p[0], p[2], '%')

    # Unary operators
    @_('"&" ID')
    def address(self, p):
        NodeId(p[1], p.lineno)

    @_('"!" unary')
    def unary(self, p):
        return not p[1]

    @_('"-" unary')
    def num(self, p):
        return NodeUnaryOp(p[1], '-')

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
        return NodeNum(p[0], p.lineno)

    @_('ID')
    def num(self, p):
        return NodeId(p[0], p.lineno)

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
    symbolEBPoffset = {}
    offsetEBP = -4
    contador = 0
    strings = []
    lexer = CLexer()
    parser = CParser()
    Node.outputFilename = "Output9.s"
    open(Node.outputFilename, 'w').close()

    text = open("Source9.c").read()
    tokenizedText = lexer.tokenize(text)
    print("\n =========[ Lexer ] ===========")
    for token in tokenizedText:
        print("token:", token.type, ", lexvalue:", token.value)

    print("\n =========[ Parser ] ===========")
    try:
        parser.parse(lexer.tokenize(text))
    except RuntimeError as e:
        print(bcolors.BOLD, bcolors.OKCYAN, e)
