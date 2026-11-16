// Screenshot a browser view of real saved evidence. Author: 殷明骏.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '/home/yinwhcmy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const esc = s => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const read = p => fs.existsSync(path.join(root,p)) ? fs.readFileSync(path.join(root,p),'utf8') : '(pending)';
const data = JSON.parse(read('output/analysis/results.json'));
const shown=data.receipts;
const out = path.join(root,'evidence/screenshots');
fs.mkdirSync(out,{recursive:true});
const panels = [
  ['01_schedule_configuration', 'Hourly execution configuration', [
    ['Installed crontab',read('evidence/crontab_installed.txt')],
    ['Expected local times',JSON.parse(read('cron/schedule.json')).expected_times.join('\n')]
  ]],
  ['01_schedule_execution', 'Original cron execution evidence', [
    ['Original scheduler events',read('cron/scheduled.log').split('\n').filter(s=>/^(CRON_|SCHEDULE_)/.test(s)).join('\n')],
    ['Cron ancestry and actual timestamps',shown.map(r=>`Execution ${r.sequence}: ${r.started_at} to ${r.completed_at}; ${r.records} records\n`+r.ancestors.filter(a=>a.command.includes('/usr/sbin/cron')).map(a=>`PID ${a.pid}, PPID ${a.ppid}: ${a.command}`).join('\n')).join('\n')]
  ]],
  ...data.receipts.map(r=>{
    const log=read(`${r.output}/experiment.log`).split('\n').filter(s=>/^(SUITE_RESULT|VALIDATION_SUCCESS|BATCH_SUCCESS)/.test(s)).join('\n');
    return [`02_execution_${r.sequence}`, `Execution ${r.sequence} log and summary`, [['Original score lines',log],[`Extracted summary_report.txt`,read(`${r.output}/summary_report.txt`)]]];
  }),
  ['03_unix_tools', 'Unix tools and input validation', [
    ['Actual permission and Bash help output',read('evidence/unix_help.txt').split('\n').slice(0,14).join('\n')],
    ['Recorded editor session', 'evidence/editor.typescript retains the actual vi session, the /SUITE_RESULT search and :q! exit.']
  ]],
  ['04_input_validation', 'Pipeline input and record checks', [
    ['Actual test transcript',read('evidence/pipeline_tests.log').split('\n').filter(s=>/^(test_|Ran |OK)/.test(s)).join('\n')]
  ]]
];
if(data.precomputed_input){
  const r=data.precomputed_input;
  panels.splice(panels.length-1,0,['02_manual_prerun','Manual numerical pre-run',[
    ['Source and actual timestamps',`${r.source}\n${r.started_at} to ${r.completed_at}\nHourly scheduling receipts: ${data.scheduled_successes} of 3`],
    ['Validated numerical summary',read(`${r.output}/summary_report.txt`)]
  ]]);
}
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome'});
try {
  for (const name of fs.readdirSync(out)) if (/\.(png|html)$/.test(name)) fs.unlinkSync(path.join(out,name));
  const page=await browser.newPage({viewport:{width:1000,height:800},deviceScaleFactor:1.5});
  for(const [name,title,blocks] of panels){
    const html=`<!doctype html><meta charset="utf-8"><title>${esc(title)}</title><style>
      body{font:24px Georgia,serif;margin:28px;color:#152331;background:#fff}h1{font-size:32px;margin:0 0 12px}p{margin:0 0 22px;color:#425466}h2{font:600 24px Arial;margin:24px 0 10px}pre{font:24px/1.35 monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;border:1px solid #d9dfe5;padding:16px;margin:0}footer{margin-top:24px;font-size:18px;color:#425466}
      </style><h1>${esc(title)}</h1><p>Project3 | ${data.complete?'Three scheduled executions validated':'In progress'}</p>
      ${blocks.map(([label,body])=>`<h2>${esc(label)}</h2><pre>${esc(body)}</pre>`).join('')}<footer>Source files accompany this capture of the saved execution evidence.</footer>`;
    const target=path.join(out,`${name}.html`);fs.writeFileSync(target,html);
    await page.goto('file://'+target);await page.locator('body').screenshot({path:path.join(out,`${name}.png`)});
  }
} finally {await browser.close();}
console.log(`Saved ${panels.length} evidence screenshots`);
