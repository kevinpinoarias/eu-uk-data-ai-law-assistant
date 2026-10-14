# The structured table of exact facts

`facts/legal_facts.jsonl`, read with `law_assistant.facts.table`. Checks in `law_assistant.facts.checks`.

## Why it exists

**Generic idea.** Many AI systems pair free-text retrieval with structured data that is queried by key through a tool call. A language model can misread or mis-copy a number; a table returns the same verified value every time. Each fact is stored with its sources, can be checked by a script, and is tested against everything else the system says. It is the same split as in the hospitality project: exact figures from data, explanations from text.

**In this project.** Eight gold questions must be answered from this table, and the Phase 4 router has to send them here (roadmap 4.5 measures that). Every row can be proved to come from the provisions it cites.

## What a fact holds

- `key` (for example `gdpr-fine-upper-tier`), `kind` (fine ceiling, deadline, age, application date), `jurisdictions`;
- `value`: typed figures, such as `{"amount": 20000000, "currency": "EUR", "turnover_percent": 4, "rule": "higher_of"}` or `{"annex_iii": "2027-12-02", "annex_i": "2028-08-02"}`;
- a one-line answer with its citation in English and in Spanish, and the subject in both;
- `caveat_en` and `caveat_es`: what the figure does not say (a ceiling, a default that Member States may change, a date that is derived);
- `sources`: instrument, unit, pinpoint ids, quotes, and the version the figure comes from.

## What the checks prove

1. Every source unit, pinpoint id and quote exists in the parsed corpus (the same check as for the gold set).
2. Every number and date inside `value` appears in the text of the provisions cited. Numbers are read as digits (with a space, comma or point between thousands: `20 000 000`, `£17,500,000`), as number words only when they count a period or an age (`one month`, `catorce años`; "one of the following" is not a number) and as dates in English or Spanish. A negative control is part of the tests: a corrupted amount, date and period are all caught on the real corpus.
3. Keys are unique and every summary and subject is filled in both languages.
4. Every numeric gold question names a key that exists, and its expected answer states the figures of that fact. The two were written separately, so agreement is a real cross-check.

## The 19 facts (as of the corpus snapshot of 14 October 2026)

| Key | Kind | Figure | Sources |
|---|---|---|---|
| `ai-act-fine-gpai-providers` | fine ceiling | 15,000,000 EUR or 3 % of turnover | eu-ai-act article 101 |
| `ai-act-fine-operator-obligations` | fine ceiling | 15,000,000 EUR or 3 % of turnover | eu-ai-act article 99 |
| `ai-act-fine-prohibited-practices` | fine ceiling | 35,000,000 EUR or 7 % of turnover | eu-ai-act article 99 |
| `ai-act-general-application-date` | application date | date 2026-08-02 | eu-ai-act article 113 |
| `ai-act-gpai-application-date` | application date | date 2025-08-02 | eu-ai-act article 113 |
| `ai-act-gpai-legacy-models-deadline` | deadline | date 2027-08-02 | eu-ai-act article 111 |
| `ai-act-high-risk-application-dates` | application date | annex iii 2027-12-02, annex i 2028-08-02 | eu-ai-act article 113 |
| `ai-act-prohibitions-application-date` | application date | date 2025-02-02, new points date 2026-12-02 | eu-ai-act article 113 |
| `ai-act-synthetic-content-marking-transition` | deadline | date 2026-12-02 | eu-ai-act article 111 |
| `gdpr-breach-notification-deadline` | deadline | 72 hours | eu-gdpr article 33 |
| `gdpr-child-consent-age` | age | 16 years (Member States may go down to 13) | eu-gdpr article 8 |
| `gdpr-fine-lower-tier` | fine ceiling | 10,000,000 EUR or 2 % of turnover | eu-gdpr article 83 |
| `gdpr-fine-upper-tier` | fine ceiling | 20,000,000 EUR or 4 % of turnover | eu-gdpr article 83 |
| `gdpr-response-deadline` | deadline | 1 month (+2 months) | eu-gdpr article 12 |
| `lopdgdd-child-consent-age` | age | 14 years | es-lopdgdd article 7 |
| `uk-gdpr-child-consent-age` | age | 13 years | uk-gdpr article 8 |
| `uk-gdpr-fine-lower-tier` | fine ceiling | 8,700,000 GBP or 2 % of turnover | uk-gdpr article 83; uk-dpa-2018 section 157 |
| `uk-gdpr-fine-upper-tier` | fine ceiling | 17,500,000 GBP or 4 % of turnover | uk-gdpr article 83; uk-dpa-2018 section 157 |
| `uk-gdpr-response-deadline` | deadline | 1 month (+2 months) | uk-gdpr article 12A |

## Decisions behind it

- **Derived dates are not stored as facts.** The date from which the Article 101 fines on general-purpose AI model providers apply follows from Article 113 ("with the exception of Article 101") but is not stated; it is in the caveat of `ai-act-gpai-application-date`, not in a value.
- **Ambiguity is kept visible.** The LOPDGDD says "mayor de catorce años"; the table records 14 and says in the caveat that the wording does not by itself settle the case of exactly 14. The EU age is a default that Member States may lower, so it has two figures.
- **Pinned to the snapshot.** The AI Act application dates are those of the consolidated text of 27 July 2026; when the law changes, a fact is changed and its sources and checks are re-run.

## Not in the table

Dates that come only from corpus metadata (for example the date a UK provision came into force, taken from legislation.gov.uk's restriction dates) are not here, because a quote cannot prove them; they belong to the as-of questions and to `in_force_from`.
