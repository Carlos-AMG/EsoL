from utils import string_with_arrows

# errors
class Error:
    def __init__(self, pos_start, pos_end, error_name, details) -> None:
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name 
        self.details = details

    def as_string(self):
        result  = f'{self.error_name}: {self.details}\n'
        result += f'File {self.pos_start.fn}, line {self.pos_start.ln + 1}'
        result += '\n\n' + string_with_arrows(self.pos_start.ftxt, self.pos_start, self.pos_end)
        return result
    
class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details) -> None:
        super().__init__(pos_start, pos_end, "Illegal character", details=details) 

class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details="") -> None:
        super().__init__(pos_start, pos_end, "Invalid Syntax" , details)
    
class RTError(Error):
    def __init__(self, pos_start, pos_end, details="") -> None:
        super().__init__(pos_start, pos_end, "Runtime Error", details)

# idx -> index
# ln -> line number
# col -> column number
class Position:
    def __init__(self, idx, ln, col, fn, ftxt):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.fn = fn
        self.ftxt = ftxt

    def advance(self, current_char=None):
        self.idx += 1
        self.col += 1
        if current_char == '\n':
            self.ln += 1
            self.col = 0
        return self
    
    def copy(self):
        return Position(self.idx, self.ln, self.col, self.fn, self.ftxt)
    

# tokens and class token
DIGITS = "0123456789"

TT_INT = "TT_INT"
TT_FLOAT = "FLOAT"
TT_PLUS = "PLUS"
TT_MINUS = "MINUS"
TT_MUL = "MUL"
TT_DIV = "DIV"
TT_LPAREN = "LPAREN"
TT_RPAREN = "RPAREN"
TT_EOF = "EOF"

class Token:
    def __init__(self, type_, value=None, pos_start=None, pos_end=None) -> None:
        self.type = type_
        self.value = value
        if pos_start:
            self.pos_start = pos_start.copy()
            self.pos_end = pos_start.copy()
            self.pos_end.advance()
        if pos_end:
            self.pos_end = pos_end
    def __repr__(self):
        if self.value: 
            return f'{self.type}:{self.value}'
        return f'{self.type}'
    
# Lexer section
class Lexer:
    def __init__(self, fn, text) -> None:
        self.fn = fn
        self.text = text
        self.pos = Position(-1, 0, -1, fn, text)
        self.current_char = None
        self.advance()

    def advance(self):
        self.pos.advance(self.current_char)
        self.current_char = self.text[self.pos.idx] if self.pos.idx < len(self.text) else None

    def make_tokens(self):
        tokens = []
        while self.current_char != None:
            if self.current_char in " \t":
                self.advance()
            elif self.current_char in DIGITS:
                tokens.append(self.make_number())
            elif self.current_char == "+":
                tokens.append(Token(TT_PLUS, pos_start=self.pos))
                self.advance()
            elif self.current_char == "-":
                tokens.append(Token(TT_MINUS,  pos_start=self.pos))
                self.advance()
            elif self.current_char == "*":
                tokens.append(Token(TT_MUL,  pos_start=self.pos))
                self.advance()
            elif self.current_char == "/":
                tokens.append(Token(TT_DIV, pos_start=self.pos))
                self.advance()
            elif self.current_char == "(":
                tokens.append(Token(TT_LPAREN,  pos_start=self.pos))
                self.advance()
            elif self.current_char == ")":
                tokens.append(Token(TT_RPAREN,  pos_start=self.pos))
                self.advance()
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                return [], IllegalCharError(pos_start, self.pos, "'" + char + "'")
        tokens.append(Token(TT_EOF, pos_start=self.pos))
        return tokens, None

    def make_number(self):
        num_str = ""
        dot_count = 0
        pos_start = self.pos.copy()
        while self.current_char != None and self.current_char in DIGITS + ".":
            if self.current_char == ".":
                if dot_count == 1: 
                    break
                dot_count += 1
                num_str += "."
            else: 
                num_str += self.current_char
            self.advance()
        
        if dot_count == 0:
            return Token(TT_INT, int(num_str), pos_start, self.pos)
        else:
            return Token(TT_FLOAT, float(num_str), pos_start, self.pos)
        
# nodes

class NumberNode:
    def __init__(self, token) -> None:
        self.token = token
        self.pos_start = self.token.pos_start 
        self.pos_end = self.token.pos_end
    def __repr__(self) -> str:
        return f'{self.token}'

# op_token -> operator_token
class BinOpNode:
    def __init__(self, left_node, right_node, op_token) -> None:
        self.left_node = left_node
        self.right_node = right_node
        self.op_token = op_token
        self.pos_start = self.left_node.pos_start
        self.pos_end = self.right_node.pos_end

    def __repr__(self) -> str:
        return f'({self.left_node}, {self.op_token}, {self.right_node})'
    
class UnaryOpNode:
    def __init__(self, op_token, node) -> None:
        self.op_token = op_token
        self.node = node
        self.pos_start = self.op_token.pos_start
        self.pos_end = self.node.pos_end
    
    def __repr__(self) -> str:
        return f'({self.op_token}, {self.node})'

# Parse result

class ParseResult:
    def __init__(self):
        self.error = None
        self.node = None

    def register(self, result):
        if isinstance(result, ParseResult):
            if result.error:
                self.error = result.error
            return result.node
        return result
    
    def success(self, node):
        self.node = node
        return self
    
    def failure(self, error):
        self.error = error
        return self


