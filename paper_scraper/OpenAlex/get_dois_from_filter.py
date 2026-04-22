from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger
from pyalex import Works, Concepts, Topics
from paper_scraper import OpenAlex

OpenAlexOptions = OpenAlex.Options.Options


@dataclass
class SearchFilter:
    topics: str | list[str] | None = None
    keywords: str | list[str] | None = None
    year_min: int | None = None
    year_max: int | None = None
    open_access_only: bool = True
    max_papers: int = 1000


@dataclass
class ASTNode:
    pass


@dataclass
class IdNode(ASTNode):
    id: str


@dataclass
class KeywordNode(ASTNode):
    keyword: str


@dataclass
class NotNode(ASTNode):
    child: ASTNode


@dataclass
class AndNode(ASTNode):
    left: ASTNode
    right: ASTNode


@dataclass
class OrNode(ASTNode):
    left: ASTNode
    right: ASTNode


class TokenType:
    ID = "ID"
    KEYWORD = "KEYWORD"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass
class Token:
    type: str
    value: str | None = None


class Tokenizer:
    OPERATORS = {"and", "or", "not", "&&", "||", "!"}
    LPAREN = {"(", "["}
    RPAREN = {")", "]"}

    def __init__(self, expression: str):
        self.expression = expression.strip()
        self.pos = 0
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.expression):
            self._skip_whitespace()
            if self.pos >= len(self.expression):
                break

            char = self.expression[self.pos]

            if char in self.LPAREN:
                self.tokens.append(Token(TokenType.LPAREN, char))
                self.pos += 1
            elif char in self.RPAREN:
                self.tokens.append(Token(TokenType.RPAREN, char))
                self.pos += 1
            elif char == "&":
                if (
                    self.pos + 1 < len(self.expression)
                    and self.expression[self.pos + 1] == "&"
                ):
                    self.tokens.append(Token(TokenType.AND, "&&"))
                    self.pos += 2
                else:
                    raise ValueError(f"Unexpected character '&' at position {self.pos}")
            elif char == "|":
                if (
                    self.pos + 1 < len(self.expression)
                    and self.expression[self.pos + 1] == "|"
                ):
                    self.tokens.append(Token(TokenType.OR, "||"))
                    self.pos += 2
                else:
                    raise ValueError(f"Unexpected character '|' at position {self.pos}")
            elif char in {'"', "'"}:
                self._read_quoted_keyword(char)
            elif char.isalnum() or char in {"T", "C"}:
                self._read_id_or_keyword()
            else:
                raise ValueError(
                    f"Unexpected character '{char}' at position {self.pos}"
                )

        self.tokens.append(Token(TokenType.EOF))
        return self.tokens

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.expression) and self.expression[self.pos].isspace():
            self.pos += 1

    def _read_quoted_keyword(self, quote_char: str) -> None:
        self.pos += 1
        start = self.pos
        while (
            self.pos < len(self.expression) and self.expression[self.pos] != quote_char
        ):
            self.pos += 1

        if self.pos >= len(self.expression):
            raise ValueError(f"Unclosed quote at position {start}")

        keyword = self.expression[start : self.pos]
        self.pos += 1
        self.tokens.append(Token(TokenType.KEYWORD, keyword))

    def _read_id_or_keyword(self) -> None:
        start = self.pos
        while self.pos < len(self.expression) and (
            self.expression[self.pos].isalnum()
            or self.expression[self.pos] in {"_", "-"}
        ):
            self.pos += 1

        value = self.expression[start : self.pos]

        if value.lower() in self.OPERATORS:
            if value.lower() in ("and", "&&"):
                self.tokens.append(Token(TokenType.AND, value))
            elif value.lower() in ("or", "||"):
                self.tokens.append(Token(TokenType.OR, value))
            elif value.lower() in ("not", "!"):
                self.tokens.append(Token(TokenType.NOT, value))
            else:
                raise ValueError(f"Unknown operator '{value}' at position {start}")
        elif not value.startswith(("T", "C")):
            self.tokens.append(Token(TokenType.KEYWORD, value))
        else:
            self.tokens.append(Token(TokenType.ID, value))


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> ASTNode:
        if self._current().type == TokenType.EOF:
            raise ValueError("Empty expression")

        result = self._parse_expr()

        if self._current().type != TokenType.EOF:
            raise ValueError(
                f"Unexpected token '{self._current().value}' at position {self.pos}"
            )

        return result

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _expect(self, token_type: str) -> Token:
        if self._current().type != token_type:
            raise ValueError(
                f"Expected {token_type}, got {self._current().type} "
                f"('{self._current().value}') at position {self.pos}"
            )
        return self._advance()

    def _parse_expr(self) -> ASTNode:
        left = self._parse_term()

        while self._current().type in (TokenType.AND, TokenType.OR):
            op = self._advance().type
            right = self._parse_term()
            if op == TokenType.AND:
                left = AndNode(left, right)
            else:
                left = OrNode(left, right)

        return left

    def _parse_term(self) -> ASTNode:
        if self._current().type == TokenType.NOT:
            self._advance()
            child = self._parse_factor()
            return NotNode(child)
        return self._parse_factor()

    def _parse_factor(self) -> ASTNode:
        if self._current().type == TokenType.LPAREN:
            self._advance()
            node = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return node
        elif self._current().type == TokenType.ID:
            return IdNode(self._advance().value)
        elif self._current().type == TokenType.KEYWORD:
            return KeywordNode(self._advance().value)
        else:
            raise ValueError(
                f"Expected ID, KEYWORD, or '(', got '{self._current().type}' "
                f"('{self._current().value}') at position {self.pos}"
            )


