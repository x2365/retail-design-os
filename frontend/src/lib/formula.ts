/** Tiny calculator-style expression evaluator for money fields that accept
 * a formula (e.g. "=200*1000+18%"). Deliberately not `eval`/`new Function` —
 * user input goes straight into this, so it's a real (if small) recursive-
 * descent parser for `+ - * /`, parens and unary minus.
 *
 * `%` is handled as a single trailing adjustment, calculator-style, not
 * Excel's postfix-anywhere semantics: "<base> + N%" means "base plus N% of
 * base" (base*(1+N/100)) — the reading that makes "subtotal + 18% markup"
 * come out right — not a bare N/100 wherever % happens to appear. Only
 * supported at the very end of the whole formula; that's the only shape
 * this field needs ("=200*1000+18%", "=1500-5%", or no % at all).
 */

type TokenType = "number" | "+" | "-" | "*" | "/" | "(" | ")";
interface Token {
  type: TokenType;
  value?: number;
}

function tokenize(input: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < input.length) {
    const ch = input[i];
    if (/\s/.test(ch)) {
      i++;
      continue;
    }
    if ("+-*/()".includes(ch)) {
      tokens.push({ type: ch as TokenType });
      i++;
      continue;
    }
    if (/[0-9.]/.test(ch)) {
      let j = i;
      while (j < input.length && /[0-9.]/.test(input[j])) j++;
      const raw = input.slice(i, j);
      const value = Number(raw);
      if (raw === "" || Number.isNaN(value)) {
        throw new Error(`Не число: «${raw}»`);
      }
      tokens.push({ type: "number", value });
      i = j;
      continue;
    }
    throw new Error(`Непонятный символ: «${ch}»`);
  }
  return tokens;
}

class Parser {
  private pos = 0;
  constructor(private tokens: Token[]) {}

  private peek(): Token | undefined {
    return this.tokens[this.pos];
  }
  private consume(type: TokenType): Token {
    const t = this.tokens[this.pos];
    if (!t || t.type !== type) {
      throw new Error(`Ожидался «${type}»`);
    }
    this.pos++;
    return t;
  }

  parse(): number {
    const result = this.additive();
    if (this.pos < this.tokens.length) {
      throw new Error("Лишнее в конце выражения");
    }
    return result;
  }

  // additive := term (('+'|'-') term)*
  private additive(): number {
    let left = this.term();
    while (this.peek()?.type === "+" || this.peek()?.type === "-") {
      const op = this.consume(this.peek()!.type).type;
      const right = this.term();
      left = op === "+" ? left + right : left - right;
    }
    return left;
  }

  // term := factor (('*'|'/') factor)*
  private term(): number {
    let left = this.factor();
    while (this.peek()?.type === "*" || this.peek()?.type === "/") {
      const op = this.consume(this.peek()!.type).type;
      const right = this.factor();
      if (op === "/" && right === 0) throw new Error("Деление на ноль");
      left = op === "*" ? left * right : left / right;
    }
    return left;
  }

  // factor := '-' factor | '(' additive ')' | number
  private factor(): number {
    const t = this.peek();
    if (!t) throw new Error("Незаконченное выражение");
    if (t.type === "-") {
      this.consume("-");
      return -this.factor();
    }
    if (t.type === "(") {
      this.consume("(");
      const v = this.additive();
      this.consume(")");
      return v;
    }
    if (t.type === "number") {
      this.consume("number");
      return t.value!;
    }
    throw new Error("Ожидалось число или «(»");
  }
}

function evaluatePlain(expr: string): number {
  if (!expr.trim()) throw new Error("Пустая формула");
  return new Parser(tokenize(expr)).parse();
}

/** `input` may or may not include the leading "=" — both are accepted so
 * callers can pass the raw field text as-is. */
export function evaluateFormula(input: string): number {
  const expr = input.trim().replace(/^=/, "");
  if (!expr.trim()) throw new Error("Пустая формула");

  // Trailing "<base> +/- N%" — the only place % is meaningful here.
  const withPercent = expr.match(/^(.*)([+-])\s*(\d+(?:\.\d+)?)\s*%$/);
  if (withPercent) {
    const [, baseExpr, sign, pctStr] = withPercent;
    const base = evaluatePlain(baseExpr);
    const pct = Number(pctStr);
    return sign === "+" ? base + (base * pct) / 100 : base - (base * pct) / 100;
  }

  // A bare "N%" with nothing before it — just N/100.
  const barePercent = expr.match(/^(.*\S)\s*%$/);
  if (barePercent) {
    return evaluatePlain(barePercent[1]) / 100;
  }

  return evaluatePlain(expr);
}
