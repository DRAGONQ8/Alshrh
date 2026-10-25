"""Run: python tests/browser_smoke.py (serve the repository and set NAHW_URL).

Uses installed Python Playwright/Chromium. Downloads reopen through the same
HTTP server; no file URLs, browser downloads, or third-party requests are needed.
"""

import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get(
    "NAHW_URL", "http://127.0.0.1:8765/Alshrh/nahw-interactive.html"
)
STORAGE_KEY = "nahw-progress-v3"
ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / ".test-artifacts"
SCREENSHOTS = ARTIFACTS / "screenshots"


class BrowserSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"),
            args=["--no-sandbox"],
        )
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        expect.set_options(timeout=4000)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.contexts = []
        self.unexpected_requests = []
        self.javascript_errors = []
        self.allowed_document_urls = {URL}
        self.page = self.new_page()

    def tearDown(self):
        for context in self.contexts:
            context.close()
        self.assertEqual(self.unexpected_requests, [], "unexpected page requests")
        self.assertEqual(self.javascript_errors, [], "browser JavaScript errors")

    def new_page(self, width=1280, initial_storage=None, deny_storage=False):
        context = self.browser.new_context(
            viewport={"width": width, "height": 900},
            accept_downloads=True,
            reduced_motion="reduce",
        )
        self.contexts.append(context)
        if initial_storage is not None:
            context.add_init_script(
                "for (const [key, value] of Object.entries(%s)) "
                "{ localStorage.setItem(key, value); }" % json.dumps(initial_storage)
            )
        if deny_storage:
            context.add_init_script("""(() => {
                const denied = () => { throw new DOMException('Storage disabled', 'SecurityError'); };
                for (const method of ['getItem', 'setItem', 'removeItem']) {
                    Object.defineProperty(Storage.prototype, method,
                        {value: denied, configurable: true});
                }
            })();""")
        page = context.new_page()
        page.set_default_timeout(4000)
        page.on("pageerror", lambda error: self.javascript_errors.append(str(error)))
        page.on("request", self.check_request)
        return page

    def check_request(self, request):
        target = urlsplit(request.url)
        if target.scheme not in ("http", "https") or target.path.endswith("/favicon.ico"):
            return
        allowed = {
            (parsed.scheme, parsed.netloc, parsed.path)
            for parsed in map(urlsplit, self.allowed_document_urls)
        }
        if (target.scheme, target.netloc, target.path) not in allowed:
            self.unexpected_requests.append(request.url)

    def open_app(self, page=None, url=URL):
        page = page or self.page
        page.goto(url, wait_until="load")
        page.wait_for_function("Boolean(globalThis.NahwApp)")
        return page

    def navigate(self, name, page=None):
        page = page or self.page
        page.locator(f'[data-screen="{name}"]:visible').first.click()
        expect(page.locator(f"#{name}")).to_be_visible()

    def start(self, page=None):
        page = page or self.page
        page.locator("[data-start]:visible").first.click()

    def entry(self, index=None, page=None):
        page = page or self.page
        return page.evaluate(
            "index => NahwApp.session.entries[index === null ? NahwApp.session.index : index]",
            index,
        )

    def stats(self, page=None):
        return (page or self.page).evaluate(
            "NahwCore.stats(NahwApp.session, NahwApp.questions)"
        )

    def jump(self, index, page=None):
        page = page or self.page
        page.locator(f'#questionMap [data-question="{index}"]').click()
        expect(page.locator(".question-title")).to_be_visible()
        self.assertEqual(page.evaluate("NahwApp.session.index"), index)

    def answer(self, index, page=None):
        page = page or self.page
        self.jump(index, page)
        answer = page.evaluate("i => NahwApp.questions[i].answer", index)
        page.locator(f'[data-answer="{answer}"]').click()
        page.locator("#checkAnswer").click()
        expect(page.locator("#answerBox")).to_be_visible()
        self.assertEqual(self.entry(index, page)["firstChoice"], answer)

    def assert_fresh(self, page):
        state = page.evaluate("NahwApp.session")
        self.assertEqual(state["index"], 0)
        self.assertEqual(len(state["entries"]), 8)
        for entry in state["entries"]:
            self.assertIsNone(entry["selected"])
            self.assertIsNone(entry["firstChoice"])
            self.assertFalse(entry["revealed"])

    def test_eight_basic_questions_complete_to_summary(self):
        page = self.open_app()
        questions = page.evaluate("NahwApp.questions")
        self.assertEqual(len(questions), 8)
        for question in questions:
            self.assertIn(question["kind"], ("word", "mcq"))
            self.assertIsInstance(question["answer"], int)
            self.assertIn(question["answer"], range(len(question["options"])))
        self.assertEqual(
            (ROOT / "index.html").read_bytes(),
            (ROOT / "nahw-interactive.html").read_bytes(),
            "deployment alias must match the canonical standalone file",
        )
        self.start()
        expect(page.locator("#questionMap [data-question]")).to_have_count(8)
        expect(page.locator('#questionMap [data-question="8"]')).to_have_count(0)
        for index in range(8):
            self.answer(index)
            expect(page.locator("#answerBox details")).to_have_count(0)
            self.assertLess(len(page.locator("#answerBox").inner_text()), 450)
            page.locator("#quizNext").click()
        expect(page.locator("#summary")).to_be_visible()
        self.assertEqual(self.stats(), {"answered": 8, "correct": 8, "revealed": 8, "total": 8})
        expect(page.locator("#summaryReview [data-review-question]")).to_have_count(8)
        page.screenshot(path=str(SCREENSHOTS / "summary-complete.png"), full_page=True)
        page.locator('#summaryReview [data-review-question="0"]').click()
        expect(page.locator("#quiz")).to_be_visible()
        expect(page.locator("#answerBox")).to_be_visible()
        self.assertEqual(page.evaluate("NahwApp.session.index"), 0)
        self.navigate("home")
        self.start()
        expect(page.locator("#summary")).to_be_visible()

    def test_keyboard_correction_hint_and_submitted_answer_is_immutable(self):
        page = self.open_app()
        self.start()
        answer, count = page.evaluate("[NahwApp.questions[0].answer, NahwApp.questions[0].options.length]")
        wrong = (answer + 1) % count
        expect(page.locator("#checkAnswer")).to_be_disabled()
        expect(page.locator("#quizNext")).to_be_disabled()
        page.locator(f'[data-answer="{wrong}"]').focus()
        page.keyboard.press("Space")
        self.assertEqual(self.entry()["selected"], wrong)
        self.assertIsNone(self.entry()["firstChoice"])
        page.locator(f'[data-answer="{answer}"]').click()
        self.assertEqual(self.entry()["selected"], answer)
        expect(page.locator("#quizNext")).to_be_disabled()
        page.locator("#hintBtn").click()
        expect(page.locator("#hintBtn")).to_have_attribute("aria-expanded", "true")
        self.assertEqual(self.stats(), {"answered": 0, "correct": 0, "revealed": 0, "total": 8})
        self.assertFalse(self.entry()["revealed"])
        page.locator("#checkAnswer").click()
        expect(page.locator("#answerBox")).to_be_visible()
        before = self.entry()
        page.locator(f'[data-answer="{wrong}"]').dispatch_event("click")
        self.assertEqual(self.entry(), before)
        self.assertEqual(self.stats()["correct"], 1)
        page.locator("#quizNext").click()
        self.assertEqual(page.evaluate("NahwApp.session.index"), 1)
        page.locator("#quizPrev").click()
        self.assertEqual(self.entry(), before)
        expect(page.locator("#answerBox")).to_be_visible()
        expect(page.locator("[data-mode], #settingsBtn, #fontLarge, #showQuestion, [data-order]")).to_have_count(0)

    def test_reload_resumes_first_unfinished_and_rejects_invalid_or_old_storage(self):
        page = self.open_app()
        self.start()
        self.answer(0)
        self.jump(2)
        page.locator('[data-answer="0"]').click()
        self.jump(4)
        saved = page.evaluate("key => JSON.parse(localStorage.getItem(key))", STORAGE_KEY)
        self.assertEqual(saved["version"], 3)
        self.assertEqual(saved["session"], page.evaluate("NahwApp.session"))
        page.reload(wait_until="load")
        expect(page.locator("#home")).to_be_visible()
        self.start()
        self.assertEqual(page.evaluate("NahwApp.session.index"), 1)
        self.assertTrue(self.entry(0)["revealed"])
        self.assertEqual(self.entry(2)["selected"], 0)
        self.assertEqual(self.stats()["correct"], 1)
        old = json.dumps({"version": 2, "session": saved["session"]})
        malformed = [
            {STORAGE_KEY: "{bad JSON"},
            {STORAGE_KEY: "null"},
            {STORAGE_KEY: old},
            {"nahw-progress-v2": old},
            {STORAGE_KEY: json.dumps({"version": 3, "session": {"index": 99, "entries": []}})},
        ]
        invalid_answer = json.loads(json.dumps(saved))
        invalid_answer["session"]["entries"][0]["selected"] = 999
        malformed.append({STORAGE_KEY: json.dumps(invalid_answer)})
        for payload in malformed:
            with self.subTest(payload=str(payload)[:75]):
                fresh = self.open_app(self.new_page(initial_storage=payload))
                self.assert_fresh(fresh)
                self.start(fresh)
                fresh.locator('[data-answer="0"]').click()
                expect(fresh.locator("#checkAnswer")).to_be_enabled()

    def test_denied_storage_still_allows_learning(self):
        page = self.open_app(self.new_page(deny_storage=True))
        self.assert_fresh(page)
        self.start(page)
        self.answer(0, page)
        self.assertEqual(self.stats(page), {"answered": 1, "correct": 1, "revealed": 1, "total": 8})
        self.navigate("lesson", page)
        expect(page.locator("#lesson [data-rule]")).to_have_count(3)
        self.navigate("quiz", page)
        self.assertEqual(page.evaluate("NahwApp.session.index"), 1)
        expect(page.locator("#saveState")).to_contain_text("الحفظ غير متاح")
        self.jump(0, page)
        expect(page.locator("#answerBox")).to_be_visible()
        self.assertEqual(self.stats(page)["correct"], 1)

    def test_restart_requires_confirmation_and_clears_saved_progress(self):
        page = self.open_app()
        self.start()
        self.answer(0)
        page.evaluate("NahwApp.navigate('summary')")
        page.locator("#restartBtn").click()
        expect(page.locator("#restartDialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator("#restartDialog")).to_be_hidden()
        self.assertEqual(self.stats()["answered"], 1)
        page.locator("#restartBtn").click()
        page.locator("#confirmRestart").click()
        expect(page.locator("#restartDialog")).to_be_hidden()
        self.assert_fresh(page)
        self.assertEqual(self.stats(), {"answered": 0, "correct": 0, "revealed": 0, "total": 8})
        page.reload(wait_until="load")
        self.assert_fresh(page)
        self.start()
        expect(page.locator("#quiz")).to_be_visible()
        expect(page.locator("#checkAnswer")).to_be_disabled()

    def test_light_readable_layout_has_no_overflow_desktop_and_mobile(self):
        for width in (1280, 320, 360, 390, 768):
            with self.subTest(width=width):
                page = self.open_app(self.new_page(width=width))
                colors = page.evaluate("""() => {
                    const style = getComputedStyle(document.body);
                    const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
                    const luminance = color => rgb(color).map(v => {
                        v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
                    }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
                    return {background: luminance(style.backgroundColor),
                        foreground: luminance(style.color), font: parseFloat(style.fontSize)};
                }""")
                self.assertGreater(colors["background"], .75, "page should use a light background")
                self.assertGreaterEqual((colors["background"] + .05) / (colors["foreground"] + .05), 4.5)
                self.assertGreaterEqual(colors["font"], 16)
                for screen in ("home", "lesson", "quiz", "summary"):
                    page.evaluate("name => NahwApp.navigate(name)", screen)
                    expect(page.locator(f"#{screen}")).to_be_visible()
                    self.assert_no_overflow(page, f"{width}px {screen}")
                page.evaluate("NahwApp.navigate('quiz')")
                for index in range(8):
                    self.jump(index, page)
                    self.assert_no_overflow(page, f"{width}px question {index + 1}")
                page.screenshot(path=str(SCREENSHOTS / f"quiz-{width}.png"), full_page=True)

    def assert_no_overflow(self, page, label):
        dimensions = page.evaluate("""() => ({
            viewport: document.documentElement.clientWidth,
            html: document.documentElement.scrollWidth,
            body: document.body.scrollWidth
        })""")
        self.assertLessEqual(dimensions["html"], dimensions["viewport"] + 1, f"{label}: {dimensions}")
        self.assertLessEqual(dimensions["body"], dimensions["viewport"] + 1, f"{label}: {dimensions}")

    def test_download_reopens_fresh_standalone_html_without_external_requests(self):
        page = self.open_app()
        self.start()
        self.answer(0)
        self.jump(4)
        page.locator("#hintBtn").click()
        with tempfile.TemporaryDirectory(prefix="nahw-export-", dir=ARTIFACTS) as directory:
            with page.expect_download() as download_info:
                page.locator("#downloadBtn").click()
            download = download_info.value
            self.assertIsNone(download.failure())
            target = Path(directory) / "nahw-interactive.html"
            download.save_as(str(target))
            self.assertGreater(target.stat().st_size, 1000)
            origin = urlsplit(URL)
            base_path = origin.path.rsplit("/", 1)[0]
            exported_url = (
                f"{origin.scheme}://{origin.netloc}{base_path}/.test-artifacts/"
                f"{Path(directory).name}/{target.name}"
            )
            self.allowed_document_urls.add(exported_url)
            exported = self.open_app(self.new_page(), exported_url)
            expect(exported.locator("#home")).to_be_visible()
            expect(exported.locator("dialog[open], iframe, script[src]")).to_have_count(0)
            expect(exported.locator("script")).to_have_count(3)
            self.assert_fresh(exported)
            self.start(exported)
            expect(exported.locator("#checkAnswer")).to_be_disabled()
            expect(exported.locator("#answerBox:visible")).to_have_count(0)
            self.answer(0, exported)
            self.assertEqual(self.stats(exported)["correct"], 1)

    def test_home_word_meanings_and_three_rule_lesson_navigation(self):
        page = self.open_app()
        expect(page.locator("#home")).to_be_visible()
        expect(page.locator("[data-hero-role]")).to_have_count(3)
        meanings = []
        for role in ("verb", "subject", "object"):
            button = page.locator(f'[data-hero-role="{role}"]')
            button.click()
            expect(button).to_have_attribute("aria-pressed", "true")
            meanings.append(page.locator("#heroInsight").inner_text())
        self.assertEqual(len(set(meanings)), 3)
        self.assertTrue(all(len(meaning) > 8 for meaning in meanings))
        self.navigate("lesson")
        expect(page.locator("#lesson [data-rule]")).to_have_count(3)
        lesson_text = page.locator("#lesson").inner_text()
        for term in ("الفعل", "الفاعل", "المفعول به"):
            self.assertIn(term, lesson_text)
        # The lesson and interactive home use the same simple sentence.
        normalized = lambda text: "".join(char for char in text if not "\u064b" <= char <= "\u065f")
        self.assertIn("قرأ الطالب الكتاب", " ".join(normalized(lesson_text).split()))
        self.navigate("quiz")
        expect(page.locator(".question-title")).to_be_visible()
        self.navigate("home")
        self.start()
        expect(page.locator("#quiz")).to_be_visible()


if __name__ == "__main__":
    unittest.main(verbosity=2)
