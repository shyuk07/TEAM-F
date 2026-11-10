#!/usr/bin/env node
// 작업 주석(TODO·FIXME·open-issues) 목록과 형식 검사. 정본: ../SKILL.md
// 사용: node .claude/skills/code-annotations/scripts/annotations.mjs list [--tag TODO|FIXME|open-issues] [--match 글자]
//       node .claude/skills/code-annotations/scripts/annotations.mjs check
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(fileURLToPath(new URL('.', import.meta.url)), '..', '..', '..', '..')
const DIRS = ['src', 'tests', 'e2e']
const EXT = /\.(ts|tsx|css|mjs)$/
const SKIP = new Set(['src/app/styles/tokens.css', 'src/app/styles/bundle.css'])
const COMMENT = String.raw`^\s*(?:\/\/+|\/\*+|\*)\s*`
const TAG_LINE = new RegExp(`${COMMENT}(TODO|FIXME|HACK|XXX)\\b[:(]?\\s*(.*)$`)
const OPEN_ISSUES = new RegExp(`${COMMENT}open-issues:\\s*(.*)$`)
const FIELD = new RegExp(`${COMMENT}(왜|언제):\\s*(.*)$`)
const BANNED = new Set(['HACK', 'XXX'])
const FOLLOW_LINES = 4

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name.startsWith('.')) continue
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (EXT.test(name) && !name.endsWith('.d.ts')) out.push(p)
  }
  return out
}

const clean = (s) => s.replace(/\s*\*\/\s*$/, '').trim()

function collect() {
  const items = []
  for (const d of DIRS) {
    const abs = join(ROOT, d)
    if (!existsSync(abs)) continue
    for (const file of walk(abs)) {
      const rel = relative(ROOT, file).split(sep).join('/')
      if (SKIP.has(rel)) continue
      const lines = readFileSync(file, 'utf8').split('\n')
      lines.forEach((line, i) => {
        const open = OPEN_ISSUES.exec(line)
        if (open) {
          items.push({ tag: 'open-issues', file: rel, line: i + 1, summary: clean(open[1]) })
          return
        }
        const m = TAG_LINE.exec(line)
        if (!m) return
        const item = { tag: m[1], file: rel, line: i + 1, summary: clean(m[2]) }
        for (let j = i + 1; j < Math.min(lines.length, i + 1 + FOLLOW_LINES); j++) {
          const f = FIELD.exec(lines[j])
          if (!f) break
          item[f[1] === '왜' ? 'why' : 'when'] = clean(f[2])
        }
        items.push(item)
      })
    }
  }
  return items
}

function problems(item) {
  const out = []
  if (BANNED.has(item.tag)) return [`${item.tag} 태그는 쓰지 않는다. FIXME 또는 TODO로 바꾼다`]
  if (item.tag === 'open-issues') {
    if (!item.summary) out.push('open-issues: 뒤에 항목과 임시 동작을 적는다')
    return out
  }
  if (!item.summary) out.push('첫 줄 요약이 비어 있다')
  if (!item.why) out.push("'왜:' 줄이 없다")
  if (!item.when) out.push("'언제:' 줄이 없다")
  if (item.tag === 'FIXME' && item.when && /^리팩터링 시/.test(item.when))
    out.push("FIXME의 '언제:'에 '리팩터링 시'를 쓰지 않는다. 확인할 사람이 있는 시점을 정한다")
  return out
}

function arg(name) {
  const i = process.argv.indexOf(name)
  return i === -1 ? undefined : process.argv[i + 1]
}

const cmd = process.argv[2]
const items = collect()

if (cmd === 'list') {
  const tag = arg('--tag')
  const match = arg('--match')?.toLowerCase()
  const shown = items.filter(
    (it) =>
      (!tag || it.tag === tag) &&
      (!match || [it.summary, it.why, it.when].some((s) => s?.toLowerCase().includes(match))),
  )
  for (const it of shown) {
    console.log(`${it.tag} ${it.file}:${it.line}  ${it.summary}`)
    if (it.why) console.log(`    왜: ${it.why}`)
    if (it.when) console.log(`    언제: ${it.when}`)
  }
  const count = (t) => shown.filter((it) => it.tag === t).length
  console.log(`\n${shown.length}건 (FIXME ${count('FIXME')}, TODO ${count('TODO')}, open-issues ${count('open-issues')})`)
} else if (cmd === 'check') {
  let bad = 0
  for (const it of items) {
    for (const p of problems(it)) {
      console.log(`[주석형식] ${it.file}:${it.line} ${it.tag}: ${p}`)
      bad++
    }
  }
  console.log(bad ? `\n형식 위반 ${bad}건 (주석 ${items.length}개 검사)` : `형식 위반 0건 (주석 ${items.length}개 검사)`)
  process.exit(bad ? 1 : 0)
} else {
  console.error('사용: annotations.mjs list [--tag TODO|FIXME|open-issues] [--match 글자] | check')
  process.exit(2)
}
