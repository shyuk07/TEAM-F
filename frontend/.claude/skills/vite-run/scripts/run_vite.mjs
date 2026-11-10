#!/usr/bin/env node
// 마감 직전 프론트엔드 Vite 서버 실행 래퍼 (Windows·macOS·Linux 공통, Node만 필요)
//   node run_vite.mjs dev       vite 개발 서버를 백그라운드로 띄우고 응답할 때까지 대기
//   node run_vite.mjs preview   vite preview를 백그라운드로 띄움 (dist/ 필요)
//   node run_vite.mjs check     첫 화면·SPA 라우트·백엔드·proxy 확인 (실패 시 종료코드 1)
//   node run_vite.mjs stop      상태 파일에 기록된 서버(와 자식 프로세스)만 종료
//   node run_vite.mjs status    실행 여부 확인
// 옵션: --port <번호>(dev 5173, preview 4173) --state-dir <폴더>(기본 OS 임시 폴더/lastcall-vite)
//       --backend <URL>(기본 http://localhost:8001) --wait <초>(기본 30)
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, openSync, closeSync, readFileSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..')
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    port: { type: 'string' },
    'state-dir': { type: 'string' },
    backend: { type: 'string' },
    wait: { type: 'string' },
  },
})
const STATE_DIR = resolve(values['state-dir'] ?? join(tmpdir(), 'lastcall-vite'))
const STATE_FILE = join(STATE_DIR, 'vite.json')
const BACKEND = (values.backend ?? 'http://localhost:8001').replace(/\/$/, '')
const WAIT_SECONDS = Number(values.wait ?? 30)
const DEFAULT_PORT = { dev: 5173, preview: 4173 }
const IS_WIN = process.platform === 'win32'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const fail = (msg) => { console.error(`[실패] ${msg}`); process.exit(1) }

function readState() {
  try { return JSON.parse(readFileSync(STATE_FILE, 'utf8')) } catch { return null }
}

function isAlive(pid) {
  try { process.kill(pid, 0); return true } catch (e) { return e.code === 'EPERM' }
}

async function get(url) {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(5000), redirect: 'manual' })
    return { status: res.status, type: res.headers.get('content-type') ?? '', text: await res.text() }
  } catch {
    return null
  }
}

function tail(file, lines = 20) {
  try { return readFileSync(file, 'utf8').split(/\r?\n/).slice(-lines).join('\n') } catch { return '(로그 없음)' }
}

