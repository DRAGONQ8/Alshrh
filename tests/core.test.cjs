const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function loadCore() {
  const html = fs.readFileSync(path.join(__dirname, '..', 'nahw-interactive.html'), 'utf8');
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
  const source = scripts.find((match) => match[1].includes('function createSession'));
  assert.ok(source, 'the HTML should contain the standalone session core');
  const context = {};
  vm.runInNewContext(source[1], context, { filename: 'nahw-core.js' });
  assert.ok(context.NahwCore, 'the standalone core should expose NahwCore');
  return context.NahwCore;
}

// Values created in the VM have different prototypes; compare their JSON data.
function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function assertStats(core, session, questions, expected) {
  assert.deepEqual(plain(core.stats(session, questions)), expected);
}

test('a new session starts in practice mode with ten untouched questions', () => {
  const core = loadCore();
  const session = core.createSession(10);
  assert.equal(session.index, 0);
  assert.equal(session.mode, 'practice');
  assert.equal(session.entries.length, 10);
  for (const entry of session.entries) {
    assert.deepEqual(plain(entry), {
      shown: false, selected: null, revealed: false, firstChoice: null,
    });
  }
  assertStats(core, session, [], { answered: 0, correct: 0, revealed: 0, total: 10 });
});

test('a learner can correct a selection before submitting and only the final answer is graded', () => {
  const core = loadCore();
  const session = core.createSession(1);
  const questions = [{ answer: 2 }];
  assert.equal(core.show(session), true);
  assert.equal(core.choose(session, 0), true);
  assert.equal(session.entries[0].firstChoice, null);
  assertStats(core, session, questions, { answered: 0, correct: 0, revealed: 0, total: 1 });
  assert.equal(core.choose(session, 2), true);
  assert.equal(session.entries[0].selected, 2);
  assert.equal(session.entries[0].firstChoice, null);
  assert.equal(core.submit(session), true);
  assert.equal(session.entries[0].firstChoice, 2);
  assert.equal(session.entries[0].revealed, true);
  assertStats(core, session, questions, { answered: 1, correct: 1, revealed: 1, total: 1 });
});

test('submit rejects hidden questions and empty selections without changing grading state', () => {
  const core = loadCore();
  const session = core.createSession(1);
  assert.equal(typeof core.submit, 'function', 'submission should be a separate action');
  assert.equal(core.submit(session), false);
  assert.equal(core.choose(session, 0), false);
  assert.equal(core.reveal(session), false);
  assert.equal(core.show(session), true);
  assert.equal(core.submit(session), false);
  assert.deepEqual(plain(session.entries[0]), {
    shown: true, selected: null, revealed: false, firstChoice: null,
  });
  assert.equal(core.choose(session, []), true);
  assert.equal(core.submit(session), false);
  assert.equal(session.entries[0].firstChoice, null);
  assert.equal(session.entries[0].revealed, false);
});

test('submitted answers cannot be changed or submitted again', () => {
  const core = loadCore();
  const session = core.createSession(1);
  core.show(session);
  core.choose(session, 1);
  assert.equal(core.submit(session), true);
  const submitted = plain(session.entries[0]);
  assert.equal(core.choose(session, 2), false);
  assert.equal(core.submit(session), false);
  core.reveal(session);
  core.show(session);
  assert.deepEqual(plain(session.entries[0]), submitted);
  assertStats(core, session, [{ answer: 2 }], { answered: 1, correct: 0, revealed: 1, total: 1 });
});

test('revealing a question skips grading even when the selected answer is correct', () => {
  const core = loadCore();
  const session = core.createSession(2);
  core.show(session);
  core.choose(session, 0);
  assert.equal(core.reveal(session), true);
  assert.equal(session.entries[0].firstChoice, null);
  assert.equal(session.entries[0].revealed, true);
  const skipped = plain(session.entries[0]);
  assert.equal(core.choose(session, 1), false);
  assert.equal(core.submit(session), false);
  assert.deepEqual(plain(session.entries[0]), skipped);
  core.go(session, 1);
  core.show(session);
  core.reveal(session);
  assertStats(core, session, [{ answer: 0 }, { answer: 1 }], {
    answered: 0, correct: 0, revealed: 2, total: 2,
  });
});

