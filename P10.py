from sly import Lexer
from sly import Parser
import re

global symbolEBPoffset, offsetEBP, contador, symbolType


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
    literals = {'=', '+', '-', '/', '*', '%', '!', ';', ',', '(', ')', '{', '}', ',', '"', '&', '<', '>', '[', ']'}

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

    @_(r'/\*(.|\n)*\*/')
    def ignore_commentBlock(self, t):
        self.lineno += len([*re.finditer('\n', t.value)])

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
    nodeType = None

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

    @staticmethod
    def WriteStrings():
        contador = 0
        for string in strings:
            Node.WriteLabel(".s" + str(contador))
            Node.Write(string)
            contador += 1


class NodeError(Node):
    def __init__(self, msg, line=None):
        if line is not None:
            print(bcolors.BOLD, bcolors.OKGREEN, "Linea:", line, "->", msg, bcolors.ENDC)
        else:
            print(bcolors.BOLD, bcolors.OKGREEN, "->", msg, bcolors.ENDC)
        return


# AST Type Nodes
class NodeInt(Node):
    def __init__(self):
        self.size = 4


class NodeId(Node):
    def __init__(self, idname):
        global symbolEBPoffset, symbolType
        self.idname = idname
        self.val = symbolEBPoffset[self.idname]
        self.nodeType = symbolType[self.idname]


class NodeNum(Node):
    def __init__(self, val, nodeType, line):
        self.nodeType = nodeType
        try:
            numVal = int(float(val.replace('f', '')))
            self.val = str(numVal)
            self.numVal = numVal
        except ValueError:
            NodeError("Error parsing number value!", line)


class NodeArray(Node):
    def __init__(self, refNode, indxVal):
        self.refNode = refNode
        self.indxVal = indxVal
        self.size = 4
        return


class NodePointer(Node):
    def __init__(self, refNode):
        self.refNode = refNode
        self.size = refNode.size
        return


class NodeVoid(Node):
    def __init__(self):
        pass


# AST Operation Nodes
class NodeDeclarationAssign(Node):
    def __init__(self, elmNode, expr=None):
        self.rval = expr
        self.lval = elmNode
        self.idname = None
        self.nodeType = None

    def declare(self, givenType):
        global symbolEBPoffset, offsetEBP, symbolType
        # Obtain array size multiplier and ID name
        super().Write("movl $1, %eax")
        varSize = 1
        while isinstance(self.lval, NodeArray):
            if isinstance(self.lval.indxVal, NodeNum):
                sizeMult = "$" + self.lval.indxVal.val
                varSize *= self.lval.indxVal.numVal
            elif isinstance(self.lval.indxVal, NodeId):
                sizeMult = symbolEBPoffset[self.lval.indxVal.val] + "(%ebp)"
            else:
                super().Write("popl %ebx")
                sizeMult = "%ebx"
            super().Write("imul " + sizeMult)
            self.lval = self.lval.refNode

        # Obtain name and check table
        self.idname = self.lval
        if self.idname in symbolEBPoffset:
            NodeError("Symbol " + self.idname + " is already declared")
        else:
            # Obtain type and its size
            self.nodeType = givenType
            varSize *= self.nodeType.size

            # Create table entries
            symbolType[self.idname] = self.nodeType
            symbolEBPoffset[self.idname] = str(offsetEBP)

            # Reserve space and update counter
            offsetEBP = offsetEBP - varSize
            super().Write("subl $" + str(varSize) + ", %esp",
                          self.idname + " (offset=" + symbolEBPoffset[self.idname] + ")")

            # Initialize if necessary
            if self.rval is not None:
                if isinstance(self.rval, NodeId):
                    strOp1 = self.rval.val + "(%ebp)"
                elif isinstance(self.rval, NodeNum):
                    strOp1 = "$" + self.rval.val
                else:
                    super().Write("popl %eax", "Pop assignment value")
                    strOp1 = "%eax"

                super().Write("movl " + strOp1 + ", " + symbolEBPoffset[self.idname] + "(%ebp)",
                              self.idname + " = assignment")


class NodeAssign(Node):
    def __init__(self, idNode, expr, line):
        global symbolEBPoffset
        self.nodeType = idNode.nodeType
        if isinstance(idNode, NodeNum):
            NodeError("Left member of assignment is not a valid Lval!", line)
        else:
            # Get Rval
            if isinstance(expr, NodeId):
                assignment = expr.val + "(%ebp)"
            elif isinstance(expr, NodeNum):
                assignment = "$" + expr.val
            elif isinstance(expr, NodeAssign):
                assignment = symbolEBPoffset[expr.idname] + "(%ebp)"
            else:
                super().Write("popl %eax", "Pop assignment value")
                assignment = "%eax"

            # Get Lval
            if isinstance(idNode, NodeId):
                self.lvalStr = idNode.val + "(%ebp)"
            elif isinstance(idNode, NodeAssign):
                self.lvalStr = idNode.lvalStr
            else:
                super().Write("popl %ebx", "Pop lval value")
                self.lvalStr = "%ebx"
            super().Write("movl " + assignment + ", PTR [" + self.lvalStr + "]", "Assign rval to where lval points")


