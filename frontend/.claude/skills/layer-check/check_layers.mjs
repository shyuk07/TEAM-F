#!/usr/bin/env node
// 마감 직전 프론트엔드 FSD + slice 안 4계층 규칙 검사
//   node .claude/skills/layer-check/check_layers.mjs [src 경로]
// 위반이 있으면 종료코드 1, 없으면 0. 규칙 ID는 frontend-invariants 스킬이 정본이다.
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs'
import { join, relative, dirname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const SRC = resolve(process.argv[2] ?? join(ROOT, 'src'))

const LAYERS = ['app', 'pages', 'widgets', 'features', 'entities', 'shared']
const RANK = Object.fromEntries(LAYERS.map((l, i) => [l, i]))
const SLICED = new Set(['pages', 'widgets', 'features', 'entities'])
const INNER = ['presentation', 'application', 'domain', 'infrastructure']
const ALLOWED_INNER = {
  presentation: ['presentation', 'application', 'domain'],
  application: ['application', 'domain', 'infrastructure'],
  infrastructure: ['infrastructure', 'domain'],
  domain: ['domain'],
}
const DOMAIN_BANNED_PKGS = /^(react|react-dom|react-router|react-router-dom)(\/|$)/
const DOMAIN_BANNED_CODE = [
  [/\bwindow\./, 'window 사용'],
  [/\bdocument\./, 'document 사용'],
  [/\b(localStorage|sessionStorage)\b/, '브라우저 저장소 사용'],
  [/import\.meta\.env/, 'import.meta.env 사용'],
]
const COLOR = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b|\b(?:rgba?|hsla?)\(/
const DESIGN_COPIES = new Set(['app/styles/tokens.css', 'app/styles/bundle.css'])
const TEST_FILE = /\.(test|spec)\.(ts|tsx)$/

const violations = []
const report = (tag, file, line, msg) => violations.push({ tag, file, line, msg })

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name.startsWith('.')) continue
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(ts|tsx|css)$/.test(name) && !name.endsWith('.d.ts')) out.push(p)
  }
  return out
}

// src 기준 경로 → { layer, slice, inner, parts }
// 파일 경로는 entities/stray.ts처럼 slice 없이 놓일 수 있고, import 대상은 '@/entities/offer'처럼 slice에서 끝날 수 있다.
function locate(rel, { isFile }) {
  const parts = rel.split('/')
  const layer = LAYERS.includes(parts[0]) ? parts[0] : null
  const minLen = isFile ? 3 : 2
  const slice = layer && SLICED.has(layer) && parts.length >= minLen ? parts[1] : null
  let inner = null
  if (slice && parts.length > 2) inner = parts.length > 3 ? parts[2] : parts[2].replace(/\.(ts|tsx)$/, '')
  return { layer, slice, inner, parts }
}

function resolveSpec(spec, fileRel) {
  if (spec.startsWith('@/')) return spec.slice(2)
  if (spec.startsWith('.')) {
    const abs = resolve(SRC, dirname(fileRel), spec)
    const rel = relative(SRC, abs)
    return rel.startsWith('..') ? null : rel.split(sep).join('/')
  }
  return undefined // 외부 패키지
}

function stripComments(line, state) {
  let out = ''
  for (let i = 0; i < line.length; i++) {
    if (state.block) {
      if (line[i] === '*' && line[i + 1] === '/') { state.block = false; i++ }
      continue
    }
    if (line[i] === '/' && line[i + 1] === '*') { state.block = true; i++; continue }
    if (line[i] === '/' && line[i + 1] === '/') break
    out += line[i]
  }
  return out
}

function checkStructure(rel, loc) {
  const { layer, slice, inner, parts } = loc
  if (!layer) {
    if (parts.length > 1) report('[구조]', rel, 1, `FSD 계층(${LAYERS.join(', ')}) 밖의 폴더`)
    return
  }
  if (SLICED.has(layer) && !slice) report('[구조]', rel, 1, `${layer} 계층 바로 아래 파일. slice 폴더 안에 둔다 (F3)`)
  if (slice) {
    if (parts.length === 3 && inner !== 'index') report('[구조]', rel, 1, 'slice 루트에는 index.ts만 둔다 (F4)')
    if (parts.length > 3 && !INNER.includes(inner))
      report('[구조]', rel, 1, `slice 안 폴더 '${inner}'. ${INNER.join(' / ')}만 쓴다 (F4)`)
  }
  if ((layer === 'app' || layer === 'shared') && parts.length > 2 && INNER.includes(parts[1]))
    report('[구조]', rel, 1, `${layer}에는 slice·4계층 폴더를 두지 않는다 (F3)`)
}

