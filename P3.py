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
    tokens = {PRINT, BOOLVAL, ASSIGN, AND, OR, NOT, ID}
    literals = {';', '(', ')'}

    # Tokens
    BOOLVAL = r'true | TRUE | false | FALSE'
    ASSIGN = ':='
    AND = r'and | AND'
    OR = r'or | OR'
    NOT = r'not | NOT'
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'

    ignore_space = r' '
    ignore_tabs = r'\t'
    ignore_comments = r'//.*'

    # Reserved keywords
    ID['print'] = PRINT

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


    # Program structure
    @_('instruction sentence')
    def sentence(self, p):
        return

    @_('')
    def sentence(self, p):
        return

    @_('ID ASSIGN expr ;')
    def instruction(self, p):
        return

    @_('PRINT expr ;')
    def instruction(self, p):
        return

    # Operations
    @_('logicalAND logicalORPrima')
    def logicalOR (self, p):
        return

    @_('OR logicalAND logicalORPrima')
    def logicalORPrima(self, p):
        return

    @_('')
    def logicalORPrima(self, p):
        return

    @_('unary logicalANDPrima')
    def logicalAND(self, p):
        return

    @_('AND unary logicalANDPrima')
    def logicalANDPrima(self, p):
        return

    @_('')
    def logicalANDPrima(self, p):
        return

    @_('NOT unary')
    def unary(self, p):
        return

    @_('bool')
    def unary(self, p):
        return

    @_('( expr )')
    def bool(self, p):
        return

    @_('BOOLVAL')
    def bool(self, p):
        return

    @_('ID')
    def bool(self, p):
        return

    @_('logicalOR')
    def expr(self, p):
        return