function killTree(pid, force) {
  if (IS_WIN) {
    // /T: 자식 프로세스까지, /F: 강제. Windows는 정상 종료 신호가 없어 처음부터 /F를 쓴다.
    spawnSync('taskkill', ['/pid', String(pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true })
    return
  }
  // detached로 띄웠으므로 pid가 곧 프로세스 그룹 ID다. 음수 pid로 그룹 전체에 보낸다.
  try { process.kill(-pid, force ? 'SIGKILL' : 'SIGTERM') } catch { /* 이미 종료 */ }
}

async function start(mode) {
  const state = readState()
  if (state && isAlive(state.pid)) {
    console.log(`이미 실행 중입니다 (PID ${state.pid}, ${state.mode} ${state.port})`)
    return
  }
  const port = Number(values.port ?? DEFAULT_PORT[mode])
  const base = `http://127.0.0.1:${port}`
  if (await get(`${base}/`)) fail(`포트 ${port}를 다른 프로세스가 쓰고 있습니다. --port로 바꾸세요.`)

  const viteBin = join(ROOT, 'node_modules', 'vite', 'bin', 'vite.js')
  if (!existsSync(viteBin)) fail('node_modules/vite가 없습니다. npm install을 먼저 실행하세요.')
  if (mode === 'preview' && !existsSync(join(ROOT, 'dist'))) fail('dist/가 없습니다. npm run build를 먼저 실행하세요.')

  mkdirSync(STATE_DIR, { recursive: true })
  const log = join(STATE_DIR, `vite-${mode}-${port}.log`)
  const fd = openSync(log, 'w')
  const args = [viteBin, ...(mode === 'preview' ? ['preview'] : []), '--port', String(port), '--strictPort', '--host', '127.0.0.1']
  // npm·셸을 거치지 않고 node로 vite를 직접 띄운다. 셸 차이가 없고 PID가 vite 자신이다.
  const child = spawn(process.execPath, args, { cwd: ROOT, detached: true, stdio: ['ignore', fd, fd], windowsHide: true })
  child.unref()
  closeSync(fd)
  writeFileSync(STATE_FILE, JSON.stringify({ pid: child.pid, mode, port, log }, null, 2))

  for (let i = 0; i < WAIT_SECONDS; i++) {
    await sleep(1000)
    if (await get(`${base}/`)) {
      console.log(`${mode} 서버 준비 완료: ${base} (PID ${child.pid}, 로그 ${log})`)
      return
    }
    if (!isAlive(child.pid)) break
  }
  console.error(`[실패] ${mode} 서버가 ${WAIT_SECONDS}초 안에 응답하지 않습니다. 로그:\n${tail(log)}`)
  await stop()
  process.exit(1)
}

async function stop() {
  const state = readState()
  if (!state || !isAlive(state.pid)) {
    console.log('실행 중인 서버가 없습니다.')
    rmSync(STATE_FILE, { force: true })
    return
  }
  killTree(state.pid, false)
  for (let i = 0; i < 10 && isAlive(state.pid); i++) await sleep(1000)
  if (isAlive(state.pid)) killTree(state.pid, true)
  rmSync(STATE_FILE, { force: true })
  console.log(`서버를 종료했습니다 (PID ${state.pid}).`)
}

function status() {
  const state = readState()
  if (state && isAlive(state.pid)) console.log(`실행 중: ${state.mode} ${state.port} (PID ${state.pid}, 로그 ${state.log})`)
  else console.log('실행 중이 아닙니다.')
}

async function check() {
  const state = readState()
  const mode = state?.mode ?? 'dev'
  const port = Number(values.port ?? state?.port ?? DEFAULT_PORT[mode])
  const base = `http://127.0.0.1:${port}`
  let failed = false
  const result = (ok, msg) => { console.log(`[${ok ? 'PASS' : 'FAIL'}] ${msg}`); if (!ok) failed = true }

  const root = await get(`${base}/`)
  result(root?.status === 200 && root.text.includes('id="root"'), `첫 화면 ${base}/ (200 + <div id="root">)`)

  const spa = await get(`${base}/__spa_check__/1`)
  result(spa?.status === 200 && spa.text.includes('id="root"'), 'SPA 라우트 fallback (없는 경로도 index.html)')

  const backend = await get(`${BACKEND}/docs`)
  if (backend?.status === 200) {
    console.log(`[PASS] 백엔드 응답 ${BACKEND}`)
    if (mode === 'dev') {
      const proxied = await get(`${base}/v1/offers`)
      result(/json/i.test(proxied?.type ?? ''), `proxy /v1 → ${BACKEND} (Content-Type: ${proxied?.type || '응답 없음'})`)
    } else {
      console.log('[SKIP] proxy (preview 모드는 VITE_API_BASE_URL로 직접 호출)')
    }
  } else {
    console.log(`[SKIP] 백엔드 꺼짐 (${BACKEND}). proxy 확인은 통과가 아닙니다. ../backend/README.md로 백엔드를 띄우세요.`)
  }
  process.exit(failed ? 1 : 0)
}

const commands = { dev: () => start('dev'), preview: () => start('preview'), stop, status, check }
const run = commands[positionals[0]]
if (!run) {
  console.error('사용법: node run_vite.mjs <dev|preview|check|stop|status> [--port N] [--state-dir 폴더] [--backend URL] [--wait 초]')
  process.exit(2)
}
await run()
