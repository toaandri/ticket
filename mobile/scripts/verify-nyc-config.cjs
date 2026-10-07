// The narrowly scoped js-yaml override removes vulnerable argparse/sprintf-js.
// Verify the actual consumer's .load API with a temporary YAML config.
const assert = require('node:assert/strict');
const { mkdtemp, writeFile, rm } = require('node:fs/promises');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { loadNycConfig } = require('@istanbuljs/load-nyc-config');

(async () => {
  const directory = await mkdtemp(join(tmpdir(), 'ticket-nyc-'));
  try {
    await writeFile(join(directory, '.nycrc.yml'), 'all: true\ninclude:\n  - src/**/*.tsx\nreporter:\n  - text\n');
    const config = await loadNycConfig({ cwd: directory, nycrcPath: join(directory, '.nycrc.yml') });
    assert.equal(config.all, true); assert.deepEqual(config.include, ['src/**/*.tsx']); assert.deepEqual(config.reporter, ['text']);
    console.log('NYC YAML configuration loads correctly with the scoped js-yaml override.');
  } finally { await rm(directory, { recursive: true, force: true }); }
})().catch(error => { console.error(error); process.exitCode = 1; });
