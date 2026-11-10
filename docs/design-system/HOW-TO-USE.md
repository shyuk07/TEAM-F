# 마감직전 구현 패키지

다른 LLM이나 개발자에게 이 폴더를 통째로 넘기면 됩니다.

## 파일

| 파일 | 내용 |
|---|---|
| README.md | 디자인 원칙, 색·글자·간격 규칙, 컴포넌트 목록 (먼저 읽기) |
| tokens.json / tokens.css | 토큰 값(라이트·다크) / 같은 값을 CSS 변수로 |
| components/bundle.css | 컴포넌트 클래스 전부 (tokens.css 다음에 불러오기) |
| components/<이름>/README.md, preview.html | 컴포넌트 규칙과 마크업 예시 (19종) |
| layout.md | 역할별 셸, 720px 반응형 기준, 화면 골격, 화면 연결 지도 |
| content.md | 말투, 버튼·오류 문구, 숫자·시간 표기 |
| states.md | 상태 enum ↔ 한국어 문구, 화면에서 계산하는 값 |
| screens.md / screens.json | 37개 화면 명세 (사람용 / 기계용) |
| api-map.md | 화면별 엔드포인트 |
| open-issues.md | 아직 정해지지 않은 항목과 임시 동작 |
| wireframe.html | 원본 와이어프레임 (브라우저로 열어 모양 확인) |

## LLM에 줄 때 프롬프트 예시

> 첨부한 마감직전 디자인 시스템으로 [화면 ID, 예: C1·C2·C3]를 구현해 줘. README.md → layout.md → screens.md의 해당 화면 순서로 읽고, 색·간격은 tokens.css 변수만, 컴포넌트는 components/bundle.css 클래스와 각 README 규칙만 써. 문구는 screens.md에 있는 그대로 쓰고, open-issues.md에 있는 항목은 적힌 임시 동작으로 구현해. 새 색·새 컴포넌트를 만들지 마.

## 주의

- 다크 테마의 accent 버튼 글자(on-accent #ffffff on #ff8a50)는 대비 2.3:1로 기준 미달입니다. 값을 정한 뒤 tokens.json과 tokens.css를 같이 바꾸세요.
- tokens.css와 screens.*는 생성 파일입니다. 고칠 때는 tokens.json과 원본 와이어프레임을 기준으로 하세요.