def validate_id(id: str) -> bool:
    if id.startswith("T"):
        try:
            Topics()[id]
            return True
        except Exception:
            return False
    elif id.startswith("C"):
        results = Concepts().filter(openalex=id).get(per_page=1)
        return bool(results)
    return False


class Evaluator:
    def __init__(self, max_papers: int, is_keyword: bool = False):
        self.max_papers = max_papers
        self.is_keyword = is_keyword
        self.cache: dict[str, set[str]] = {}

    def evaluate(self, ast: ASTNode) -> set[str]:
        if isinstance(ast, IdNode):
            return self._get_ids(ast.id)
        elif isinstance(ast, KeywordNode):
            return self._get_keyword_dois(ast.keyword)
        elif isinstance(ast, NotNode):
            all_ids = self._get_all_ids()
            return all_ids - self.evaluate(ast.child)
        elif isinstance(ast, AndNode):
            return self.evaluate(ast.left) & self.evaluate(ast.right)
        elif isinstance(ast, OrNode):
            return self.evaluate(ast.left) | self.evaluate(ast.right)
        else:
            raise ValueError(f"Unknown AST node type: {type(ast)}")

    def _get_all_ids(self) -> set[str]:
        all_ids: set[str] = set()
        for ids in self.cache.values():
            all_ids.update(ids)
        return all_ids

    def _get_ids(self, id: str) -> set[str]:
        if id in self.cache:
            return self.cache[id]

        dois = self._query_openalex(id)
        self.cache[id] = dois
        return dois

    def _query_openalex(self, id: str) -> set[str]:
        if id.startswith("T"):
            query = Works().filter(topics={"id": id})
        elif id.startswith("C"):
            query = Works().filter(concepts={"id": id})
        else:
            raise ValueError(f"Unknown ID type: {id}")

        results = query.get(per_page=self.max_papers)

        dois: set[str] = set()
        for work in results:
            doi = work.get("doi")
            if doi:
                dois.add(doi)

        logger.info(f"Queried {id}: found {len(dois)} DOIs")
        return dois

    def _get_keyword_dois(self, keyword: str) -> set[str]:
        if keyword in self.cache:
            return self.cache[keyword]

        dois = self._query_openalex_keyword(keyword)
        self.cache[keyword] = dois
        return dois

    def _query_openalex_keyword(self, keyword: str) -> set[str]:
        query = Works().search(keyword)
        results = query.get(per_page=self.max_papers)

        dois: set[str] = set()
        for work in results:
            doi = work.get("doi")
            if doi:
                dois.add(doi)

        logger.info(f"Queried keyword '{keyword}': found {len(dois)} DOIs")
        return dois


def _parse_expression(
    expression: str, max_papers: int, is_keyword: bool = False
) -> set[str]:
    if not expression:
        return set()

    tokens = Tokenizer(expression).tokenize()
    ast = Parser(tokens).parse()

    if not is_keyword:
        validate_id(ast)

    evaluator = Evaluator(max_papers, is_keyword=is_keyword)
    return evaluator.evaluate(ast)