class NodeIntCons(Node):
    def __init__(self):
        self.nodeType = NodeInt()


class NodeArithmBinOp(Node):
    def __init__(self, p1, p2, op, line=None):

        # Operand 2
        if isinstance(p2, NodeId):
            super().Write("movl " + p2.val + "(%ebp)" + ", %ebx", p2.val + " (offset=" + p2.val + ")")
            p2str = "%ebx"
        elif isinstance(p2, NodeNum):
            p2str = "$" + p2.val
        else:
            super().Write("popl " + "%ebx", "Operand 2")
            p2str = "%ebx"

        # Operand 1
        if isinstance(p1, NodeId):
            super().Write("movl " + p1.val + "(%ebp)" + ", %eax", p1.val + " (offset=" + p1.val + ")")
        elif isinstance(p1, NodeNum):
            super().Write("movl $" + p1.val + ", %eax")
        else:
            super().Write("popl " + "%eax", "Operand 1")

        # Operation
        if op == '+':
            super().Write("addl " + p2str + ', %eax')
            super().Write("pushl %eax", "Result add")
        elif op == '-':
            super().Write("subl " + p2str + ', %eax')
            super().Write("pushl %eax", "Result sub")
        elif op == '*':
            super().Write("imull " + p2str + ', %eax')
            super().Write("pushl %eax", "Result mult")
        elif op == '/':
            super().Write("cdq")
            super().Write("idivl " + p2str)
            super().Write("pushl %eax", "Result div")
        elif op == '%':
            super().Write("cdq")
            super().Write("idivl " + p2str)
            super().Write("pushl %ebx", "Result mod")


class NodeRelationalBinOp(Node):
    def __init__(self, p1, p2, op, line):
        self.ID = newLabelID()

        # Type Checkingds
        if not isinstance(p1.nodeType, type(p2.nodeType)):
            NodeError("Incompatible type of the operands!", line)
        else:
            self.nodeType = p1.nodeType

        # Operand 2
        if isinstance(p2, NodeId):
            super().Write("movl " + p2.val + "(%ebp)" + ", %ebx")
            p2str = "%ebx"
        elif isinstance(p2, NodeNum):
            p2str = "$" + p2.val
        else:
            super().Write("popl " + "%ebx")
            p2str = "%ebx"

        # Operand 1
        if isinstance(p1, NodeId):
            p1str = p1.val + "(%ebp)"
        elif isinstance(p1, NodeNum):
            p1str = "$" + p1.val
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
        self.nodeType = None

    def firstOperand(self, p):
        self.nodeType = p.nodeType
        if isinstance(p, NodeId):
            super().Write("movl " + p.val + "(%ebp)" + ", %eax")
            operand = "%eax"
        elif isinstance(p, NodeNum):
            operand = "$" + p.val
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
        self.nodeType = p.nodeType
        if isinstance(p, NodeId):
            super().Write("movl " + p.val + "(%ebp)" + ", %eax")
            operand = "%eax"
        elif isinstance(p, NodeNum):
            operand = "$" + p.val
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
    def __init__(self, p1, op, line):
        self.op = op
        self.p1 = p1

        if op == '!':
            # Type Checking
            self.nodeType = p1.nodeType
            # Operand
            if isinstance(p1, NodeId):
                super().Write("movl " + p1.val + "(%ebp)" + ", %eax", p1.val + "(%ebp) is " + p1.idname)
            elif isinstance(p1, NodeNum):
                super().Write("movl $" + p1.val + ", %eax")
            else:
                super().Write("popl " + "%eax")

            super().Write("cmp $0, %eax", "Check if operand is false")
            super().Write("movl $1, %eax", "Set as true (negation)")
            labelID = str(newLabelID())
            super().Write("je " + "negFinal" + labelID, "Jump if false")
            super().Write("movl $0, %eax", "Set as false (negate)")
            super().WriteLabel("negFinal" + labelID)
            super().Write("puslh %eax", "Store result")

        elif op == '-':
            if not isinstance(p1.nodeType, NodeInt):
                NodeError("Incompatible type for unary minus operand!", line)
            else:
                self.nodeType = p1.nodeType

            # Operand
            if isinstance(p1, NodeId):
                super().Write("movl " + p1.val + "(%ebp)" + ", %eax")
            elif isinstance(p1, NodeNum):
                super().Write("movl $" + p1.val + ", %eax")
            else:
                super().Write("popl " + "%eax")

            super().Write("imul $-1")
            super().Write("pushl %eax")
        else:
            raise RuntimeError('Invalid operation')


