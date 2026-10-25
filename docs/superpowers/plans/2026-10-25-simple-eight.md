# Simple eight-question grammar site plan

> **For agentic workers:** Use inline implementation and independent review.

**Goal:** Deliver an attractive, simple Arabic grammar site with exactly eight easy questions and a direct website URL.

**Architecture:** Preserve the session core and embedded fonts; replace the old interface and content with concise HTML/CSS/vanilla JavaScript. Keep the canonical standalone file and a byte-identical index.html for GitHub Pages.

**Tech Stack:** HTML, CSS, JavaScript; Node tests and Python Playwright.

**Spec:** docs/superpowers/specs/2026-10-25-simple-eight-design.md

## Global constraints

- Exactly eight basic multiple-choice questions, three choices each.
- No runtime external assets; draft answers are graded only on explicit verification.
- One visible question, short feedback, no advanced grammar or presentation controls.

## Review focus

- Old ten-question data cannot restore into the new quiz.
- Native Space/Enter activation must work on answer buttons.
- Users cannot advance from the current question before checking it.
- Export reopens cleanly with embedded fonts and scripts.
- No horizontal overflow at 320px or when text is enlarged by the browser.

### Tasks

- [x] Run a failing eight-question requirement check, then integrate reviewed easy content.
- [x] Build the simplified interface and guarded persistence while retaining the tested core.
- [x] Verify core tests and full browser journeys; inspect desktop/mobile screenshots.
- [x] Resolve independent review findings, update README, push main and verify live hosting.

## Validation

All 11 reusable session-core tests and all 8 new browser tests pass. Verified exactly 8 easy questions and matching standalone/index files, 320/360/390/768px layouts, native keyboard selection, draft corrections, reset confirmation, unavailable/old storage and a clean exported HTML document with no external requests.

## Delivery

Published the verified standalone files to GitHub main. GitHub Pages setup returned HTTP403 because the integration cannot enable Pages. Published the same HTML through Sites instead; the native deployment succeeded at https://nahw-simple-q8.qq8081927.chatgpt.site with the default owner-private audience. Independent review found no significant issues and additionally completed all eight questions from exported HTML in an offline browser context.