def get_dois_from_filter(filter: SearchFilter) -> list[str]:
    result_dois: set[str] | None = None

    if filter.topics is not None:
        if isinstance(filter.topics, list):
            if filter.topics:
                expression = " and ".join(filter.topics)
            else:
                expression = ""
        else:
            expression = filter.topics.strip()

        arg_dois = _parse_expression(expression, filter.max_papers)
        result_dois = arg_dois

    if filter.keywords is not None:
        if isinstance(filter.keywords, list):
            if filter.keywords:
                expression = " and ".join(filter.keywords)
            else:
                expression = ""
        else:
            expression = filter.keywords.strip()

        keyword_dois = _parse_expression(expression, filter.max_papers, is_keyword=True)

        if result_dois is None:
            result_dois = keyword_dois
        else:
            result_dois &= keyword_dois

    if result_dois is None:
        return []

    logger.info(f"Found {len(result_dois)} DOIs from filter")
    return sorted(result_dois)


def validate_id(ast: ASTNode) -> bool:
    if isinstance(ast, IdNode):
        return _check_id_exists(ast.id)
    elif isinstance(ast, NotNode):
        return validate_id(ast.child)
    elif isinstance(ast, AndNode):
        return validate_id(ast.left) and validate_id(ast.right)
    elif isinstance(ast, OrNode):
        return validate_id(ast.left) or validate_id(ast.right)
    return True


def _check_id_exists(id: str) -> bool:
    if id.startswith("T"):
        try:
            Topics()[id]
            return True
        except Exception:
            raise ValueError(f"Topic ID not found in OpenAlex: {id}")
    elif id.startswith("C"):
        results = Concepts().filter(openalex=id).get(per_page=1)
        if not results:
            raise ValueError(f"Concept ID not found in OpenAlex: {id}")
        return True
    raise ValueError(f"ID must start with 'T' (topic) or 'C' (concept): {id}")


def _filter_by_year(
    dois: list[str], year_min: int | None, year_max: int | None
) -> set[str]:
    filtered: set[str] = set()
    for doi in dois:
        work = Works()["https://openalex.org/" + doi.replace("https://doi.org/", "")]
        try:
            pub_year = work.get("publication_year")
            if pub_year is None:
                continue
            if year_min and pub_year < year_min:
                continue
            if year_max and pub_year > year_max:
                continue
            filtered.add(doi)
        except Exception:
            continue
    return filtered


def _filter_open_access_only(dois: list[str]) -> set[str]:
    filtered: set[str] = set()
    for doi in dois:
        work = Works()["https://openalex.org/" + doi.replace("https://doi.org/", "")]
        try:
            if work.get("is_oa"):
                filtered.add(doi)
        except Exception:
            continue
    return filtered


def test_usage():
    f = SearchFilter(topics="T11948", max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"Found {len(dois)} DOIs: {dois}")


def test_and_operator():
    f = SearchFilter(topics="T11948 and C185592680", max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"AND result: {len(dois)} DOIs")


def test_or_operator():
    f = SearchFilter(topics="T11948 or C185592680", max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"OR result: {len(dois)} DOIs")


def test_complex():
    f = SearchFilter(topics="(T11948 or C185592680)", max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"Complex expression: {len(dois)} DOIs")


def test_list_input():
    f = SearchFilter(topics=["T11948", "C185592680"], max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"List input (implicit AND): {len(dois)} DOIs")


def test_missing_operator_error():
    try:
        f = SearchFilter(topics="T11948 T12345", max_papers=10)
        get_dois_from_filter(f)
    except ValueError as e:
        logger.info(f"Caught expected error: {e}")


def test_invalid_id_error():
    try:
        f = SearchFilter(topics="T999999999", max_papers=10)
        get_dois_from_filter(f)
    except ValueError as e:
        logger.info(f"Caught expected error: {e}")


def test_keywords_only():
    f = SearchFilter(keywords='"deep learning"', max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"Keywords only: {len(dois)} DOIs")


def test_keywords_and_arguments():
    f = SearchFilter(topics="T11948", keywords='"CRISPR"', max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"Keywords AND topics: {len(dois)} DOIs")


def test_keywords_boolean():
    f = SearchFilter(keywords='"AI" and "ethics"', max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"Keywords boolean: {len(dois)} DOIs")


def test_keywords_list():
    f = SearchFilter(keywords=['"AI"', '"ethics"'], max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"Keywords list: {len(dois)} DOIs")
