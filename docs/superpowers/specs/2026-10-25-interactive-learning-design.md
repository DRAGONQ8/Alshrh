# Arabic grammar learning improvements

The user requests a complete review and improvement of the existing standalone Arabic grammar website, exactly ten improved questions, richer interactions, a GitHub upload and a downloadable HTML file.

Preserve the existing RTL navy/mint/gold visual identity and embedded fonts. Keep all production CSS, content and JavaScript within nahw-interactive.html with no runtime dependencies. Organize the ten questions into five coherent pairs of increasing difficulty. Each answer includes clear grammar, a hint, reasoning steps and explanation of the chosen distractor.

Implementation choice: retain vanilla JavaScript and the current lesson/home/quiz/summary structure. A framework rewrite would add build requirements and complicate offline delivery. Split source files would make the requested standalone deliverable harder to use.

Practice mode shows questions immediately. Group discussion mode preserves manual reveal. Selecting an answer is an editable draft; explicit verification freezes and scores it. Opening an explanation without submitting earns no point. Question status, pair progress and review links must agree with the final submitted state. Preserve progress locally when browser storage is available; storage denial must not break the app.

Improve lesson interaction, keyboard and touch operation, focus, screen-reader names, reduced motion and responsive layout. Export a clean standalone HTML document; remove the accidentally embedded Cloudflare injection.

Use local Chromium screenshots and interaction checks, node core tests and a fresh independent code review. Push the verified final changes to the repository main branch as requested; check for concurrent remote updates first.
