from sly import Lexer
from sly import Parser
import re

global EBPoffsetTable, typeTable, counterEBP, counterString
global local_EBPoffsetTable, local_typeTable, local_counterEBP


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
    tokens = {EQUAL, LESSTHANEQUAL, GREATERTHANEQUAL, NOTEQUAL, LOGICAND, LOGICOR, ID, INTVALUE,
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
        # Remove quotation marks
        t.value = t.value[1:-1]
        return t

    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
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
    global counterString
    counterString += 1
    return counterString


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
        global EBPoffsetTable
        contador = 0
        if not ("main" in typeTable.keys()):
            NodeError("main function is missing!")
        for string in strings:
            Node.WriteLabel(".s" + str(contador))
            Node.Write(string)
            contador += 1
        for globalVar in EBPoffsetTable.keys():
            Node.WriteLabel(globalVar)



class NodeError(Node):
    def __init__(self, msg, line=None):
        if line is not None:
            raise RuntimeError(bcolors.BOLD + bcolors.OKGREEN + "Line:" + str(line) + "->" + msg + bcolors.ENDC)
        else:
            raise RuntimeError(bcolors.BOLD + bcolors.OKGREEN + "->" + msg + bcolors.ENDC)


# AST Type Nodes
class NodeInt(Node):
    def __init__(self):
        self.size = 4


class NodeId(Node):
    def __init__(self, idname, line=None):
        global EBPoffsetTable, typeTable
        self.idname = idname
        if local_EBPoffsetTable is not None:
            if self.idname in local_EBPoffsetTable:
                self.val = EBPoffsetTable[self.idname] + "(%ebp)"
                self.nodeType = local_typeTable[self.idname]
        elif self.idname in EBPoffsetTable:
            self.val = "$" + self.idname
            self.nodeType = typeTable[self.idname]
        else:
            NodeError("Symbol " + self.idname + " is not declared!", line)


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
    def __init__(self, elmNode, expr=None, givenType=None):
        self.rval = expr
        self.lval = elmNode
        self.idname = None # Eliminar
        self.nodeType = givenType

    def declare(self, line, givenType=None):
        global EBPoffsetTable, counterEBP, typeTable
        global local_EBPoffsetTable, local_counterEBP, local_typeTable
        # Obtain type and its size
        if givenType is not None:
            self.nodeType = givenType
        varSize = self.nodeType.size

        # Obtain array size multiplier and ID name
        if isinstance(self.lval, NodeArray):
            super().Write("movl $1, %eax")
        while isinstance(self.lval, NodeArray):
            self.nodeType = NodePointer(self.nodeType)
            if isinstance(self.lval.indxVal, NodeNum):
                sizeMult = "$" + self.lval.indxVal.val
                varSize *= self.lval.indxVal.numVal
            elif isinstance(self.lval.indxVal, NodeId):
                sizeMult = EBPoffsetTable[self.lval.indxVal.val] + "(%ebp)"
            else:
                super().Write("popl %ebx")
                sizeMult = "%ebx"
            super().Write("imul " + sizeMult)
            self.lval = self.lval.refNode

        # Obtain name and check table
        self.idname = self.lval
        if local_EBPoffsetTable is None:
            if self.idname in EBPoffsetTable:
                NodeError("Symbol " + self.idname + " is already declared!", line)
            else:
                # Create table entries in Global Scope
                typeTable[self.idname] = self.nodeType
                EBPoffsetTable[self.idname] = str(counterEBP)

                # Initialize if necessary
                if self.rval is not None:
                    if isinstance(self.rval, NodeId):
                        strOp1 = self.rval.val + "(%ebp)"
                    elif isinstance(self.rval, NodeNum):
                        strOp1 = "$" + self.rval.val
                    elif isinstance(self.rval, NodeAssign):
                        strOp1 = self.rval.lvalStr
                    else:
                        super().Write("popl %eax", "Pop assignment value")
                        strOp1 = "%eax"

                    super().Write("movl " + strOp1 + ", $" + self.idname,
                                  self.idname + " = assignment")
        else:
            if self.idname in local_EBPoffsetTable:
                NodeError("Symbol " + self.idname + " is already declared", line)
            else:
                # Create table entries in Local Scope
                local_typeTable[self.idname] = self.nodeType
                local_EBPoffsetTable[self.idname] = str(local_counterEBP)

                # Reserve space and update counter
                local_counterEBP = local_counterEBP - varSize
                super().Write("subl $" + str(varSize) + ", %esp",
                              "Reserve space for " + self.idname + " (offset=" + local_EBPoffsetTable[self.idname] + ")")

                # Initialize if necessary
                if self.rval is not None:
                    if isinstance(self.rval, NodeId):
                        strOp1 = self.rval.val + "(%ebp)"
                    elif isinstance(self.rval, NodeNum):
                        strOp1 = "$" + self.rval.val
                    elif isinstance(self.rval, NodeAssign):
                        strOp1 = self.rval.lvalStr
                    else:
                        super().Write("popl %eax", "Pop assignment value")
                        strOp1 = "%eax"

                    super().Write("movl " + strOp1 + ", " + local_EBPoffsetTable[self.idname] + "(%ebp)",
                                  self.idname + " = assignment")


class NodeAssign(Node):
    def __init__(self, lval, expr, line):
        global EBPoffsetTable
        if not isinstance(expr.nodeType, type(lval.nodeType)):
            NodeError("Incompatible assignation types!", line)
        else:
            self.nodeType = lval.nodeType
            if isinstance(lval, NodeNum):
                NodeError("Left member of assignment is not a valid L-Value!", line)
            else:
                # Get Rval
                if isinstance(expr, NodeId):
                    assignment = expr.val
                elif isinstance(expr, NodeNum):
                    assignment = "$" + expr.val
                elif isinstance(expr, NodeAssign):
                    assignment = expr.lvalStr
                else:
                    super().Write("popl %eax", "Pop assignment value")
                    assignment = "%eax"

                # Get Lval
                if local_EBPoffsetTable is None:
                    if isinstance(lval, NodeId):
                        self.lvalStr = lval.val
                        super().Write("movl " + assignment + ", " + self.lvalStr,
                                      lval.idname + " = assignment")
                    elif isinstance(lval, NodeAssign):
                        self.lvalStr = lval.lvalStr
                        super().Write("movl " + assignment + ", " + self.lvalStr,
                                      self.lvalStr + " = assignment")
                    else:
                        super().Write("popl %ebx", "Pop lval (address)")
                        self.lvalStr = "%ebx"
                        super().Write("movl " + assignment + ", PTR [" + self.lvalStr + "]",
                                      "Assign rval to where lval points")
                else:
                    if isinstance(lval, NodeId):
                        self.lvalStr = lval.val
                        super().Write("movl " + assignment + ", " + self.lvalStr,
                                      lval.idname + " = assignment")
                    elif isinstance(lval, NodeAssign):
                        self.lvalStr = lval.lvalStr
                        super().Write("movl " + assignment + ", " + self.lvalStr,
                                      self.lvalStr + " = assignment")
                    else:
                        super().Write("popl %ebx", "Pop lval (address)")
                        self.lvalStr = "%ebx"
                        super().Write("movl " + assignment + ", PTR [" + self.lvalStr + "]",
                                      "Assign rval to where lval points")


class NodeIntCons(Node):
    def __init__(self):
        self.nodeType = NodeInt()


class NodeArithmBinOp(Node):
    def __init__(self, p1, p2, op, line=None):
        # Type Checking
        if not isinstance(p1.nodeType, type(p2.nodeType)):
            NodeError("Incompatible type of the operands!", line)
        else:
            self.nodeType = p1.nodeType

        # Operand 2
        if isinstance(p2, NodeId):
            super().Write("movl " + p2.val + ", %ebx", "Operand " + p2.idname + " (offset=" + p2.val + ")")
            p2str = "%ebx"
        elif isinstance(p2, NodeNum):
            p2str = "$" + p2.val
        else:
            super().Write("popl " + "%ebx", "Pop second operand from stack")
            p2str = "%ebx"

        # Operand 1
        if isinstance(p1, NodeId):
            super().Write("movl " + p1.val + ", %eax", "Operand " + p1.idname + " (offset=" + p1.val + ")")
        elif isinstance(p1, NodeNum):
            super().Write("movl $" + p1.val + ", %eax")
        else:
            super().Write("popl " + "%eax", "Pop first operand from stack")

        # Operation
        if op == '+':
            super().Write("addl " + p2str + ', %eax')
            super().Write("pushl %eax", "Push addition result")
        elif op == '-':
            super().Write("subl " + p2str + ', %eax')
            super().Write("pushl %eax", "Push substraction result")
        elif op == '*':
            super().Write("imull " + p2str + ', %eax')
            super().Write("pushl %eax", "Push multiplication result")
        elif op == '/':
            super().Write("cdq")
            super().Write("idivl " + p2str)
            super().Write("pushl %eax", "Push division result")
        elif op == '%':
            super().Write("cdq")
            super().Write("idivl " + p2str)
            super().Write("pushl %ebx", "Push modulus result")


class NodeRelationalBinOp(Node):
    def __init__(self, p1, p2, op, line):
        self.ID = newLabelID()

        # Type Checking
        if not isinstance(p1.nodeType, type(p2.nodeType)):
            NodeError("Incompatible type of the operands!", line)
        else:
            self.nodeType = p1.nodeType

        # Operand 2
        if isinstance(p2, NodeId):
            super().Write("movl " + p2.val + ", %ebx", "Operand " + p2.idname + " (offset=" + p2.val + ")")
            p2str = "%ebx"
        elif isinstance(p2, NodeNum):
            p2str = "$" + p2.val
        else:
            super().Write("popl " + "%ebx", "Pop second operand")
            p2str = "%ebx"

        # Operand 1
        if isinstance(p1, NodeId):
            p1str = p1.val
        elif isinstance(p1, NodeNum):
            p1str = "$" + p1.val
        else:
            super().Write("popl " + "%eax", "Pop first operand")
            p1str = "%eax"

        # Operation
        super().Write("movl $1, %ecx", "Assume condition is true")
        super().Write("cmp " + p1str + ", " + p2str, "Compare both Operands")
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

        super().Write("movl $0, %ecx","Reached if condition is false, set result as false")
        super().WriteLabel("condTrue" + str(self.ID))
        super().Write("pushl %ecx", "Push result")


class NodeLogical(Node):
    def __init__(self, op):
        self.op = op
        self.ID = newLabelID()
        self.nodeType = None

    def firstOperand(self, p):
        self.nodeType = p.nodeType
        if isinstance(p, NodeId):
            super().Write("movl " + p.val + ", %eax", "(" + self.op + " operator) Operand " + p.idname + " (offset=" + p.val + ")")
            operand = "%eax"
        elif isinstance(p, NodeNum):
            operand = "$" + p.val
        else:
            super().Write("popl " + "%eax", "(" + self.op + " operator) Pop first operand")
            operand = "%eax"

        super().Write("cmpl " + "$0, " + operand, "check if first operand is false")
        if self.op == '&&':
            super().Write("pushl $0", "assume first operand is false")
            super().Write("je shortcut" + str(self.ID), "if first operand is false, jump to end")
        elif self.op == '||':
            super().Write("pushl $1", "assume first operand is true")
            super().Write("jne shortcut" + str(self.ID), "if first operand is true, jump to end")

    def secondOperand(self, p):
        self.nodeType = p.nodeType
        if isinstance(p, NodeId):
            super().Write("movl " + p.val + ", %eax", "(" + self.op + " operator) Operand " + p.idname + " (offset=" + p.val + ")")
            operand = "%eax"
        elif isinstance(p, NodeNum):
            operand = "$" + p.val
        else:
            super().Write("popl " + "%eax", "(" + self.op + " operator) Pop second operand")
            operand = "%eax"

        super().Write("cmpl " + "$0, " + operand, "check if second operand is false")
        if self.op == '&&':
            super().Write("movl $0, %eax", "assume operator && result is False")
            super().Write("je shortcut" + str(self.ID), "if second operand is False, jump")
            super().Write("movl $1, %eax", "else, negate assumption")
        elif self.op == '||':
            super().Write("movl $1, %eax", "assume operator || result is True")
            super().Write("jne shortcut" + str(self.ID), "if second operand is True, jump")
            super().Write("movl $0, %eax", "else, negate assumption")
        super().Write("popl %ebx", "Remove result of first operand")
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
                super().Write("movl " + p1.val + ", %eax", "(! operator) " + p1.val + " = " + p1.idname)
            elif isinstance(p1, NodeNum):
                super().Write("movl $" + p1.val + ", %eax")
            else:
                super().Write("popl " + "%eax", "(! operator) Pop unary operand")

            super().Write("cmp $0, %eax", "Check if operand is false")
            super().Write("movl $1, %eax", "Set as true (negation)")
            labelID = str(newLabelID())
            super().Write("je " + "negFinal" + labelID, "Jump if false")
            super().Write("movl $0, %eax", "Set as false (negation)")
            super().WriteLabel("negFinal" + labelID)
            super().Write("puslh %eax", "Push result")

        elif op == '-':
            if not isinstance(p1.nodeType, NodeInt):
                NodeError("Incompatible type for unary minus operand!", line)
            else:
                self.nodeType = p1.nodeType

            # Operand
            if isinstance(p1, NodeId):
                super().Write("movl " + p1.val + ", %eax", "(Unary -) " + p1.val + " = " + p1.idname)
            elif isinstance(p1, NodeNum):
                super().Write("movl $" + p1.val + ", %eax")
            else:
                super().Write("popl " + "%eax", "(! operator) Pop unary operand")

            super().Write("imul $-1")
            super().Write("pushl %eax")
        else:
            raise RuntimeError('Invalid operation')


class NodeUnaryRefs(Node):
    def __init__(self, p1, op, line, offsetExpr=None):
        global EBPoffsetTable, typeTable
        self.op = op
        self.p1 = p1

        if op == '&':
            if isinstance(p1, NodeId):
                self.nodeType = NodePointer(p1.nodeType)
                super().Write("movl " + p1.val + ", %eax", "(& Operator) %eax = " + p1.idname)
            elif isinstance(p1, NodeNum):
                NodeError("Reference '&' operator can only be applied to variable identifers", line)
            else:
                super().Write("popl %eax", "(& Operator) Pop unary operand")
            super().Write("leal %eax, %eax", "Obtain operand's effective address")
            super().Write("pushl %eax","Push result")

        elif op == '*':
            if not isinstance(p1.nodeType, NodePointer):
                NodeError("Operand is not a pointer!", line)
            else:
                self.nodeType = p1.nodeType.refNode

            if isinstance(p1, NodeNum):
                NodeError("Operand is not a pointer!", line)
            elif isinstance(p1, NodeId):
                super().Write("movl " + p1.val + ", %eax", "(* Operator) %eax = " + p1.idname)
            else:
                super().Write("popl %eax", "(* Operator) Pop unary operand")
            super().Write("movl PTR [%eax], %eax", "Dereference pointer")
            super().Write("pushl %eax", "Push result")

        elif op == '[]':
            if not isinstance(p1.nodeType, NodePointer):
                NodeError("Is not a pointer!", line)
            else:
                self.nodeType = p1.nodeType.refNode

            # Calculate Offset
            if isinstance(offsetExpr, NodeNum):
                offset = "$" + offsetExpr.val
            elif isinstance(offsetExpr, NodeId):
                offset = offsetExpr.val
            else:
                super().Write("popl %eax", "([] Operator) Pop offset literal")
                offset = "%eax"
            super().Write("imul $" + str(p1.nodeType.size) + ", " + offset, "Calculate Offset")
            super().Write("movl %eax, %ebx", "Store Offset in ebx")

            # Obtain base address
            if isinstance(p1, NodeNum):
                NodeError("Operand is not a pointer!", line)
            elif isinstance(p1, NodeId):
                super().Write("movl " + p1.val + ", %eax", "([] Operator) %eax = " + p1.idname)
            else:
                super().Write("popl %eax", "([] Operator) Pop unary operand")

            super().Write("addl %ebx", "Address = Pointer + Offset")
            super().Write("movl PTR [%eax], %eax", "Dereference Address")
            super().Write("pushl %eax", "Push result")
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

    def compare(self, expr):
        if isinstance(expr, NodeId):
            super().Write("movl " + expr.val + ", %eax", "Condition " + expr.idname + " (offset=" + expr.val + ")")
        elif isinstance(expr, NodeNum):
            super().Write("movl $" + expr.val + ", %eax", "Condition = " + expr.val)
        else:
            super().Write('popl %eax', "Pop condition value")

        super().Write('cmpl $0, %eax', "Compare IF condition")
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

    def compare(self, expr):
        if isinstance(expr, NodeId):
            super().Write("movl " + expr.val + ", %eax",
                          "Condition " + expr.idname + " (offset=" + expr.val + ")")
        elif isinstance(expr, NodeNum):
            super().Write("movl $" + expr.val + ", %eax", "Condition = " + expr.val)
        else:
            super().Write('popl %eax', "Pop condition value")

        super().Write('cmpl $0, %eax', "Compare WHILE condition")
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

        # Create local tables
        global typeTable, local_EBPoffsetTable, local_typeTable
        funcArgs = typeTable[name][1]

        local_ParamEBP = 8
        local_EBPoffsetTable = {}
        local_typeTable = {}
        if funcArgs is not None:
            for arg in reversed(funcArgs):
                local_EBPoffsetTable[arg.lval] = str(local_ParamEBP)
                local_typeTable[arg.lval] = arg.nodeType
                local_ParamEBP += 4


class NodeFunctionEpilogue(Node):
    def __init__(self):
        super().Write('movl %ebp, %esp', "Function Epilogue")
        super().Write('popl %ebp')
        super().Write('ret\n')

        # Reset local tables
        global local_EBPoffsetTable, local_typeTable, local_counterEBP

        local_EBPoffsetTable.clear()
        local_typeTable.clear()

        local_EBPoffsetTable = None
        local_typeTable = None
        local_counterEBP = -4


class NodeFunctionCall(Node):
    def __init__(self, name, argc, paramTypes, line):

        global typeTable
        # Check only for functions that are not printf or scanf
        if name != 'printf' and name != 'scanf':
            argTypes = typeTable[name]
            self.nodeType = argTypes[0] # Get function return type
            if paramTypes is not None:
                argTypes = argTypes[1] # Get parameters type list
                if argTypes is None or len(argTypes) != argc:
                    NodeError("Invalid number of arguments", line)
                else:
                    for arg in range(0, len(argTypes)):
                        if not isinstance(argTypes[arg].nodeType, type(paramTypes[arg].nodeType)):
                            NodeError("Unexpected types for arguments when calling function " + name, line)
            else:
                if argTypes[1] is not None:
                    NodeError("Unexpected types for arguments when calling function " + name, line)
        super().Write('call ' + name)
        if argc > 0:
            super().Write('addl $' + str(argc * 4) + ', %esp')
        super().Write('pushl %eax')


class NodeFunctionParam(Node):
    def __init__(self, arg):
        # Code writing
        if isinstance(arg, int):  # cadena
            super().Write('pushl ' + '$s' + str(arg))
        elif isinstance(arg, NodeNum):  # literal
            super().Write('pushl $' + arg.val)
        elif isinstance(arg, NodeId):  # literal
            super().Write('pushl ' + arg.val + '%(ebp)')
        elif isinstance(arg, NodeFunctionCall) or isinstance(arg, NodeUnaryOp) or isinstance(arg,
                                                                                             NodeArithmBinOp):  # resultado de función o expresión
            pass
        else:
            pass


class NodeReturn(Node):
    def __init__(self, exprNode):
        if isinstance(exprNode, NodeId):
            super().Write("movl " + exprNode.val + ", %eax", "Move return value")
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
            node.declare(p.lineno, p[0])

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
        node.compare(p.expr)
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

        NodeFunctionCall('printf', len(p[4]) + 1, p[4], p.lineno)

        NodePrint(p.lineno, p.STRING, p.callParams)

    @_('PRINTF "(" STRING ")" ";" ')
    def instruction(self, p):
        global strings
        strings.append(p[2])
        NodeFunctionParam(len(strings) - 1)

        NodeFunctionCall('printf', 1, None, p.lineno)

        NodePrint(p.lineno, p.STRING)

    @_('SCANF "(" STRING "," scanfParams ")"')
    def num(self, p):
        global strings
        strings.append(p[2])
        NodeFunctionParam(len(strings) - 1)

        node = NodeFunctionCall('scanf', len(p[4]) + 1, None, p.lineno)
        NodeScan(p.lineno, p.STRING, p.scanfParams)
        return node

    # User Functions
    @_('type ID',
       'VOID ID')
    def param(self, p):
        node = NodeDeclarationAssign(p[1], None, p[0])
        return node

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
        return p[2]  # La lista resultante está al revés

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

    @_('expr "," scanfParams')
    def scanfParams(self, p):
        NodeFunctionParam(p[0])
        p[2].append(p.address)
        return p[2]

    @_('expr')
    def scanfParams(self, p):
        NodeFunctionParam(p[0])
        return [p[0]]

    @_('ID "(" callParams ")"')
    def num(self, p):
        if p[0] in self.functions:
            return NodeFunctionCall(p[0], len(p[2]), p[2], p.lineno)
        else:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a Function')

    @_('ID "(" ")"')
    def num(self, p):
        if p[0] in self.functions:
            return NodeFunctionCall(p[0], 0, None, p.lineno)
        else:
            raise RuntimeError('line ' + str(p.lineno) + ': ' + p[0] + ' is not a Function')

    @_('RETURN expr ";"')
    def retInstruction(self, p):
        NodeReturn(p[1])
        return

    @_('type ID "(" params ")"',
       'type ID "(" typeDec ")"')
    def functionDecl(self, p):
        global typeTable
        typeTable[p[1]] = [p[0], p[3]]
        return p[1]

    @_( 'type ID "(" ")"')
    def functionDecl(self, p):
        global typeTable
        typeTable[p[1]] = [p[0], None]
        return p[1]

    @_('VOID ID "(" params ")"',
       'VOID ID "(" typeDec ")"')
    def voidFunctionDecl(self, p):
        global typeTable
        typeTable[p[1]] = [p[0], p[3]]
        return p[1]

    @_('VOID ID "(" ")"')
    def voidFunctionDecl(self, p):
        global typeTable
        typeTable[p[1]] = [p[0], None]
        return p[1]

    @_('functionDecl ";"',
       'voidFunctionDecl ";"')
    def instruction(self, p):
        if p[0] in self.functions:
            NodeError('Redeclaration of function ' + p[0] + ' is not allowed', p.lineno)
        else:
            if p[0] in EBPoffsetTable:
                NodeError(p[0] + ' is already declared as a variable', p.lineno)
            else:
                self.functions[p[0]] = 0
        return 0

    @_('functionDecl "{"')
    def functDefInit(self, p):
        self.functions[p[0]] = 0
        NodeFunctionPrologue(p[0])
        return 0

    @_('voidFunctionDecl "{"')
    def voidfunctDefInit(self, p):
        self.functions[p[0]] = 0
        NodeFunctionPrologue(p[0])
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

    # Relational Operations
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
        return NodeNum(p[0], NodeInt(), p.lineno)

    @_('ID')
    def num(self, p):
        return NodeId(p[0], p.lineno)

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
            print("Syntax error at EOF, check for any missing semicolon")


if __name__ == '__main__':
    EBPoffsetTable = {}
    typeTable = {}
    local_typeTable = None
    local_EBPoffsetTable = None
    counterEBP = -4
    local_counterEBP = -4
    counterString = 0
    strings = []
    lexer = CLexer()
    parser = CParser()
    Node.outputFilename = "OutputFinal.s"
    open(Node.outputFilename, 'w').close()

    text = open("SourceFinal.c").read()
    tokenizedText = lexer.tokenize(text)
    # print("\n =========[ Lexer ] ===========")
    # for token in tokenizedText:
        # print("token:", token.type, ", lexvalue:", token.value)

    print("\n =========[ Parser ] ============")
    try:
        parser.parse(lexer.tokenize(text))
        print("========== [ Fin ]===============")
    except RuntimeError as e:
        print(e)