class NodeUnaryRefs(Node):
    def __init__(self, p1, op, line, offsetExpr=None):
        global symbolEBPoffset, symbolType
        self.op = op
        self.p1 = p1

        if op == '&':
            self.nodeType = NodePointer(p1.nodeType)
            if isinstance(p1, NodeId):
                super().Write("movl " + p1.val + "(%ebp), %eax", "%eax is " + p1.idname)
            elif isinstance(p1, NodeNum):
                NodeError("Reference '&' operator can only be applied to variable identifers")
            else:
                super().Write("popl %eax")
            super().Write("leal %eax, %eax")
            super().Write("pushl %eax")

        elif op == '*':
            if not isinstance(p1.nodeType, NodePointer):
                NodeError("Operand is not an address!", line)
            else:
                self.nodeType = p1.nodeType.refNode.nodeType

            if isinstance(p1, NodeNum):
                super().Write("movl PTR [$" + p1.val + "], %eax")
            elif isinstance(p1, NodeId):
                super().Write("movl " + p1.val + "(%ebp), %eax")
            else:
                super().Write("popl %eax")
            super().Write("movl PTR [%eax], %eax", "Dereference pointer")
            super().Write("pushl %eax")

        elif op == '[]':
            if not isinstance(p1.nodeType, NodePointer):
                NodeError("Is not an address!", line)
            else:
                self.nodeType = p1.nodeType.refNode.nodeType

            # Calculate Offset
            if isinstance(offsetExpr, NodeNum):
                offset = "$" + offsetExpr.val
            elif isinstance(offsetExpr, NodeId):
                offset = offsetExpr.val + "(%ebp)"
            else:
                super().Write("popl %eax")
                offset = "%eax"
            super().Write("imul $" + str(p1.nodeType.size) + ", " + offset, "Calculate Offset")
            super().Write("movl %eax, %ebx", "Store Offset in ebx")

            # De-rerference pointer
            if isinstance(p1, NodeNum):
                super().Write("movl PTR [$" + p1.val + "], %eax")
            elif isinstance(p1, NodeId):
                super().Write("movl " + p1.val + "(%ebp), %eax")
            else:
                super().Write("popl %eax")

            super().Write("subl %ebx", "Address = Pointer + Offset")
            super().Write("movl PTR [%eax], %eax", "Dereference Address")
            super().Write("pushl %eax", "Store value")
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
                NodeError('Number of parameters is different from the number of specifiers', line)
            else:
                for val in values:
                    string = string.replace('%d', str(val), 1)
        else:
            if string.count('%d') > 0:
                NodeError('Number of parameters is different from the number of specifiers', line)
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
                NodeError("Number of parameters is different from the number of specifiers", line)
        else:
            if string.count('%d') > 0:
                NodeError("Number of parameters is different from the number of specifiers", line)
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
        super().Write('pushl %ebp', "Function Prologue")
        super().Write('movl %esp, %ebp')


class NodeFunctionEpilogue(Node):
    def __init__(self):
        super().Write('movl %ebp, %esp', "Function Epilogue")
        super().Write('popl %ebp')
        super().Write('ret\n')


class NodeFunctionCall(Node):
    def __init__(self, name, argc, paramTypes):

        # Check only for functions that are not printf or scanf
        if name != 'printf' and name != 'scanf' and paramTypes is not None:
            argTypes = symbolType[name]
            argTypes = argTypes[1]
            if len(argTypes) != argc:
                NodeError("Invalid number of arguments")
            else:
                for arg in range(0, len(argTypes)):
                    if type(argTypes[arg]) != type(paramTypes[arg].nodeType):
                        NodeError("Unexpected types for arguments")

        super().Write('call ' + name)
        if argc > 0:
            super().Write('addl $' + str(argc * 4) + ', %esp')
        super().Write('pushl %eax')