test('ordering answers can be corrected and require all positions before submission', () => {
  const core = loadCore();
  const session = core.createSession(1);
  core.show(session);
  assert.equal(core.choose(session, [0, 2]), true);
  assert.equal(core.submit(session, 3), false);
  assert.equal(session.entries[0].firstChoice, null);
  assert.equal(session.entries[0].revealed, false);
  assert.equal(core.choose(session, [0, 2, 1]), true);
  assert.equal(core.choose(session, [2, 0, 1]), true);
  assert.equal(session.entries[0].firstChoice, null);
  assert.equal(core.submit(session, 3), true);
  assert.deepEqual(plain(session.entries[0].firstChoice), [2, 0, 1]);
  assertStats(core, session, [{ answer: [2, 0, 1] }], {
    answered: 1, correct: 1, revealed: 1, total: 1,
  });
});

test('selection and submission snapshot ordering arrays without retaining caller references', () => {
  const core = loadCore();
  const session = core.createSession(1);
  core.show(session);
  const selected = [2, 1, 0];
  assert.equal(core.choose(session, selected), true);
  selected[0] = 99;
  assert.deepEqual(plain(session.entries[0].selected), [2, 1, 0]);
  assert.equal(core.submit(session, 3), true);
  assert.notEqual(session.entries[0].firstChoice, session.entries[0].selected);
  session.entries[0].selected[0] = 88;
  assert.deepEqual(plain(session.entries[0].firstChoice), [2, 1, 0]);
});

test('choose accepts only nonnegative integer options or arrays of unique integer options', () => {
  const core = loadCore();
  const session = core.createSession(1);
  core.show(session);
  assert.equal(core.choose(session, 0), true);
  const invalidValues = [null, undefined, '0', 'answer', -1, 1.5, NaN, Infinity, true,
    {}, [[0]], [0, 0], [-1, 0], [0, 1.5], [0, null], [0, '1']];
  for (const invalid of invalidValues) {
    assert.equal(core.choose(session, invalid), false, `reject ${String(invalid)}`);
    assert.equal(session.entries[0].selected, 0, 'rejected input must preserve the current selection');
    assert.equal(session.entries[0].firstChoice, null);
  }
  assert.equal(core.choose(session, [3, 1, 0]), true);
  assert.deepEqual(plain(session.entries[0].selected), [3, 1, 0]);
});

test('statistics count only submitted answers and preserve exact ordering', () => {
  const core = loadCore();
  const session = core.createSession(4);
  const questions = [{ answer: 0 }, { answer: [0, 1] }, { answer: 2 }, { answer: 1 }];
  core.show(session);
  core.choose(session, 0);
  core.submit(session);
  core.go(session, 1);
  core.show(session);
  core.choose(session, [1, 0]);
  core.submit(session, 2);
  core.go(session, 2);
  core.show(session);
  core.choose(session, 2);
  core.reveal(session);
  core.go(session, 3);
  core.show(session);
  core.choose(session, 1);
  assertStats(core, session, questions, { answered: 2, correct: 1, revealed: 3, total: 4 });
});

test('statistics never count a matching unrevealed firstChoice as correct', () => {
  const core = loadCore();
  const session = core.createSession(1);
  session.entries[0].firstChoice = 0;
  assertStats(core, session, [{ answer: 0 }], { answered: 1, correct: 0, revealed: 0, total: 1 });
});

test('navigation validates bounds and reset clears every question and restores practice mode', () => {
  const core = loadCore();
  const session = core.createSession(3);
  for (const invalid of [-1, 3, 1.5, '1', NaN, Infinity, null]) {
    assert.equal(core.go(session, invalid), false);
    assert.equal(session.index, 0);
  }
  assert.equal(core.go(session, 2), true);
  core.show(session);
  core.choose(session, [1, 0]);
  core.reveal(session);
  assert.equal(core.go(session, 0), true);
  core.show(session);
  core.choose(session, 1);
  session.mode = 'review';
  assert.equal(core.reset(session), true);
  assert.equal(session.index, 0);
  assert.equal(session.mode, 'practice');
  assert.equal(session.entries.length, 3);
  for (const entry of session.entries) {
    assert.deepEqual(plain(entry), {
      shown: false, selected: null, revealed: false, firstChoice: null,
    });
  }
  assertStats(core, session, [], { answered: 0, correct: 0, revealed: 0, total: 3 });
});