# Parser class
class Parser:
    def __init__(self, tokens) -> None:
        self.tokens = tokens
        self.tok_idx = -1
        self.advance()

    def advance(self):
        self.tok_idx += 1
        if self.tok_idx < len(self.tokens):
            self.current_token = self.tokens[self.tok_idx]
        
        return self.current_token
    
    # methods
    def parse(self):
        result = self.expr()
        if not result.error and self.current_token.type != TT_EOF:
            return result.failure(InvalidSyntaxError(self.current_token.pos_start, self.current_token.pos_end,
                "Expected '+', '-', '*' or '/'"))
        return result
    
    def factor(self):
        result = ParseResult()
        token = self.current_token

        if token.type in (TT_PLUS, TT_MINUS):
            result.register(self.advance())
            factor = result.register(self.factor())
            if result.error:
                print("It will error")
                return result
            return result.success(UnaryOpNode(token, factor))

        elif token.type in (TT_INT, TT_FLOAT):
            result.register(self.advance())
            return result.success(NumberNode(token))
        elif token.type == TT_LPAREN:
            result.register(self.advance())
            expr = result.register(self.expr())
            if result.error:
                return result
            if self.current_token.type == TT_RPAREN:
                result.register(self.advance())
                return result.success(expr)
            else:
                return result.failure(InvalidSyntaxError(self.current_token.pos_start, self.current_token.pos_end, "Expected ')'"))
            


        return result.failure(InvalidSyntaxError(token.pos_start, token.pos_end, "Expected int or float"))

    def term(self):
        return self.bin_op(self.factor, (TT_MUL, TT_DIV))

    def expr(self):
        return self.bin_op(self.term, (TT_PLUS, TT_MINUS))
    
    def bin_op(self, func, ops):
        """Because both expr and term have the same grammar, they share the same function only differing on what the BinOpNode will contain
        So we modularize this into a single function that handles both cases"""
        result = ParseResult()
        left = result.register(func())
        if result.error:
            return result 
        while self.current_token.type in ops:
            op_token = self.current_token
            result.register(self.advance())
            right = result.register(func())
            if result.error:
                return result
            left = BinOpNode(left, right, op_token)
        # print(result.error)
        return result.success(left)
    
# Runtime Result
class RTResult:
    def __init__(self) -> None:
        self.value = None
        self.error = None
    def register(self, result):
        if result.error:
            self.error = result.error
        return result.value
    def success(self, value):
        self.value = value
        return self
    
    def failure(self, error):
        self.error = error 
        return self

# values
class Number:
    def __init__(self, value) -> None:
        self.value = value
    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self
    def added_to(self, other):
        if isinstance(other, Number):
            return Number(self.value + other.value), None
    def subbed_by(self, other):
        if isinstance(other, Number):
            return Number(self.value - other.value), None
    def multiplied_by(self, other):
        if isinstance(other, Number):
            return Number(self.value * other.value), None
    def divided_by(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RTError(other.pos_start, other.pos_end, "Division by zero")
            return Number(self.value / other.value), None 
    def __repr__(self) -> str:
        return str(self.value)
    
# context
class Context:
    def __init__(self, display_name, parent_context=None, parent_entry_pos=None) -> None:
        self.display_name = display_name
        self.parent_context = parent_context
        self.parent_entry_pos = parent_entry_pos

#interpeter
class Interpreter:
    def visit(self, node):
        # visit all nodes based on type
        method_name = f'visit_{type(node).__name__}'
        method = getattr(self, method_name, self.no_visit_method)
        return method(node)
    def no_visit_method(self, node):
        raise Exception(f"no visit_{type(node).__name__} method defined")
    
    def visit_NumberNode(self, node):
        return RTResult().success(
            Number(node.token.value).set_pos(node.pos_start, node.pos_end)
        )
    def visit_BinOpNode(self, node):
        res = RTResult()
        left = res.register(self.visit(node.left_node))
        if res.error:
            return res
        right = res.register(self.visit(node.right_node))
        if res.error:
            return res

        if node.op_token.type == TT_PLUS:
            result, error = left.added_to(right)
        elif node.op_token.type == TT_MINUS:
            result, error = left.subbed_by(right)
        elif node.op_token.type == TT_MUL:
            result, error = left.multiplied_by(right)
        elif node.op_token.type == TT_DIV:
            result, error = left.divided_by(right)

        if error:
            return res.failure(error)
        else:
            return res.success(result.set_pos(node.pos_start, node.pos_end))
    
    def visit_UnaryOpNode(self, node):
        res = RTResult()
        number = res.register(self.visit(node.node))
        if res.error:
            return res
        if node.op_token.type == TT_MINUS:
            number, error = number.multiplied_by(Number(-1))
        if error:
            return res.failure(error)
        else:
            return res.success(number.set_pos(node.pos_start, node.pos_end))

# run segment        
def run(fn, text):
    # Generate tokens
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
        return None, error
    
    # print("Tokens: ", tokens)

    # Generate AST (Abstract Syntax Tree)
    parser = Parser(tokens)
    ast = parser.parse()
    if ast.error:
        return None, ast.error
    
    # run program
    interpreter = Interpreter()
    context = Context("<program>")
    result =  interpreter.visit(ast.node)
    return result.value, result.error