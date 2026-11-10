#!/usr/bin/env node
// 디자인 시스템 CSS 복사본 관리 (Windows·macOS·Linux 공통, Node만 필요)
//   node sync_styles.mjs check   원본과 src/app/styles/ 복사본이 같은지 확인 (다르면 종료코드 1)
//   node sync_styles.mjs copy    원본을 src/app/styles/로 다시 복사
// 줄바꿈(CRLF/LF) 차이는 같은 내용으로 본다. Windows의 git 자동 변환 때문에 생기는 차이다.
import { copyFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..')
const PAIRS = [
  ['../docs/design-system/tokens.css', 'src/app/styles/tokens.css'],
  ['../docs/design-system/components/bundle.css', 'src/app/styles/bundle.css'],
].map(([src, dst]) => [resolve(ROOT, src), resolve(ROOT, dst)])

const show = (p) => relative(ROOT, p).split('\\').join('/')
const normalize = (p) => readFileSync(p, 'utf8').replace(/\r\n/g, '\n')

function check() {
  let failed = false
  for (const [src, dst] of PAIRS) {
    if (!existsSync(src)) { console.log(`[FAIL] 원본 없음: ${show(src)}`); failed = true; continue }
    if (!existsSync(dst)) { console.log(`[FAIL] 복사본 없음: ${show(dst)}`); failed = true; continue }
    const same = normalize(src) === normalize(dst)
    console.log(`[${same ? 'PASS' : 'FAIL'}] ${show(dst)} ${same ? '= ' : '≠ '}${show(src)}`)
    if (!same) failed = true
  }
  console.log(failed ? '디자인 시스템 복사본 불일치' : '디자인 시스템 복사본 동기화됨')
  process.exit(failed ? 1 : 0)
}

function copy() {
  for (const [src, dst] of PAIRS) {
    if (!existsSync(src)) { console.error(`[실패] 원본 없음: ${show(src)}`); process.exit(1) }
    mkdirSync(dirname(dst), { recursive: true })
    copyFileSync(src, dst)
    console.log(`복사: ${show(src)} → ${show(dst)}`)
  }
}

const cmd = { check, copy }[process.argv[2]]
if (!cmd) { console.error('사용법: node sync_styles.mjs <check|copy>'); process.exit(2) }
cmd()
