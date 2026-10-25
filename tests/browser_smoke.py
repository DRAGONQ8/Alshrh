"""Run with: python tests/browser_smoke.py (serve the project and set NAHW_URL).

Override NAHW_URL to test another served copy. Requires Python Playwright and
Chromium, but does not download a browser or make requests to third-party sites.
"""

import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get(
    "NAHW_URL", "http://127.0.0.1:8765/Alshrh/nahw-interactive.html"
)
STORAGE_KEY = "nahw-progress-v2"
ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / ".test-artifacts"
SCREENSHOTS = ARTIFACTS / "screenshots"


class BrowserSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), args=["--no-sandbox"]
        )
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)

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

    def new_page(self, width=1280, initial_storage=None):
        context = self.browser.new_context(
            viewport={"width": width, "height": 900},
            accept_downloads=True,
            reduced_motion="reduce",
        )
        self.contexts.append(context)
        if initial_storage is not None:
            context.add_init_script(
                "try { localStorage.setItem(%s, %s); } catch (_) {}"
                % (json.dumps(STORAGE_KEY), json.dumps(initial_storage))
            )
        page = context.new_page()
        page.set_default_timeout(6000)
        page.on("pageerror", lambda error: self.javascript_errors.append(str(error)))
        page.on("request", self.check_request)
        return page

    def check_request(self, request):
        target = urlsplit(request.url)
        if target.scheme not in ("http", "https"):
            return
        if target.path.endswith("/favicon.ico"):
            return
        allowed = {
            (parsed.scheme, parsed.netloc, parsed.path)
            for parsed in map(urlsplit, self.allowed_document_urls)
        }
        if (target.scheme, target.netloc, target.path) not in allowed:
            self.unexpected_requests.append(request.url)

    def open_app(self, page=None):
        page = page or self.page
        page.goto(URL, wait_until="networkidle")
        page.wait_for_function("Boolean(globalThis.NahwApp)")
        return page

    def quiz(self, page=None):
        page = page or self.page
        page.evaluate("NahwApp.navigate('quiz')")
        expect(page.locator("#quiz")).to_be_visible()
        expect(page.locator(".question-title")).to_be_visible()
        expect(page.locator("#questionMap button")).to_have_count(10)

    def entry(self, index=None, page=None):
        page = page or self.page
        return page.evaluate(
            "index => NahwApp.session.entries[index === null ? NahwApp.session.index : index]",
            index,
        )

    def jump(self, index, page=None):
        page = page or self.page
        page.locator(f'[data-question="{index}"]').click()
        expect(page.locator(".question-title")).to_be_visible()
        self.assertEqual(page.evaluate("NahwApp.session.index"), index)

    def assert_fresh(self, page):
        state = page.evaluate("NahwApp.session")
        self.assertEqual(state["index"], 0)
        self.assertEqual(state["mode"], "practice")
        self.assertEqual(len(state["entries"]), 10)
        for entry in state["entries"]:
            self.assertIsNone(entry["selected"])
            self.assertIsNone(entry["firstChoice"])
            self.assertFalse(entry["revealed"])

    def test_selection_keyboard_submit_skip_and_presentation_gate(self):
        page = self.open_app()
        self.quiz()
        answer = page.evaluate("NahwApp.questions[0].answer")
        wrong = page.evaluate("(NahwApp.questions[0].answer + 1) % NahwApp.questions[0].options.length")
        page.locator(f'[data-answer="{wrong}"]').focus()
        page.keyboard.press("Space")
        self.assertEqual(self.entry()["selected"], wrong)
        self.assertIsNone(self.entry()["firstChoice"])
        self.assertFalse(self.entry()["revealed"])
        expect(page.locator("#answerBox")).to_have_count(0)
        page.locator(f'[data-answer="{answer}"]').click()
        page.locator("#hintBtn").click()
        expect(page.locator("#hintBtn")).to_have_attribute("aria-expanded", "true")
        self.assertIsNone(self.entry()["firstChoice"])
        page.locator("#checkAnswer").click()
        expect(page.locator("#answerBox")).to_be_visible()
        self.assertEqual(self.entry()["firstChoice"], answer)
        self.assertTrue(self.entry()["revealed"])
        page.locator(f'[data-answer="{wrong}"]').dispatch_event("click")
        self.assertEqual(self.entry()["firstChoice"], answer)
        page.locator("#quizNext").click()
        expect(page.locator(".question-title")).to_be_visible()
        page.locator("#revealAnswer").click()
        self.assertIsNone(self.entry()["firstChoice"])
        self.assertTrue(self.entry()["revealed"])
        page.locator('[data-mode="presentation"]').click()
        # Select a fresh question in presentation mode without assuming its title exists.
        page.locator('[data-question="2"]').click()
        expect(page.locator("#showQuestion")).to_be_visible()
        expect(page.locator(".question-title")).to_have_count(0)
        page.locator("#showQuestion").click()
        expect(page.locator(".question-title")).to_be_visible()
        page.locator('[data-mode="practice"]').click()
        self.jump(3)
        expect(page.locator("#showQuestion")).to_have_count(0)

    def test_lesson_examples_keep_tenses_in_sync_and_skip_link_is_keyboard_accessible(self):
        page = self.open_app()
        page.keyboard.press("Tab")
        expect(page.locator(".skip")).to_be_focused()
        expect(page.locator(".skip")).to_be_in_viewport()
        page.keyboard.press("Enter")
        expect(page.locator("#main")).to_be_focused()
        page.evaluate("NahwApp.navigate('lesson')")
        expect(page.locator(".tense-chip b")).to_have_text(["قَرَأَ", "يَقْرَأُ", "اِقْرَأْ"])
        page.locator("#nextExample").click()
        expect(page.locator(".tense-chip b")).to_have_text(["فَتَحَ", "يَفْتَحُ", "اِفْتَحْ"])
        page.locator('[data-example-word="1"]').click()
        expect(page.locator("#exampleInsight")).to_contain_text("الحارس")
        page.locator("#nextExample").click()
        expect(page.locator(".tense-chip b")).to_have_text(["زَرَعَ", "يَزْرَعُ", "اِزْرَعْ"])

    def test_ordering_partial_edit_navigation_and_reload_persistence(self):
        page = self.open_app()
        self.quiz()
        index = page.evaluate("NahwApp.questions.findIndex(q => q.kind === 'order')")
        self.assertGreaterEqual(index, 0)
        answer = page.evaluate("i => NahwApp.questions[i].answer", index)
        self.jump(index)
        expect(page.locator("#checkAnswer")).to_be_disabled()
        page.locator(f'[data-order="{answer[0]}"]').click()
        expect(page.locator("#checkAnswer")).to_be_disabled()
        self.assertFalse(self.entry()["revealed"])
        self.assertIsNone(self.entry()["firstChoice"])
        self.jump(0)
        self.jump(index)
        expect(page.locator("[data-remove-order]")).to_have_count(1)
        page.reload(wait_until="networkidle")
        # A resume action may restore the saved screen from the home screen.
        if page.locator("#resumeBtn").is_visible():
            page.locator("#resumeBtn").click()
        self.quiz(page)
        self.jump(index)
        expect(page.locator("[data-remove-order]")).to_have_count(1)
        page.locator('[data-remove-order="0"]').click()
        expect(page.locator("[data-remove-order]")).to_have_count(0)
        expect(page.locator("#checkAnswer")).to_be_disabled()
        for option in answer:
            page.locator(f'[data-order="{option}"]').click()
        expect(page.locator("#checkAnswer")).to_be_enabled()
        page.locator("#checkAnswer").click()
        self.assertEqual(self.entry()["firstChoice"], answer)
        page.reload(wait_until="networkidle")
        self.quiz(page)
        self.jump(index)
        self.assertEqual(self.entry()["firstChoice"], answer)
        self.assertTrue(self.entry()["revealed"])
        expect(page.locator("#answerBox")).to_be_visible()

    def test_all_ten_correct_summary_review_and_retry_missed(self):
        page = self.open_app()
        self.quiz()
        questions = page.evaluate("NahwApp.questions")
        self.assertEqual(len(questions), 10)
        for index, question in enumerate(questions):
            self.jump(index)
            answer = question["answer"]
            if isinstance(answer, list):
                for option in answer:
                    page.locator(f'[data-order="{option}"]').click()
            else:
                page.locator(f'[data-answer="{answer}"]').click()
            page.locator("#checkAnswer").click()
            self.assertEqual(self.entry()["firstChoice"], answer)
            page.locator("#quizNext").click()
        expect(page.locator("#summary")).to_be_visible()
        expect(page.locator("#resumeBtn")).to_be_hidden()
        stats = page.evaluate("NahwCore.stats(NahwApp.session, NahwApp.questions)")
        self.assertEqual(stats, {"answered": 10, "correct": 10, "revealed": 10, "total": 10})
        expect(page.locator("#summaryReview [data-review-question]")).to_have_count(10)
        page.screenshot(path=str(SCREENSHOTS / "summary-complete.png"), full_page=True)
        page.locator('#summaryReview [data-review-question="0"]').click()
        expect(page.locator("#quiz")).to_be_visible()
        expect(page.locator("#answerBox")).to_be_visible()
        self.assertEqual(page.evaluate("NahwApp.session.index"), 0)
        # A new context supplies an incomplete round with one wrong submitted answer.
        incomplete = self.open_app(self.new_page())
        self.quiz(incomplete)
        wrong = (questions[0]["answer"] + 1) % len(questions[0]["options"])
        incomplete.locator(f'[data-answer="{wrong}"]').click()
        incomplete.locator("#checkAnswer").click()
        incomplete.evaluate("NahwApp.navigate('summary')")
        expect(incomplete.locator("#resumeBtn")).to_be_visible()
        incomplete.locator("#resumeBtn").click()
        expect(incomplete.locator("#quiz")).to_be_visible()
        incomplete.evaluate("NahwApp.navigate('summary')")
        incomplete.locator("#retryMissed").click()
        if incomplete.locator("dialog[open]").count():
            incomplete.locator("#confirmRestart").click()
        expect(incomplete.locator("#quiz")).to_be_visible()
        self.assertEqual(incomplete.evaluate("NahwApp.session.index"), 0)
        self.assertFalse(self.entry(0, incomplete)["revealed"])
        self.assertIsNone(self.entry(0, incomplete)["firstChoice"])

    def test_malformed_saved_progress_falls_back_to_a_usable_fresh_round(self):
        valid_entries = [
            {"shown": False, "selected": None, "revealed": False, "firstChoice": None}
            for _ in range(10)
        ]
        duplicate_order = [dict(entry) for entry in valid_entries]
        duplicate_order[4] = {
            "shown": True, "selected": [0, 0], "revealed": False, "firstChoice": None
        }
        unrevealed_first_choice = [dict(entry) for entry in valid_entries]
        unrevealed_first_choice[0] = {
            "shown": True, "selected": 0, "revealed": False, "firstChoice": 0
        }
        malformed = [
            "{not valid JSON",
            "null",
            "[]",
            json.dumps({"version": 2, "session": {"index": 999, "entries": []}}),
            json.dumps({"version": 2, "session": {"index": -1, "mode": "practice", "entries": [{"selected": "bad"}] * 10}}),
            json.dumps({"version": 2, "session": {"index": 4, "mode": "practice", "entries": duplicate_order}}),
            json.dumps({"version": 2, "session": {"index": 1, "mode": "practice", "entries": unrevealed_first_choice}}),
        ]
        for payload in malformed:
            with self.subTest(payload=payload[:65]):
                page = self.open_app(self.new_page(initial_storage=payload))
                self.assert_fresh(page)
                self.quiz(page)
                page.locator('[data-answer="0"]').click()
                expect(page.locator("#checkAnswer")).to_be_enabled()

    def test_denied_local_storage_still_allows_learning_and_explains_save_status(self):
        self.page.context.add_init_script("""(() => {
            const denied = () => { throw new DOMException('Storage disabled for test', 'SecurityError'); };
            Object.defineProperty(Storage.prototype, 'getItem', {value: denied, configurable: true});
            Object.defineProperty(Storage.prototype, 'setItem', {value: denied, configurable: true});
        })();""")
        page = self.open_app()
        self.assert_fresh(page)
        self.quiz(page)
        answer = page.evaluate("NahwApp.questions[0].answer")
        page.locator(f'[data-answer="{answer}"]').click()
        page.locator("#checkAnswer").click()
        expect(page.locator("#answerBox")).to_be_visible()
        self.assertEqual(self.entry()["firstChoice"], answer)
        self.assertEqual(
            page.evaluate("NahwCore.stats(NahwApp.session, NahwApp.questions)"),
            {"answered": 1, "correct": 1, "revealed": 1, "total": 10},
        )
        expect(page.locator("#saveState")).to_contain_text("الحفظ غير متاح")

    def test_mobile_large_text_dialog_names_and_no_horizontal_overflow(self):
        for width in (360, 390, 768):
            with self.subTest(width=width):
                page = self.open_app(self.new_page(width=width))
                for trigger, dialog_id in (
                    ("#settingsBtn", "#settingsDialog"),
                    ("#helpBtn", "#helpDialog"),
                    ("#restartBtn", "#restartDialog"),
                ):
                    page.evaluate("screen => NahwApp.navigate(screen)", "summary" if trigger == "#restartBtn" else "home")
                    page.locator(trigger).click()
                    expect(page.locator(dialog_id)).to_be_visible()
                    expect(page.get_by_role("dialog", name=re.compile(r"\S"))).to_have_count(1)
                    self.assert_no_overflow(page, f"{width}px {dialog_id}")
                    page.locator(f"{dialog_id} [data-close]").first.click()
                page.locator("#settingsBtn").click()
                page.locator("#fontLarge").click()
                page.locator("#settingsDialog [data-close]").first.click()
                expect(page.locator("body")).to_have_class(re.compile(r"large-text"))
                for screen in ("home", "lesson", "quiz", "summary"):
                    page.evaluate("screen => NahwApp.navigate(screen)", screen)
                    self.assert_no_overflow(page, f"{width}px large text {screen}")
                self.quiz(page)
                for index in range(10):
                    self.jump(index, page)
                    self.assert_no_overflow(page, f"{width}px large text question {index + 1}")
                page.screenshot(path=str(SCREENSHOTS / f"mobile-{width}-large-text.png"), full_page=True)

    def assert_no_overflow(self, page, label):
        dimensions = page.evaluate("""() => ({
            viewport: document.documentElement.clientWidth,
            html: document.documentElement.scrollWidth,
            body: document.body.scrollWidth,
            elements: [...document.querySelectorAll('body *')].filter(el => {
                const s = getComputedStyle(el), r = el.getBoundingClientRect();
                return s.display !== 'none' && s.visibility !== 'hidden' &&
                    r.width > 0 && (r.left < -1 || r.right > innerWidth + 1);
            }).slice(0, 8).map(el => el.id || el.className || el.tagName)
        })""")
        self.assertLessEqual(dimensions["html"], dimensions["viewport"] + 1, f"{label}: {dimensions}")
        self.assertLessEqual(dimensions["body"], dimensions["viewport"] + 1, f"{label}: {dimensions}")

    def test_downloaded_html_reopens_fresh_with_no_injected_scripts_or_iframes(self):
        page = self.open_app()
        self.quiz()
        page.locator('[data-answer="0"]').click()
        page.locator("#checkAnswer").click()
        self.jump(4)
        page.locator("#hintBtn").click()
        page.locator("#settingsBtn").click()
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
            exported_url = f"{origin.scheme}://{origin.netloc}{base_path}/.test-artifacts/{Path(directory).name}/{target.name}"
            self.allowed_document_urls.add(exported_url)
            exported = self.new_page()
            exported.goto(exported_url, wait_until="networkidle")
            exported.wait_for_function("Boolean(globalThis.NahwApp)")
            expect(exported.locator("#home")).to_be_visible()
            expect(exported.locator("dialog[open]")).to_have_count(0)
            expect(exported.locator("iframe, script[src]")).to_have_count(0)
            expect(exported.locator("script")).to_have_count(3)
            self.assert_fresh(exported)
            self.quiz(exported)
            expect(exported.locator("#checkAnswer")).to_be_disabled()
            expect(exported.locator("#answerBox")).to_have_count(0)
            page.screenshot(path=str(SCREENSHOTS / "export-source.png"), full_page=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