function checkImport(rel, loc, lineNo, spec) {
  const target = resolveSpec(spec, rel)
  if (target === null) return
  if (target === undefined) {
    if (loc.inner === 'domain' && DOMAIN_BANNED_PKGS.test(spec))
      report('[외부의존]', rel, lineNo, `domain에서 '${spec}' import (F6)`)
    return
  }
  const t = locate(target, { isFile: false })
  const srcRank = loc.layer ? RANK[loc.layer] : -1 // src 루트 파일(main.tsx)은 app보다 위
  if (!t.layer) return

  if (RANK[t.layer] < srcRank) {
    report('[계층방향]', rel, lineNo, `${loc.layer} → ${t.layer} ('${spec}'). 아래 계층만 import한다 (F1)`)
    return
  }
  const sameSlice = loc.layer === t.layer && loc.slice && loc.slice === t.slice
  if (loc.layer === t.layer && SLICED.has(t.layer) && !sameSlice) {
    report('[같은계층]', rel, lineNo, `${loc.layer}/${loc.slice} → ${t.layer}/${t.slice}. 같은 계층 slice끼리 import하지 않는다 (F1)`)
    return
  }
  if (!sameSlice && SLICED.has(t.layer)) {
    const viaIndex = t.parts.length === 2 || (t.parts.length === 3 && t.parts[2] === 'index')
    if (!viaIndex) report('[공개API]', rel, lineNo, `'${spec}'. ${t.layer}/${t.slice}의 index.ts로만 import한다 (F2)`)
  }
  if (sameSlice && loc.inner !== 'index' && INNER.includes(loc.inner) && INNER.includes(t.inner)) {
    if (!ALLOWED_INNER[loc.inner].includes(t.inner))
      report('[의존방향]', rel, lineNo, `${loc.inner} → ${t.inner} ('${spec}') (F5)`)
  }
  if (t.layer === 'shared' && t.parts[1] === 'api' && ['presentation', 'application'].includes(loc.inner))
    report('[의존방향]', rel, lineNo, `${loc.inner} → shared/api. 서버 호출은 infrastructure만 한다 (F5, F8)`)
  if (loc.inner === 'domain' && t.layer === 'shared' && t.parts[1] !== 'lib')
    report('[외부의존]', rel, lineNo, `domain → shared/${t.parts[1]}. domain은 shared/lib의 순수 함수만 쓴다 (F6)`)
}

function checkFile(abs) {
  const rel = relative(SRC, abs).split(sep).join('/')
  const loc = locate(rel, { isFile: true })
  const isTest = TEST_FILE.test(rel)
  const isCss = rel.endsWith('.css')
  checkStructure(rel, loc)

  const state = { block: false }
  readFileSync(abs, 'utf8').split('\n').forEach((raw, i) => {
    const line = stripComments(raw, state)
    const n = i + 1
    if (!DESIGN_COPIES.has(rel) && COLOR.test(line))
      report('[하드코딩색]', rel, n, `색 값 직접 사용: ${line.trim().slice(0, 80)} (F12)`)
    if (isCss || isTest) return

    for (const re of [/\bfrom\s+['"]([^'"]+)['"]/g, /^\s*import\s+['"]([^'"]+)['"]/g, /\bimport\(\s*['"]([^'"]+)['"]\s*\)/g])
      for (const m of line.matchAll(re)) checkImport(rel, loc, n, m[1])

    if (/\bfetch\s*\(/.test(line) && !(loc.layer === 'shared' && loc.parts[1] === 'api'))
      report('[fetch위치]', rel, n, 'fetch는 shared/api 클라이언트에서만 호출한다 (F8)')
    if (loc.inner === 'domain')
      for (const [re, what] of DOMAIN_BANNED_CODE)
        if (re.test(line)) report('[외부의존]', rel, n, `domain에서 ${what} (F6)`)
  })
}

if (!existsSync(SRC)) {
  console.log(`검사 대상 없음: ${SRC} 가 없습니다.`)
  process.exit(0)
}
const files = walk(SRC)
files.forEach(checkFile)

if (violations.length === 0) {
  console.log(`위반 0건 (파일 ${files.length}개 검사)`)
  process.exit(0)
}
violations.sort((a, b) => a.tag.localeCompare(b.tag) || a.file.localeCompare(b.file) || a.line - b.line)
for (const v of violations) console.log(`${v.tag} ${v.file}:${v.line} ${v.msg}`)
const counts = violations.reduce((m, v) => ((m[v.tag] = (m[v.tag] ?? 0) + 1), m), {})
console.log(`\n위반 ${violations.length}건 (파일 ${files.length}개 검사): ` +
  Object.entries(counts).map(([k, c]) => `${k} ${c}`).join(', '))
process.exit(1)
