# Simplify the Arabic grammar site to eight easy questions

User follow-up: simplify the whole experience, make the appearance nicer, make the questions easy, reduce the total to exactly eight and send the website.

Chosen implementation: replace the dense dark interface with a light cream and green layout, larger Arabic text, short labels and one main action per step. Keep the existing standalone HTML, embedded fonts and tested scoring core. Retaining the previous presentation modes, advanced question pairs and multi-step explanations would conflict with the requested simplification; a framework rewrite would complicate offline delivery.

The flow is home → optional short lesson → eight straightforward multiple-choice questions → result. Teach only the verb, subject and direct object in ordinary sentences. No dual nouns, delayed subjects, attached pronouns, word ordering or advanced inflection. Each question has three choices, an optional hint, an explicit check button and a one-sentence explanation. Selections remain editable before checking. Keep local saved progress, a simple review list, reset confirmation, keyboard access and a clean HTML download.

Use eight reviewed questions. Persist under a versioned v3 key so older ten-question results cannot appear. Reuse the existing state core and its tests. Verify browser behavior, 320/360/390/768px layouts, malformed/unavailable storage, restart and export. Publish the verified HTML under both nahw-interactive.html and index.html, update GitHub main, and enable GitHub Pages if supported so the user gets a direct website link.