class NodeFunctionParam(Node):
    def __init__(self, arg):
        if isinstance(arg, int):  # cadena
            super().Write('pushl ' + '$s' + str(arg))
        elif isinstance(arg.nodeType, NodeInt): # variable entera
            super().Write('pushl ' + arg.val + '(%ebp)')
        elif isinstance(arg, NodeNum): # literal
            super().Write('pushl $' + arg.val)
        elif isinstance(arg.nodeType, NodeFunctionCall) or isinstance(arg, NodeUnaryOp) or isinstance(arg, NodeArithmBinOp): # resultado de función o expresión
            pass
        elif isinstance(arg.nodeType, NodePointer): # puntero
            super().Write('PLACEHOLDER isinstance(arg.nodeType, NodePointer)')
        else:
            raise RuntimeError('Invalid node type ' + str(type(arg.nodeType)))


class NodeReturn(Node):
    def __init__(self, exprNode):
        if isinstance(exprNode, NodeId):
            super().Write("movl " + exprNode.val + "(%ebp), %eax", "Move return value")
        elif isinstance(exprNode, NodeNum):
            super().Write("movl $" + exprNode.val + ", %eax", "Move return value")
        else:
            super().Write("popl %eax", "Pop return value")


class CParser(Parser):
    tokens = CLexer.tokens
    start = 'program'

    functions = {}
    parser = 0

    # Program structure
    @_('sentence')
    def program(self, p):
        Node.WriteStrings()

    @_('instruction sentence')
    def sentence(self, p):
        return p[0]

    @_('')
    def sentence(self, p):
        pass

    @_('type "*"')
    def type(self, p):
        return NodePointer(p[0])

    @_('ID "[" expr "]"')
    def var(self, p):
        return NodeArray(p[0], p[2])

    @_('var "[" expr "]"')
    def var(self, p):
        return NodeArray(p[0], p[2])

    # Assignations
    @_('type declList ";"')
    def instruction(self, p):
        for node in reversed(p[1]):
            node.declare(p[0])

    @_('assignment ";"')
    def instruction(self, p):
        if not isinstance(p[0], NodeAssign):
            Node.Write("popl %eax", "Pop unused result")
        return p[0]

    @_('var "=" assignment')
    def declaration(self, p):
        return NodeDeclarationAssign(p[0], p[2])

    @_('ID "=" assignment')
    def declaration(self, p):
        return NodeDeclarationAssign(p[0], p[2])

    @_('var')
    def declaration(self, p):
        return NodeDeclarationAssign(p[0])

    @_('ID')
    def declaration(self, p):
        return NodeDeclarationAssign(p[0])

    @_('declaration "," declList')
    def declList(self, p):
        p[2].append(p[0])
        return p[2]

    @_('declaration')
    def declList(self, p):
        return [p[0]]

    @_('expr "=" assignment')
    def assignment(self, p):
        return NodeAssign(p[0], p[2], p.lineno)

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
        global strings
        strings.append(p[2])
        NodeFunctionParam(len(strings) - 1)

        NodeFunctionCall('printf', len(p[4]) + 1, p[4])

        NodePrint(p.lineno, p.STRING, p.callParams)

    @_('PRINTF "(" STRING ")" ";" ')
    def instruction(self, p):
        global strings
        strings.append(p[2])
        NodeFunctionParam(len(strings) - 1)

        NodeFunctionCall('printf', 1, None)

        NodePrint(p.lineno, p.STRING)

    @_('SCANF "(" STRING "," scanfParams ")" ";"')
    def instruction(self, p):
        global strings
        strings.append(p[2])
        NodeFunctionParam(len(strings) - 1)

        NodeFunctionCall('scanf', len(p[4]) + 1, None)

        NodeScan(p.lineno, p.STRING, p.scanfParams)

    # User Functions
    @_('type ID',
       'VOID ID')
    def param(self, p):
        node = NodeDeclarationAssign(p[1])
        node.declare(p[0])
        return node.nodeType

    @_('param "," params')
    def params(self, p):
        p[2].append(p[0])
        return p[2]  # La lista resultante está al revés

    @_('param')
    def params(self, p):
        return [p[0]]

    @_('type "," typeDec')
    def typeDec(self, p):
        p[2].append(p[0])
        return p[2]  # La lista resultante está al revés0

    @_('type')
    def typeDec(self, p):
        return [p[0]]

    @_('expr "," callParams')
    def callParams(self, p):
        NodeFunctionParam(p[0])
        p.callParams.append(p[0])
        return p.callParams

    @_('expr')
    def callParams(self, p):
        NodeFunctionParam(p[0])
        return [p[0]]

    @_('unary "," scanfParams')
    def scanfParams(self, p):
        NodeFunctionParam(p[0])
        p[2].append(p.address)
        return p[2]

    @_('unary')
    def scanfParams(self, p):
        NodeFunctionParam(p[0])
        return [p[0]]

    @_('ID "(" callParams ")"')
    def num(self, p):
        if p[0] in self.functions:
            return NodeFunctionCall(p[0], len(p[2]), p[2])
        else:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a Function')

    @_('ID "(" ")"')
    def num(self, p):
        if p[0] in self.functions:
            return NodeFunctionCall(p[0], 0, None)
        else:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a Function')

    @_('RETURN expr ";"')
    def retInstruction(self, p):
        NodeReturn(p[1])
        return

    @_('type ID "(" params ")"',
       'type ID "(" typeDec ")"',
       'type ID "(" ")"')
    def functionDecl(self, p):
        global symbolType
        symbolType[p[1]] = [p[0], p[3]]
        return p[1]

    @_('VOID ID "(" params ")"',
       'VOID ID "(" typeDec ")"',
       'VOID ID "(" ")"')
    def voidFunctionDecl(self, p):
        global symbolType
        symbolType[p[1]] = [p[0], p[3]]
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
        return NodeRelationalBinOp(p[0], p[2], '==', p.lineno)

    @_('comparison NOTEQUAL relation')
    def comparison(self, p):
        return NodeRelationalBinOp(p[0], p[2], '!=', p.lineno)

    @_('relation "<" arithExpr')
    def relation(self, p):
        return NodeRelationalBinOp(p[0], p[2], '<', p.lineno)

    @_('relation LESSTHANEQUAL arithExpr')
    def relation(self, p):
        return NodeRelationalBinOp(p[0], p[2], '<=', p.lineno)

    @_('relation ">" arithExpr')
    def relation(self, p):
        return NodeRelationalBinOp(p[0], p[2], '>', p.lineno)

    @_('relation GREATERTHANEQUAL arithExpr')
    def relation(self, p):
        return NodeRelationalBinOp(p[0], p[2], '>=', p.lineno)

    # Arithmetic operators
    @_('arithExpr "+" term')
    def arithExpr(self, p):
        return NodeArithmBinOp(p[0], p[2], '+', p.lineno)

    @_('arithExpr "-" term')
    def arithExpr(self, p):
        pass
        return NodeArithmBinOp(p[0], p[2], '-', p.lineno)

    @_('term "*" fact')
    def term(self, p):
        return NodeArithmBinOp(p[0], p[2], '*', p.lineno)

    @_('term "/" fact')
    def term(self, p):
        return NodeArithmBinOp(p[0], p[2], '/', p.lineno)

    @_('term "%" fact')
    def term(self, p):
        return NodeArithmBinOp(p[0], p[2], '%', p.lineno)

    # Unary operators
    @_('"!" unary')
    def unary(self, p):
        return NodeUnaryOp(p[1], '!', p.lineno)

    @_('"-" unary')
    def unary(self, p):
        return NodeUnaryOp(p[1], '-', p.lineno)

    @_('"*" unary')
    def unary(self, p):
        return NodeUnaryRefs(p[1], '*', p.lineno)

    @_('"&" unary')
    def unary(self, p):
        # Esto no habría que ponerlo en un AST porque es una
        # diferenciación de tipos debida a nuestra implementación,
        # no a la gramática que estamos implementando ni a ninguna
        # operación relacionada con ella de forma teórica o conceptual.
        return NodeUnaryRefs(p[1], '&', p.lineno)

    @_('postfix "[" expr "]"')
    def postfix(self, p):
        return NodeUnaryRefs(p[0], '[]', p.lineno, p[2])

    # Parenthesis
    @_('"(" expr ")"')
    def num(self, p):
        return p[1]

    # Conversion hierarchy
    # PlaceHolder type function for scalability with more types
    @_('INT')
    def type(self, p):
        return NodeInt()

    @_('INTVALUE')
    def num(self, p):
        return NodeNum(p[0], NodeIntCons(), p.lineno)

    @_('ID')
    def num(self, p):
        return NodeId(p[0])

    @_('num')
    def postfix(self, p):
        return p[0]

    @_('postfix')
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
    symbolType = {}
    offsetEBP = -4
    contador = 0
    strings = []
    lexer = CLexer()
    parser = CParser()
    Node.outputFilename = "Output10.s"
    open(Node.outputFilename, 'w').close()

    text = open("Source10.c").read()
    tokenizedText = lexer.tokenize(text)
    print("\n =========[ Lexer ] ===========")
    for token in tokenizedText:
        print("token:", token.type, ", lexvalue:", token.value)

    print("\n =========[ Parser ] ===========")
    try:
        parser.parse(lexer.tokenize(text))
        print("========== [ Fin ]===============")
    except RuntimeError as e:
        print(bcolors.BOLD, bcolors.OKCYAN, e)
