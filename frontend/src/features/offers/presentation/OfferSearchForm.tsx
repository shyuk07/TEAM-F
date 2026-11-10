import { useState, type FormEvent } from 'react';
import { KEYWORD_MAX_LENGTH } from '../domain/search';

export type OfferSearchFormProps = {
  keyword: string | undefined;
  onSubmit: (raw: string) => void;
};

export function OfferSearchForm({ keyword, onSubmit }: OfferSearchFormProps) {
  const [value, setValue] = useState(keyword ?? '');
  // 부모 keyword가 바뀌면(「검색어 지우기」 포함) 입력값을 맞춘다. 렌더 중 이전 prop과 비교해 조정한다(요소를 다시 만들지 않아 포커스가 유지됨).
  const [prevKeyword, setPrevKeyword] = useState(keyword);
  if (keyword !== prevKeyword) {
    setPrevKeyword(keyword);
    setValue(keyword ?? '');
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    onSubmit(value);
  }

  return (
    <form role="search" onSubmit={handleSubmit}>
      <input
        className="in"
        type="search"
        placeholder="상품명 검색"
        aria-label="상품명 검색"
        maxLength={KEYWORD_MAX_LENGTH}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
    </form>
  );
}
