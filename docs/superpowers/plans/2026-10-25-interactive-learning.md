# Interactive grammar learning implementation plan

> **For agentic workers:** Use executing-plans for implementation and independent review for verification.

**Goal:** Deliver ten stronger Arabic grammar questions and a polished, accessible standalone learning experience.

**Architecture:** Retain embedded HTML/CSS/JavaScript. Separate the quiz state machine conceptually from DOM rendering. Content review and state tests run independently.

**Tech Stack:** HTML, CSS, vanilla JavaScript; Node built-in test runner and Python Playwright for verification.

**Spec:** docs/superpowers/specs/2026-10-25-interactive-learning-design.md

## Global constraints

- Exactly ten questions in five pairs; no runtime external assets.
- Editable selection before explicit submission; no points for revealing without submission.
- Keep RTL, embedded fonts, presentation support and reduced-motion support.

## Review focus

- Ordering corrections must score the final submitted arrangement.
- Keyboard Space must select options through native button behavior.
- Stored malformed/old state must be ignored; denied storage must remain usable.
- Export must reopen without external requests or visible stale answers.
- Mobile and large text must not overflow or shrink text.

### Task 1: State and content

- [x] Write and run failing core tests for draft/submit/reveal/ordering/immutability.
- [x] Implement validated state transitions and integrate ten reviewed questions.
- [x] Verify node tests and grammar content.

### Task 2: Learning interactions

- [x] Add five-stage navigation, mode switch, progress and semantic answer status.
- [x] Add reasoning steps, specific feedback, interactive lesson examples and summary review.
- [x] Add guarded versioned local persistence and clean offline export.
- [x] Fix focus, keyboard shortcuts, dialogs, skip link, responsive text and reduced motion.

### Task 3: Verification and delivery

- [x] Test complete journeys and edge cases in local Chromium at desktop/mobile sizes.
- [x] Inspect screenshots and conduct independent code review; resolve significant issues.
- [x] Commit and upload verified files to GitHub; verify remote file SHA.
- [x] Provide standalone HTML download.

## Verification record

2026-10-25: 11 Node core tests and 8 real Chromium journey tests pass. The browser suite exercises ten correct answers, wrong and skipped answers, draft editing, partial ordering, reload persistence, malformed or unavailable storage, native HTML download, lesson example changes, keyboard access, named dialogs, and 360/390/768px layouts with large text. Independent code review found no remaining actionable defects.

Build choices: preserve the existing vanilla JavaScript implementation and visual identity; organize the ten questions in five learning pairs; keep all runtime assets embedded. Local file navigation is restricted by the verification browser, so downloaded HTML bytes are reopened through the local HTTP server in a fresh browser context while checking for external requests. No runtime network request is required.
