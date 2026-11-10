import { Container } from '@/shared/lib/di';

// TODO: 영역 wiring이 없어 빈 배열이다. 영역을 만들 때 wire<영역>() 한 줄을 추가한다.
//   왜: features 영역이 아직 없다 (docs/design/frontend/app-shell.md D-5)
//   언제: auth 구현 시
export function createContainer(): Container {
  return new Container([]);
}
