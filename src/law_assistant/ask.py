"""
Ask one question from the command line: `python -m law_assistant.ask "Do I need a data protection officer?"`.
Prints the answer with its sources, then the route, the steps' times and the model tokens used. Needs the
BGE-M3 model, its saved vectors and a Gemini key in `.env` (see the README).
"""

from __future__ import annotations

import sys

from law_assistant.answer.factory import build_pipeline


def main(argv: list[str]) -> int:
    flags = {a for a in argv if a.startswith("--")}
    words = [a for a in argv if not a.startswith("--")]
    if not words:
        print(
            'usage: python -m law_assistant.ask [--version-aware] [--with-dates] "your question"',
            file=sys.stderr,
        )
        return 2
    pipeline, generator = build_pipeline(
        version_aware="--version-aware" in flags, include_dates="--with-dates" in flags
    )
    result = pipeline.ask(" ".join(words))
    print(result.text)
    steps = ", ".join(f"{k} {v:.2f}s" for k, v in result.timings.items())
    tokens_in = sum(c.prompt_tokens for c in generator.calls)
    tokens_out = sum(c.output_tokens for c in generator.calls)
    print(f"\n[{result.kind}; route {result.route}; {steps}; {tokens_in} tokens in, {tokens_out} out]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
