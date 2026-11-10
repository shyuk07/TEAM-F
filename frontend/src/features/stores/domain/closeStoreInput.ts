// D-8: NFC 정규화 후 완전 일치. 앞뒤 공백 정리는 하지 않는다.
export function canSubmitClose(typed: string, storeName: string): boolean {
  if (storeName === '') return false;
  return typed.normalize('NFC') === storeName.normalize('NFC');
}
