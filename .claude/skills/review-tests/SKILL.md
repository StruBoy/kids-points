---
name: review-tests
description: Review the test evidence collected for kids-points — coverage.py results plus Playwright screenshots — flag structural gaps, and produce a dated report under reports/. Does NOT run tests; use when the user has already run `coverage run manage.py test && coverage json`.
---

# Review tests skill

Audit the test evidence currently on disk and write a report. This skill is
**read-only on test state** — it never re-runs tests. If the artifacts are
missing or stale, tell the user how to refresh them and stop.

## When to use

Invoke when the user asks to "review tests", "audit test coverage", "report
on test evidence", "check what's tested", or similar. Also appropriate
proactively at the end of a coding session if you've made non-trivial
changes and want to flag coverage regressions before committing.

## Inputs

| Path                    | Required?  | Produced by                             |
|-------------------------|------------|-----------------------------------------|
| `reports/coverage.json` | required   | `coverage run manage.py test && coverage json` |
| `screenshots/`          | optional   | `manage.py test e2e` (auto-saved)       |
| App source trees        | always     | Already in repo                         |

If `reports/coverage.json` is missing OR its mtime is older than 4 hours,
stop and ask the user to refresh:

```sh
.venv/bin/coverage run manage.py test && .venv/bin/coverage json
.venv/bin/python manage.py test e2e   # if screenshots are also stale
```

(Use `stat -f %m reports/coverage.json` on macOS to read the mtime; compare
to `date +%s`.)

## Procedure

1. **Confirm artifacts exist and are fresh.** If not, stop per above.
2. **Parse `reports/coverage.json`.** Compute:
   - Overall line coverage `%`.
   - Per-app subtotals by grouping files under `families/`, `points/`,
     `store/`, `purchases/`, `web/`, `kidspoints/`.
   - Files below 90% — list each with its uncovered line numbers from the
     `missing_lines` field.
3. **Walk source files for structural gaps.** For each non-trivial source
   module in the five apps (skip `__init__.py`, `admin.py`, `apps.py`,
   `migrations/`, `urls.py`):
   - Confirm a matching `tests/test_*.py` file exists. If not, flag.
   - For `views.py` files, grep the corresponding tests/ for the view's
     name in a URL reverse or `client.get/post` call. Views that never
     appear as a test target are gaps even if some lines are covered
     transitively.
4. **Catalog e2e screenshot evidence.** If `screenshots/` exists, walk it
   and produce a per-test inventory: `TestClass.test_method` → ordered
   list of screenshot labels (drop the `NN_` prefix and `.png` suffix).
   Count totals.
5. **Identify regressions vs prior report**, if any prior report exists
   in `reports/test-review-*.md`. A "regression" is overall coverage
   dropping by more than 1 percentage point, OR a workflow losing
   screenshots. Mention only if present.
6. **Write the report** to
   `reports/test-review-$(date +%Y-%m-%d-%H%M).md` using the template
   below. Create `reports/` if needed.
7. **Print an inline summary** to the user: overall coverage `%`, count
   of structural gaps, count of e2e screenshots, and the path to the
   full report.

## Report template

Use this structure verbatim. Sections that have no findings should still
appear with a single line ("None.") so the report shape is predictable
across runs.

```markdown
# Test Evidence Review — <YYYY-MM-DD HH:MM>

**Artifacts:** coverage.json from <ts>, screenshots from <ts or "none">.

## Headline

- Overall line coverage: **<X>%** (<covered>/<total> statements)
- Unit tests counted by coverage: <N>
- E2E screenshots on disk: <M> across <K> workflows
- Structural gaps: <G> source modules without matching tests

## Coverage by app

| App        | Files | Statements | Covered | %       |
|------------|------:|-----------:|--------:|--------:|
| families   |   ... |        ... |     ... |     ...% |
| points     |   ... |        ... |     ... |     ...% |
| ...        |       |            |         |         |

## Files below 90%

For each, show: path, %, and the missing line numbers (cite as
`path:line` so they're clickable).

- `points/views.py` — 97% — missing: points/views.py:42
- ...

(If none: "None — every covered file meets the 90% threshold.")

## Structural gaps

Source files / views with no targeted test, regardless of line coverage:

- `<path>` — <why this is a gap>
- ...

(If none: "None.")

## E2E screenshot evidence

For each test, list the screenshots in order so a reader can flip
through them mentally. Path is relative to repo root.

### HappyPathTests.test_full_purchase_cycle  (15 shots)
Path: `screenshots/HappyPathTests/test_full_purchase_cycle/`
1. login_picker
2. parent_login_form
3. ...

### ...

(If `screenshots/` missing: "No e2e screenshots on disk. Run
`./manage.py test e2e` to generate them.")

## Recommendations

Short, concrete list. Each item should be actionable — a specific
file/function/test to add. Avoid generic advice ("write more tests").

- Add a view-level test for `store.views.admin_archive` (currently
  exercised transitively but not asserted on directly).
- ...

## Compared to prior report

(Only if a previous report exists. Otherwise omit this section.)

- Coverage: <prev>% → <now>% (Δ <±X>%)
- Workflows added/removed
- Files newly below 90%
```

## Style notes

- Cite source lines as `path:line` (no parens, no extra text) so the
  reader can click them in the editor.
- Don't bury the lead — the headline section must be readable in five
  seconds.
- If coverage is healthy (>=95% overall, 0 structural gaps, screenshots
  fresh), say so plainly and keep the report short. No padding.
- Don't editorialize. State the facts and the recommendations.
