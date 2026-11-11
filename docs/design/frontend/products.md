# products 영역 설계안 (O4 매장·상품 · O6 상품 등록 · O11 상품 수정·숨기기 · O12 상품 사진)

- 대상 slice: `features/products`, `entities/product`, `pages/owner-store`(O4), `pages/product-new`(O6), `pages/product-edit`(O11), `widgets/owner-nav`(계정 행 1개 추가), `shared`(multipart 지원·`Skeleton`·`EmptyState`·경로), `app`(라우트 3줄 교체·`wireProducts()` 1줄)
- 대응 화면: 상점주 O4, O6, O11, O12(라우트 없는 사진 시트·부품). O3 할인 등록, O7 폐점(구현됨, O4에서 링크만), O8 계정 메뉴(구현됨)는 범위 밖.
- 상태: **설계안 5차(2026-11-11, 사용자 결정 3건 확정, 출처 "사용자")**. 바뀐 결정: D-19(O4 계정 행은 **모바일 전용**, `.mob`), 새 D-37(O6 데스크톱 「등록만」), 새 D-38(360px 하단 CTA 줄바꿈), Q-4 재결정, N-9 폐기, 새 C-15·C-16. 공개 API 변경: `features/products`·`entities`·`widgets` 없음. `shared/ui/Button`에 선택 prop `style?: CSSProperties` 추가(D-38, 사용자 확정·승인, 기존 호출 영향 없음). D-37·D-38은 5차 보완에서 모두 확정. `OwnerAccountRows`의 `.mob` 래핑과 그 테스트는 **frontend-e9 세션이 수행**한다. 아래 4차 기준 본문 중 5차와 부딪치는 곳은 5차로 고쳤다. 4차 기준: **(2026-11-11, 구현·리뷰 뒤 사용자 결정 A1·A2·A3·B1·B2·C1·C2·D1 모두 확정, 출처 "사용자")**. 바뀐 결정: D-11, D-16, D-17, D-24, D-26, D-30, D-31, 새 D-33~D-36, 새 C-13·C-14. 공개 API 변경: `features/products`에 `ProductLoadError`·타입 `ProductLoadFailure` 추가, `useProduct` 반환에 `failure` 추가, `useCreateProduct`에서 `cancel` 제거, `PhotoField`에서 `onCancel` 제거(§4.2, §4.4, §4.5). `npm run format:check` 기존 74건은 이번 범위 밖(D1, 별도 정리). 아래 "3차" 기준 내용 중 4차와 부딪치는 것은 이 4차 기준으로 본문을 고쳤다. 3차 기준:(2026-11-11 사용자 결정: B-1 사유를 "사용자 결정으로 이번 차수 제외"로 변경, 명세 보강 `e3abeae` 반영. 공개 API·시그니처 변경 없음). 2차 기준:(2026-11-11 사용자 결정 반영). D-1~D-7, D-9, D-11, D-14~D-19, D-23은 사용자 확정(D-4·D-16의 문구는 임시 문구 적용 승인이며 최종 문구는 미확정). 나머지(D-8, D-10, D-12·D-13, D-20~D-22, D-24~D-26)는 설계자 "임시". D-27·D-28은 이번 차수에 새로 정한 "임시". 질문 Q-1~Q-11은 모두 해소(§12.3).
- **구현 차단 범위(B-1)**: O11 「사진 바꾸기」「사진 삭제」는 사용자 결정으로 이번 차수에서 제외하고 다음 차수에 재설계한다(이번 차수 O11 사진은 보기만, §0.1). O6 등록(사진 포함)·O4·O11의 사진 외 수정·숨기기·다시 보이기는 진행한다. 이 문서에서 해당 부분은 `[차단 B-1]`로 표시했고, 그 표시가 있는 파일·함수·테스트는 만들지 않는다.
- 정본: `../../design-system/screens.md` O4(391~409줄)·O6(423~436줄)·O11(482~497줄)·O12(499~517줄), `layout.md` 49~70줄, `api-map.md` 31·33·37·38줄, `states.md`(상품 노출/숨김, 로딩·빈 상태 62~63줄), `content.md`, `open-issues.md` O11·O12(16~17줄), `wireframe.html` O4(668~690줄)·O6(706~728줄)·O11(788~814줄)·O12(816~830줄), `../../reference/catalog.md` §1·§2·§4·§5·§6·§6-1·§15~§17, 백엔드 `router.py`·`schemas.py`·`service.py`·`exceptions.py`.
- 재사용: `features/stores`·`entities/store`(`useOwnerStore().id`, `storeStatusLabel/Tone`), `shared/lib/useAsync`·`errorInfo`·`format.groupDigits`·`routes`, `shared/ui`(`AppBar`·`Box`·`Button`·`CtaBar`·`FieldError`·`Input`·`Notice`·`StatusTag`), `shared/ui/Overlay`(시트), `widgets/owner-nav`(`OwnerTopNav`·`OwnerAccountButton`), `features/auth`(`LogoutConfirmSheet`), 기존 `shared/api/client.ts`의 401 알림(`authFailure.ts`)·`app/providers/AuthFailureBridge`.

## 0. 백엔드 실재 확인 (`frontend-orchestration.md` §6)

| 항목 | 확인 위치 | 결과 |
| --- | --- | --- |
| `POST /v1/stores/{id}/products` multipart: 폼 `name`·`category`·`description`·`original_price`·`file`(0~1), 빈 `category`·`description`은 없음으로 본다, `file` 2개 이상은 400 | `catalog/presentation/router.py:114~139`, `reference/catalog.md` §1 | 명세와 같다. `file`이 문자열이거나 2개 이상이면 `VALIDATION_ERROR`(`file: 사진은 1장만 보낼 수 있습니다`) |
| 오류 코드 `IMAGE_TOO_LARGE`·`UNSUPPORTED_IMAGE_TYPE`·`STORE_CLOSED`·`STORE_SUSPENDED`·`STORE_NOT_APPROVED`·`VALIDATION_ERROR`·`HTTP_ERROR` | `domain/exceptions.py:32~37·89~92·182~190`, `error_handlers.py:65~67`(`ValueError` → 400 + `error_code` 속성, 없으면 `VALIDATION_ERROR`) | 명세 §1과 같다 |
| `GET /v1/stores/{id}/products` `is_active` 미지정 = 본인 상점이면 노출·숨김 모두, 응답 `{items,page,size,total}` | `service.py:440~457`, `schemas.py:56~78`, `reference/catalog.md` §2 | 명세와 같다(D-2) |
| `GET /v1/products/{id}`는 숨김 상품도 **본인 상점이면** 준다 | `service.py:459~465` | 명세 §4가 `e3abeae`에서 "숨김 상품은 상점주 본인에게만, 그 외 404"로 보강되어 코드와 같다(C-8 해소) |
| `POST /v1/products/{id}/deactivate` 진행 중 할인이 있으면 400 `PRODUCT_HAS_OPEN_OFFER`, 이미 숨김이면 400 `PRODUCT_ALREADY_INACTIVE` | `domain/product.py:171`, `exceptions.py:48~57`, `service.py:288~297` | 명세 §5·§6·§6-1 에러 표에 `error_code` 열이 `e3abeae`에서 추가되어 코드와 같다(C-3 해소). 숨기기 거절은 `errorCode`로 판정 |
| `POST /v1/products/{id}/activate` 오류 `STORE_CLOSED`·`PRODUCT_ALREADY_ACTIVE` | `reference/catalog.md` §6-1 | 명세만 확인(백엔드 코드 `exceptions.py:52~54`에 `PRODUCT_ALREADY_ACTIVE` 있음) |
| `PATCH /v1/products/{id}`: 보낸 필드만 반영. `category: null`이면 비움(`_validate_category`가 `None` 통과). `product_image`는 **현재 목록에 있는 업로드 주소만 유지·제거**할 수 있고 새 업로드 주소는 못 넣는다. 목록에서 빠진 업로드 이미지는 같은 트랜잭션에서 파일도 지운다. 정상 가격이 진행 중 할인가 이하이면 400 `VALIDATION_ERROR`("정상 가격은 진행 중인 할인 가격보다 커야 합니다.") | `domain/product.py:103~141`, `service.py:240~254` | 명세 §5가 `e3abeae`에서 `category`·`description` null = 비우기, `error_code` 열을 적어 코드와 같다(C-3, C-5 해소). 사진 삭제는 `PATCH`로도 된다(C-2) |
| `POST /v1/products/{id}/images` 201, 응답 `{id, product_id, url, content_type, size_bytes, product_image[]}`, 새 주소는 목록 **끝**에 붙는다 | `service.py:256~268`, `reference/catalog.md` §15 | 명세와 같다 |
| 이미지 주소는 상대 경로(`/v1/products/{pid}/images/{iid}`), 조회는 공개(`<img src>`에 서버 주소를 붙여 씀) | `reference/catalog.md` §15·§17 | 배포 빌드에서는 `API_BASE_URL`을 앞에 붙여야 한다(D-24) |
| 401 `UNAUTHORIZED`·`TOKEN_REVOKED` → 세션 정리 | `shared/api/client.ts:35~44`, `app/providers/AuthFailureBridge.tsx`, `App.tsx:14` | **이미 구현되어 있다**. `useAuthController.ts:13` FIXME는 낡았다(C-7, D-21) |

## 0.1 B-1 — 상품 사진 바꾸기·삭제 이번 차수 제외 (O11)

- 경위: 사진 보존(주문 당시 사진 유지)을 위한 백엔드 변경 요청을 사용자가 **취소**했다. 커밋 `e3abeae`가 `../catalog.md` 17절 머리(l.1703~1709, "사진 보존 철회, 현행 D97·Q49 유지")와 `../reservations.md` 17절 머리(l.1174~1178, "예약 시점 상품 사진 기록 철회")에 철회로 기록했다. 현재 백엔드는 그대로 PATCH에서 목록에서 빠진 업로드 사진의 바이트를 지우고(`../../../backend/src/catalog/application/service.py:251-252`, 백엔드 D97) DELETE도 지운다(`service.py:270-278`).
- 사용자 결정(2026-11-11, 확정): **O11 사진은 이번 차수에서 보기만 한다.** 「사진 바꾸기」「사진 삭제」는 다음 차수로 미룬다. 더 이상 "백엔드 변경 대기"가 아니다.
- 풀리는 조건: 다음 차수에 사진 교체 방식을 다시 정한다(현행 백엔드 동작 = 교체·삭제하면 이전 파일이 지워지는 것을 받아들일지). 이전 사진 보존 요구가 철회된 상태로 유지되는지 다음 차수에 다시 정하는지는 확인 필요(Q-12). 그때 D-12·D-13을 재설계하고 이 문서를 고친다.
- 이번 차수에 만들지 않는 것(`[차단 B-1]` 표시 유지):

| 계층 | 파일 · 심볼 | 이번 차수 |
| --- | --- | --- |
| domain | `productPhoto.ts`의 `PhotoEdit`, `planProductImages` | 만들지 않는다. (`validatePhoto`·`photoSlotPhase`·상수는 O6용이라 만든다) |
| domain | `productChanges.ts`의 `productImage` 필드 | 만들지 않는다 |
| domain | `productCommands.ts`의 `uploadPhoto`, `deleteUploadedPhoto` | 포트에 넣지 않는다 |
| application | `saveProduct`의 `photo` 입력과 1~4단계 사진 처리 | 없다(§4.2) |
| application | `usePhotoDraft`의 `initial`·`remove`·`removed`·`edit` | 없다. O6용 `{file, previewSrc, error, pick, clear}`만 |
| infrastructure | `HttpProductCommands.uploadPhoto`·`deleteUploadedPhoto`, `ImageUploadDto` | 만들지 않는다 |
| presentation | `ProductEditForm`의 `PhotoField` 사용(바꾸기·삭제) | 만들지 않는다. 사진이 있으면 읽기 전용 미리보기만(D-28) |
| 테스트 | §9에서 `[차단 B-1]`로 표시한 항목 전부 | 쓰지 않는다 |

- 차단되지 않는 것: O6 등록(사진 0~1장 multipart, `IMAGE_TOO_LARGE`·`UNSUPPORTED_IMAGE_TYPE` 처리), O11의 이름·가격·카테고리·설명 수정, 숨기기·다시 보이기, O4 목록.
- 남길 주석: N-10(FIXME, `ProductEditForm`).

## 1. slice 목록과 계층

| 계층 | slice | 대응 화면 | 안에 두는 계층 |
| --- | --- | --- | --- |
| `shared` | `api`(`client.ts` multipart 지원), `ui`(`Skeleton`·`EmptyState` 추가), `lib`(`routes` 1개 추가) | 전 화면 | (4계층 없음, F3) |
| `entities` | `product` | O4·O6·O11 + 재사용처(§1.1) | domain, application(토큰만). presentation·infrastructure 없음(F18) |
| `features` | `products` | O4·O6·O11·O12 | domain, application, infrastructure, presentation, `wiring.ts` |
| `widgets` | `owner-nav`(기존, 변경) | O4 | presentation(`OwnerAccountRows` 추가) |
| `pages` | `owner-store` | O4 | presentation |
| `pages` | `product-new` | O6 | presentation |
| `pages` | `product-edit` | O11 | presentation |
| `app` | `router/routes.tsx`, `router/placeholders.tsx`, `container.ts` | | (4계층 없음) |

의존 방향: `pages → features(products)·entities(product·store)·widgets`, `widgets/owner-nav → features/auth`(`OwnerAccountRows`가 `@/features/auth`의 `LogoutConfirmSheet`를 import. widgets는 features 위 계층이라 F1 허용), `app → pages·features`. `features/products`는 `features/auth`·`features/stores`·`features/offers`를 import하지 않는다(F1). 상점 ID는 페이지가 `useOwnerStore()`(entities/store)에서 읽어 훅에 인자로 넘긴다. O12(시트)는 라우트가 없고 O6·O11 안의 부품이다(`PhotoField`·`PhotoPickSheet`).

### 1.1 `entities/product`를 두는 이유와 재사용처 (D-7)

`entities/product`에는 **영역 두 곳 이상이 읽는 것**만 둔다: `Product` 타입·순수 규칙, 읽기 포트 `ProductRepository`, 토큰. 구현체는 상품을 소유한 `features/products/infrastructure`가 만든다.

| 재사용처 | 쓰는 것 | 상태 |
| --- | --- | --- |
| O3 할인 등록(`features/offers`, 다음 차수) | `ProductRepositoryToken`으로 `findById`(정가·상품명·사진으로 폼 채움), `Product`·`formatProductPrice` | 설계 예정. 이번에는 이동만(D-9) |
| O2 할인 관리·O9 | 상품명·정가·사진 표시 | 예정 |
| C1·C2 고객 할인 카드·상세 | 상품 사진(`images`)·상품명 | 예정. 지금 `OfferCard`는 사진 자리만 둔다(`features/offers/presentation/OfferCard.tsx:7` TODO) |
| `features/offers` 안의 상품 정보 복제 | `Offer.productName`·`originalPrice`·`productId`(`features/offers/domain/offer.ts:6~13`)와 `formatWon`(`offerFormat.ts`)이 상품 정보를 따로 갖는다 | 이번 구현에서 **TODO만 남긴다**(§10 N-3). 합치기는 offers 차수에서 결정 |

## 2. 공용 기반 변경 (`shared`) — 쓰기 소유: shared 담당 `fe-developer`

### 2.1 `shared/api/client.ts` multipart 지원 (D-20)

- `Options.body`가 `FormData`이면 `JSON.stringify`하지 않고 그대로 보낸다. 이때 `Content-Type`을 **지정하지 않는다**(브라우저가 경계 문자열을 붙인다). 그 밖의 `body`는 지금과 같다. 토큰·401 알림·`AbortSignal`·`NETWORK_ERROR` 동작은 그대로다. 새 export는 만들지 않는다(`request`만 쓴다).
- `PATCH`·`DELETE`는 `request(path, { method })`로 부른다. `apiPatch` 등 새 함수를 만들지 않는다.

### 2.2 `shared/ui` 추가 (D-20)

`bundle.css` 클래스만 쓴다(F12). 파일 하나에 컴포넌트 하나, `shared/ui/index.ts`에서 내보낸다.

| 컴포넌트 | props | 렌더 |
| --- | --- | --- |
| `Skeleton` | 없음 | 카드 뼈대 한 개: `<div className="card">` 안에 썸네일 칸 1개와 줄 3개(`.sk`). `components/Skeleton/preview.html`과 같은 마크업, `aria-hidden="true"` |
| `EmptyState` | `title: string`, `description?: string`, `action?: ReactNode` | `<div className="box empty"><div className="ic"/><b>{title}</b><span className="m">{description}</span>{action}</div>` (`components/EmptyState/preview.html`) |

**5차(D-38) 변경:** `shared/ui/Button`에 선택 prop `className?: string`을 추가한다(기본 클래스 뒤에 덧붙임, 기존 호출은 그대로). 테스트는 §9.1.

만들지 않는 것: `ListRow`(`.li` 클래스를 O4 행에서 직접 씀), `PhotoSlot`·`BottomSheet`(products 전용이라 `features/products/presentation`), `Chip`(O11에서 한 곳, 클래스 직접), `SplitLayout`(`.split` 클래스, stores.md C-7과 같음).

### 2.3 `shared/lib/routes.ts`

`ROUTES.ownerOfferNewFor(productId: string): string` = `` `/owner/offers/new?productId=${encodeURIComponent(productId)}` `` 추가(D-9). 기존 `ownerOfferNew`는 그대로.

## 3. `entities/product`

### 3.1 domain

`domain/product.ts`
```ts
export type ProductImage = {
  url: string   // 서버가 준 원본 주소. 저장(PATCH)할 때 그대로 되돌려 보낸다
  src: string   // <img src>용. 상대 경로면 API_BASE_URL을 붙인 주소 (infrastructure가 계산, D-24)
}
export type Product = {
  id: string
  storeId: string
  name: string
  category: string | null
  description: string | null
  originalPrice: number
  isActive: boolean
  images: ProductImage[]
}
export type ProductPage = { items: Product[]; page: number; size: number; total: number }

export function productStatusLabel(p: Product): '노출' | '숨김'          // states.md 상품
export function productStatusTone(p: Product): 'ok' | 'mute'            // 노출 ok / 숨김 mute
export function formatProductPrice(price: number): string               // 12000 → '12,000원' (content.md 금액, groupDigits 사용)
export function productSubtitle(p: Product): string                     // category 있으면 '빵 · 12,000원', 없으면 '12,000원'
export function primaryImage(p: Product): ProductImage | null           // images[0] ?? null
export function uploadedImageId(productId: string, url: string): string | null
   // '/v1/products/{productId}/images/{id}' 형태이면 id, 아니면(외부 URL·다른 상품) null
```

`domain/productRepository.ts` — 읽기 포트(domain 포트)
```ts
export interface ProductRepository {
  /** GET /v1/stores/{storeId}/products?page=1&size=100 (is_active 미지정 → 본인 상점이면 노출·숨김 모두, D-2) */
  findByStore(storeId: string, signal?: AbortSignal): Promise<ProductPage>
  /** GET /v1/products/{id}. 404·403은 ApiError로 던진다 */
  findById(productId: string, signal?: AbortSignal): Promise<Product>
}
```

### 3.2 application
`application/tokens.ts`: `ProductRepositoryToken = createToken<ProductRepository>('ProductRepository')`.

### 3.3 공개 API (`index.ts`)
```ts
export type { Product, ProductImage, ProductPage } from './domain/product'
export { productStatusLabel, productStatusTone, formatProductPrice, productSubtitle, primaryImage, uploadedImageId } from './domain/product'
export type { ProductRepository } from './domain/productRepository'
export { ProductRepositoryToken } from './application/tokens'
```

## 4. `features/products`

### 4.1 domain

`domain/productForm.ts` — 입력 검증(F7)
```ts
export type ProductFormInput = { name: string; price: string; category: string; description: string }   // 화면 입력(문자열)
export type ProductFormValue = {
  name: string                     // 앞뒤 공백 제거
  originalPrice: number            // 정수
  category: string | null          // 공백 제거 후 빈 값이면 null
  description: string | null       // 공백 제거 후 빈 값이면 null
}
export type ProductFormField = 'name' | 'price' | 'category'
export type ProductFormResult =
  | { ok: true; value: ProductFormValue }
  | { ok: false; errors: Partial<Record<ProductFormField, string>> }
export const NAME_MAX = 200, CATEGORY_MAX = 80, PRICE_MAX = 99_999_999
export function parsePrice(input: string): number | null   // 쉼표·앞뒤 공백 제거 후 숫자만이면 정수, 아니면 null
export function validateProductForm(input: ProductFormInput): ProductFormResult
export function productFormFromProduct(p: Product): ProductFormInput  // price는 숫자 문자열(쉼표 없음), null은 ''
```
규칙: 상품명 trim 후 1~200자 / 정상 가격 1 이상 99,999,999 이하 정수(`'12,000'` 허용) / 카테고리 trim 후 비면 `null`, 있으면 80자 이하 / 설명은 trim 후 비면 `null`. 오류 문구는 `productMessages.ts`(D-16, 임시).

`domain/productChanges.ts` — 수정 요청 만들기
```ts
export type ProductChanges = {
  name?: string
  originalPrice?: number
  category?: string | null     // null은 "비우기"일 때만 (D-18). 바뀌지 않았으면 키 자체가 없다
  description?: string | null  // 같음
  // productImage?: string[]   [차단 B-1] 사진 변경은 백엔드 반영 후 재설계(D-12)
}
export function diffProduct(original: Product, value: ProductFormValue): ProductChanges   // 달라진 필드만. 같으면 {}. null은 원래 값이 있었는데 비운 경우에만
export function hasChanges(c: ProductChanges): boolean                                    // 키가 하나라도 있으면 true
```

`domain/productPhoto.ts` — 사진 규칙(O12)
```ts
export const PHOTO_MAX_BYTES = 5 * 1024 * 1024          // 5,242,880
export const PHOTO_ACCEPT = ['image/jpeg', 'image/png', 'image/webp'] as const
export type PhotoMeta = { type: string; size: number }   // File을 받지 않는다(순수)
export type PhotoErrorCode = 'UNSUPPORTED_TYPE' | 'TOO_LARGE' | 'EMPTY'
export function validatePhoto(meta: PhotoMeta): PhotoErrorCode | null   // 0바이트 'EMPTY', 형식 밖 'UNSUPPORTED_TYPE', 5MiB 초과 'TOO_LARGE' (검사 순서 EMPTY → TYPE → SIZE)
// [차단 B-1] export type PhotoEdit = { kind: 'keep' } | { kind: 'remove' } | { kind: 'replace'; file: Blob }
export type PhotoSlotPhase = 'empty' | 'filled' | 'uploading' | 'failed'
export function photoSlotPhase(i: { hasImage: boolean; uploading: boolean; error: string | null }): PhotoSlotPhase
   // 4차(B2): error !== null → failed, (uploading && hasImage) → uploading, hasImage → filled, 그 외 empty
   // 사진이 없으면 uploading이 켜져도 empty(사진 없이 등록하면 사진 칸은 그대로, D-11)
// [차단 B-1] planProductImages(original, edit, uploaded): string[] | undefined
//   keep → undefined / remove → 첫 사진을 뺀 url 목록 / replace → uploaded에서 original 첫 사진을 뺀 목록
//   백엔드가 사진을 보존하는 방식으로 바뀐 뒤 재설계한다(D-12). 화면은 첫 사진 1장만 다룬다는 규칙(D-6)은 유지
```

`domain/productCommands.ts` — 쓰기 포트(domain 포트, 이 영역만 씀)
```ts
export type NewProduct = { name: string; originalPrice: number; category: string | null; description: string | null }
export interface ProductCommands {
  /** POST /v1/stores/{storeId}/products (multipart, photo 있으면 file 포함). 사진과 상품은 한 요청, 둘 다 성공하거나 둘 다 안 만들어진다 (D-1) */
  create(storeId: string, input: NewProduct, photo: Blob | null, signal?: AbortSignal): Promise<Product>
  /** PATCH /v1/products/{id}. changes의 키만 보낸다. null은 category·description을 비울 때만 나간다(D-18) */
  update(productId: string, changes: ProductChanges, signal?: AbortSignal): Promise<Product>
  /** POST /v1/products/{id}/deactivate */
  deactivate(productId: string, signal?: AbortSignal): Promise<Product>
  /** POST /v1/products/{id}/activate */
  activate(productId: string, signal?: AbortSignal): Promise<Product>
  // [차단 B-1] uploadPhoto(POST …/images), deleteUploadedPhoto(DELETE …/images/{id}) — D-12·D-13 재설계 후 추가
}
```

`domain/productToggle.ts` — 숨기기·다시 보이기 결과 판정(B1, D-33, F7)
```ts
/** 서버가 "이미 원하는 상태"라고 답한 오류 코드면 그 상태의 Product, 아니면 null.
 *  PRODUCT_ALREADY_INACTIVE → { ...product, isActive: false }, PRODUCT_ALREADY_ACTIVE → { ...product, isActive: true }. 다른 필드는 그대로 */
export function productWhenAlready(product: Product, errorCode: string): Product | null
```

`domain/productMessages.ts` — 문구(F13). 정본이 있는 것은 출처를 적고, 나머지는 **임시**(D-16). **이 파일의 `PRODUCT_TEXT`·`PRODUCT_ERROR_TEXT`·`productErrorMessage`는 `features/products` 밖으로 내보내지 않는다**(공개 API 아님, D-35). 다른 slice·pages가 상품 문구를 쓰려면 이 영역의 공개 컴포넌트·훅이 문구를 가져온다.
```ts
export function productErrorMessage(e: { status: number; errorCode: string; message: string }, ctx: 'create' | 'save' | 'toggle' | 'load'): string
export type ProductLoadFailure = { kind: 'notFound' | 'loadFailed'; message: string }   // C1, D-35
export function productLoadFailure(e: { status: number; errorCode: string; message: string }): ProductLoadFailure
   // status 404 또는 403 → { kind:'notFound', message: PRODUCT_ERROR_TEXT.notFound }
   // 그 밖 → { kind:'loadFailed', message: productErrorMessage(e, 'load') }  (NETWORK_ERROR는 그 message, 나머지는 불러오기 실패 문구)
```

| 조건 | 문구 | 출처 |
| --- | --- | --- |
| `IMAGE_TOO_LARGE` 또는 사진 `TOO_LARGE` | 「사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.」 | **정본** screens.md O12 |
| `UNSUPPORTED_IMAGE_TYPE` 또는 사진 `UNSUPPORTED_TYPE`·`EMPTY` | 「JPG, PNG, WebP 사진만 올릴 수 있어요.」 | 임시(O12 「JPG·PNG·WebP, 5MB 이하 (임시값)」) |
| `PRODUCT_HAS_OPEN_OFFER` (ctx `toggle`) | 「진행 중인 할인이 있어 숨길 수 없어요. 판매를 중단한 뒤 다시 숨겨 주세요.」 | **임시**(D-4) |
| `STORE_SUSPENDED` | 「정지된 상점에서는 상품을 등록할 수 없어요.」 | 임시 |
| `STORE_CLOSED` | 「폐점한 상점에서는 상품을 다룰 수 없어요.」 | 임시 |
| `STORE_NOT_APPROVED` | 「승인되지 않은 상점에는 상품을 등록할 수 없어요.」 | 임시 |
| `VALIDATION_ERROR` (모든 ctx) | **서버 `message`를 쓰지 않는다.** 공통 문구 `PRODUCT_ERROR_TEXT.saveFailed` 「저장하지 못했어요. 잠시 후 다시 시도해 주세요.」(load는 불러오기 문구). 입력 검증은 화면(`validateProductForm`)이 먼저 하므로 서버 `VALIDATION_ERROR`는 예외 상황이고, 서버 문구는 영어 프레임워크 문구일 수 있다 | 4차 D-17(사용자 확정) |
| `NETWORK_ERROR` | 서버(`ApiError`)가 만든 문구 그대로 | `api-client` §2 |
| 그 밖 | 「저장하지 못했어요. 잠시 후 다시 시도해 주세요.」 (load는 「상품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.」) | 임시 |
| (별도 `productLoadFailure`) 404·403 | 「상품을 찾을 수 없어요.」 (`PRODUCT_ERROR_TEXT.notFound`) | 임시(D-16). 3차까지 `pages/product-edit`의 `TEXT` 상수였고 4차에 이 파일로 옮김(C1) |

`PRODUCT_ERROR_TEXT`(폼 오류·사진·상점 상태·저장·불러오기 문구, 임시)와 `photoErrorMessage(code: PhotoErrorCode): string`(`TOO_LARGE` → 5MB 문구, 그 밖 → 형식 문구)도 이 파일에 있다. Green 개발자가 추가한 것을 설계안에 기록한다. `PRODUCT_TEXT.photo.empty` 값은 「사진 추가 · 카메라 또는 앨범」이고 앞의 「+」는 `PhotoField`가 따로 그린다.

그 밖의 화면 문구 상수 `PRODUCT_TEXT`(`domain/productMessages.ts`, 값은 `as const`, 화면별 중첩 객체, D-31). 키는 영문, 값은 문구. 「{N}」이 들어가는 것은 상수가 아니라 `productCountLabel(total)`(「상품 {N}개」)이 만든다. 「(임시)」는 정본 없음(D-4·D-16).

| 그룹.키 | 값 | 정본 |
| --- | --- | --- |
| `list.add` | 「+ 상품 등록」 | wireframe O4 |
| `list.closeStore` | 「상점 폐점」 | wireframe O4 |
| `list.account` | 「계정」 | wireframe O4 |
| `list.emptyTitle` | 「아직 등록한 상품이 없어요」 | 임시 |
| `list.emptyDescription` | 「상품을 등록하면 할인을 만들 수 있어요」 | 임시 |
| `list.emptyAction` | 「상품 등록」 | EmptyState README |
| `form.pending` | 「처리 중…」 | states.md 62줄 |
| `create.nameLabel` / `priceLabel` | 「상품명 *」 / 「정상 가격 *」 | wireframe O6 |
| `create.categoryLabel` / `descriptionLabel` | 「카테고리」 / 「설명」 | wireframe O6 |
| `create.photoLabel` | 「상품 사진 (1장)」 | wireframe O6 |
| `create.photoHint` | 「고객 목록 카드와 상세 화면에 이 사진이 보여요. 없으면 기본 그림이 나와요.」 | wireframe O6 |
| `create.submitOffer` / `submitList` | 「등록하고 할인 만들기」 / 「등록만」 | wireframe O6 |
| `edit.nameLabel` / `priceLabel` / `categoryLabel` / `descriptionLabel` / `photoLabel` | 「상품명」「정상 가격」「카테고리」「설명」「상품 사진 (1장)」 | wireframe O11 |
| `edit.save` | 「저장」 | wireframe O11 |
| `edit.visibleTitle` | 「고객에게 보이기」 | wireframe O11 |
| `edit.visibleChip` | 「노출 중」 | wireframe O11 |
| `edit.hiddenChip` | 「숨김」 | 임시(D-16) |
| `edit.hide` / `edit.show` | 「숨기기」 / 「다시 보이기」 | wireframe O11 |
| `edit.toStore` | 「매장으로」 | 임시(D-16). 3차까지 page `TEXT.toStore`. `ProductLoadError`가 씀(D-35) |
| `edit.retry` | 「다시 시도」 | 임시. 3차까지 page `TEXT.retry`. `ProductLoadError`가 씀 |
| `edit.hideHint` | 「숨기면 이 상품으로 새 할인을 올릴 수 없고, 고객 목록에서 이 상품의 할인이 빠져요.」 | wireframe O11, C-4 |
| `photo.camera` / `album` | 「카메라로 찍기」 / 「앨범에서 고르기」 | wireframe O12 |
| `photo.retry` / `pickOther` / `cancel` / `remove` | 「다시 시도」「다른 사진 고르기」「취소」「삭제」 | wireframe O12 |
| `photo.sheetTitle` | 「사진 추가」 | wireframe O12 |
| `photo.sheetHint` | 「JPG·PNG·WebP, 5MB 이하」 | wireframe O12 |

사진 칸의 「+ 사진 추가 · 카메라 또는 앨범」「사진 바꾸기」「올리는 중…」「사진 삭제」(O11 링크)도 `photo.empty`·`photo.change`·`photo.uploading`·`photo.removeLink` 키로 같은 파일에 둔다(값은 §4.4 `PhotoField` 표 그대로, 출처 wireframe O6·O11·O12). 문구 값이 바뀌어도 키는 유지한다.

### 4.2 application

`application/tokens.ts`: `ProductCommandsToken = createToken<ProductCommands>('ProductCommands')`. (`ProductRepositoryToken`은 entities가 가진다.)

유스케이스(순수 함수, 포트를 인자로 받는다 — F18)

```ts
// createProduct.ts
export async function createProduct(
  deps: { commands: ProductCommands },
  input: { storeId: string; value: ProductFormValue; photo: Blob | null },
  signal?: AbortSignal,
): Promise<Product>
// commands.create(storeId, {name, originalPrice, category, description}, photo, signal) 한 번 호출. 가공 없음(사진 + 상품은 서버가 원자 처리, D-1)

// saveProduct.ts
export async function saveProduct(
  deps: { commands: ProductCommands },
  input: { original: Product; changes: ProductChanges; photo: PhotoEdit },
  signal?: AbortSignal,
): Promise<Product>
```
`saveProduct`는 이번 차수에 사진을 다루지 않는다(`[차단 B-1]`: `photo` 입력, 사진 업로드·되돌리기 단계 없음. 시그니처는 `input: { original: Product; changes: ProductChanges }`).
1. `!hasChanges(changes)`이면 `update`를 부르지 않고 `original`을 돌려준다.
2. 아니면 `await commands.update(original.id, changes, signal)`의 `Product`를 돌려준다. 실패는 그대로 던진다.
3. 요청 본문의 `null`은 `changes`에 `null`로 담긴 `category`·`description`뿐이다(D-18).

```ts
// toggleProduct.ts
export function toggleProduct(deps: { commands: ProductCommands }, product: Product, signal?: AbortSignal): Promise<Product>
// product.isActive ? commands.deactivate(id) : commands.activate(id). 확인 단계 없음(D-3)
// 4차(B1, D-33): 던진 오류를 readErrorInfo(shared/lib/errorInfo)로 읽어 productWhenAlready(product, errorCode)가
//   Product를 주면(PRODUCT_ALREADY_INACTIVE·ACTIVE) 오류로 던지지 않고 그 Product를 resolve한다(이미 원하는 상태 = 성공).
//   그 밖의 오류(PRODUCT_HAS_OPEN_OFFER, STORE_CLOSED, 네트워크 등)와 abort는 그대로 던진다.
```

내부 훅 `useProductRun.ts`(비공개, `index.ts`로 내보내지 않음, D-36): create·save·toggle 훅이 공유하는 제출 흐름.
```ts
type RunOptions = { message(info: ErrorInfo): string }   // 4차: quiet 옵션 제거(B1 — ALREADY_*는 유스케이스가 성공으로 처리)
function useProductRun(): {
  run<T>(task: (signal: AbortSignal) => Promise<T>, options: RunOptions): Promise<T | null>   // 이미 진행 중이면 task를 부르지 않고 null(중복 제출 방지)
  status: 'idle' | 'running' | 'error'; errorMessage: string | null; errorCode: string | null
  reset(): void            // 진행 중이 아니면 idle, 오류 지움
}
// 4차: cancel() 제거(B2 — 취소 버튼 없음). 언마운트 시 진행 중 요청 abort는 유지(F10). abort된 요청의 결과로 상태를 바꾸지 않는다.
// 오류 읽기는 shared/lib/errorInfo의 readErrorInfo(F5: application은 ApiError를 직접 import하지 않는다)
```

훅(포트는 `useDep`으로, 정리된 요청의 결과로 상태를 바꾸지 않는다 — F10)

| 훅 | 받는 것 | 돌려주는 것 |
| --- | --- | --- |
| `useStoreProducts(storeId: string)` | `ProductRepositoryToken` | `useAsync(findByStore)`의 `{status:'loading'\|'success'\|'error', data: ProductPage, error, reload}`. `key = storeId` |
| `useProduct(productId: string)` | `ProductRepositoryToken` | **4차(C1, D-35)** `useAsync(findById)`의 `AsyncState<Product> & { reload(): void }`에 **`failure: ProductLoadFailure \| null`을 더한다**(전: 없음). `status === 'error'`일 때 `failure = productLoadFailure(readErrorInfo(error))`(404·403 → `notFound` + 「상품을 찾을 수 없어요.」, 그 밖 → `loadFailed` + 불러오기 문구), 그 외 상태에서는 `null`. 기존 `status`·`data`·`error`·`reload`는 그대로. `key = productId` |
| `useCreateProduct()` | `ProductCommandsToken` | `{ submit(storeId, value, photo): Promise<Product \| null>, status: 'idle'\|'submitting'\|'error', errorMessage: string \| null, photoError: boolean, reset(): void }` — **4차: `cancel()` 제거**(B2, D-11). 성공하면 `Product`를 resolve하고 `status`를 `idle`로, 실패하면 `null`을 resolve하고 `status='error'`·`errorMessage=productErrorMessage(…,'create')`. `IMAGE_TOO_LARGE`·`UNSUPPORTED_IMAGE_TYPE`이면 `photoError=true`(사진 칸에 표시). 제출 중 `submit` 재호출은 무시(이중 제출 방지). 언마운트 시 abort(F10, 유지) |
| `useSaveProduct()` | `ProductCommandsToken` | 같은 모양(`photoError` 없음), `submit(original, changes)` → 성공 시 갱신된 `Product`. ctx `'save'` |
| `useToggleProduct()` | `ProductCommandsToken` | `{ toggle(product): Promise<Product \| null>, status: 'idle'\|'pending'\|'error', errorMessage: string \| null }`. **4차(B1, D-33): 시그니처는 그대로, 동작 변경.** `PRODUCT_ALREADY_INACTIVE`·`PRODUCT_ALREADY_ACTIVE`는 **성공**이다: `toggleProduct`가 그 상태의 `Product`(`isActive`가 서버 응답이 가리키는 상태)를 resolve하므로 훅도 `null`이 아닌 `Product`를 resolve하고 `status`는 `idle`, `errorMessage`는 `null`이다(전: `null`을 돌려주고 화면이 `reload`). `null`은 이제 실패(`status='error'`)·중복 호출·abort일 때만이다. `PRODUCT_HAS_OPEN_OFFER` 등은 `errorMessage`(D-4) |
| `usePhotoDraft()` (O6 전용) | 없음 | `{ file: Blob \| null, previewSrc: string \| null, error: string \| null, pick(file: File): void, clear(): void }`. `pick`은 `validatePhoto`로 먼저 검사하고 **4차(A2, D-34): 실패하면 이전 `file`·`previewSrc`를 버리고(이전 미리보기 URL `revokeObjectURL`) `error`만 설정한다**(전: 이전 사진 유지). 통과하면 `URL.createObjectURL`로 미리보기를 만든다. 이전 미리보기 URL은 `revokeObjectURL`, 언마운트 시에도 revoke. `clear()`는 파일·미리보기를 버린다(revoke). `[차단 B-1]` `initial`·`removed`·`remove()`·`edit: PhotoEdit`는 O11 사진 재설계 때 추가 |

### 4.3 infrastructure (F9 — DTO는 이 폴더 안에서만)

`infrastructure/productDto.ts`
```ts
type ProductDto = { id: string; store_id: string; name: string; category: string | null; description: string | null; original_price: number; is_active: boolean; product_image: string[] | null }   // D-32: ProductDto·ProductListDto는 export하되 index.ts로는 내보내지 않는다
type ProductListDto = { items: ProductDto[]; page: number; size: number; total: number }
// [차단 B-1] type ImageUploadDto (POST …/images 응답)
export function toProduct(d: ProductDto, apiBase: string): Product
export function toProductPage(d: ProductListDto, apiBase: string): ProductPage
export function toImages(urls: string[], apiBase: string): ProductImage[]
export function toImageSrc(url: string, apiBase: string): string   // '//'(프로토콜 상대 주소)·'/\'로 시작 → '' (A1, D-24: 브라우저가 외부 호스트로 해석하므로 apiBase를 붙여도 외부 요청이 됨. 먼저 검사)
//   그 밖에 '/'로 시작 → apiBase + url / 'http://'·'https://' → 그대로 / 그 밖(javascript: 등) → '' (F17)
```
`toProduct`는 `product_image`가 `null`로 오면 `[]`로 본다. `src`가 `''`인 이미지는 `images`에서 **빼지 않는다**(저장할 때 `url`이 필요). 그림은 `src !== ''`일 때만 그린다.

| 구현체 | 포트 | 엔드포인트 |
| --- | --- | --- |
| `HttpProductRepository` | `ProductRepository`(entities) | `findByStore` → `GET /v1/stores/{id}/products?page=1&size=100`, `findById` → `GET /v1/products/{id}` (`encodeURIComponent`) |
| `HttpProductCommands` | `ProductCommands` | `create` → `POST /v1/stores/{id}/products` **항상 multipart**(D-10): `FormData`에 `name`, `original_price`(문자열), `category`·`description`(**값이 있을 때만, 빈 값은 키를 생략하고 null을 보내지 않는다**, D-18), `file`(있을 때만). `update` → `PATCH /v1/products/{id}` 본문은 `ProductChanges`를 `{name, category, description, original_price}`로 바꾼 JSON(키가 있는 것만 보낸다. `null`은 `category`·`description`을 비울 때만, D-18). `deactivate`·`activate` → `POST …/deactivate`·`…/activate` 본문 없음. `[차단 B-1]` `uploadPhoto`·`deleteUploadedPhoto`는 만들지 않는다 |

`API_BASE_URL`은 `@/shared/config/env`에서 읽어 `toProduct`에 인자로 넘긴다(domain·presentation은 env를 모른다, F6).

### 4.4 presentation

| 컴포넌트 | props | 화면 상태별 표시 |
| --- | --- | --- |
| `ProductList` | `storeId: string` | 로딩: `Skeleton` 3개 / 오류: `.err`(`productErrorMessage('load')`) + `Button` 「다시 시도」(`reload`) / 빈(`total === 0`): `EmptyState`(제목·설명 임시, 버튼 `Link` 「상품 등록」 → O6) / 성공: 상단 줄 「상품 {total}개」 + `Link.btn.sm` 「+ 상품 등록」, 그 아래 `ProductRow` 목록. `items.length < total`이면 목록만 보이고 개수는 total을 쓴다(D-15) |
| `ProductRow` | `product: Product` | `Link.li` → `ROUTES.ownerProduct(id)`. 왼쪽 `<b>이름</b>` + `.m` `productSubtitle`, 오른쪽 `StatusTag`(`productStatusTone/Label`) |
| `ProductForm` (내부 부품, 공개 API 아님, D-30) | `mode: 'create' \| 'edit'`(라벨만 다름: create는 「상품명 *」「정상 가격 *」, edit는 `*` 없음), `values: ProductFormInput`, `errors: Partial<Record<ProductFormField, string>>`, `disabled?: boolean`, `onChange(field: keyof ProductFormInput, value: string): void` | 제어 컴포넌트: 값·오류는 부모가 들고(`useState`), 검증(`validateProductForm`)·제출·버튼·`<form>`·`onSubmit`은 부모(`ProductCreateForm`·`ProductEditForm`)가 한다. 이 컴포넌트는 입력 4칸을 **`shared/ui/Input`을 쓰지 않고 직접 마크업**한다(4차 정정, C2, D-26): `<label className="lbl">` + `<input className="in">`(상품명·가격·카테고리), 설명은 `<textarea className="in">`. 이유 ① `Input`에 `disabled` prop이 없어 제출 중 입력 칸을 막을 수 없다 ② `Input`은 라벨에 `*`를 스스로 붙여 `PRODUCT_TEXT.create.nameLabel`(「상품명 *」)의 `*`와 중복된다. `Input`은 바꾸지 않는다(D1·C2). 칸별 오류 `FieldError`(검증 실패는 `onBlur`가 아니라 제출 시점에 부모가 `errors`를 채워 표시). `disabled`면 4칸 모두 비활성(제출 중) |
| `ProductCreateForm` | `storeId: string`, `onCreated(product: Product, intent: 'offer' \| 'list'): void` | `ProductForm` + `PhotoField` + 버튼. 제출 중(`submitting`): 두 버튼 `pending`(「처리 중…」), 입력 칸·사진 칸 비활성. **4차(B2, D-11): 사진 칸의 `uploading`(「올리는 중…」)은 사진이 있을 때만 보이고(`photoSlotPhase`가 `hasImage`와 함께 판정), 사진 없이 등록하면 사진 칸은 `empty` 그대로다. 등록 중 「취소」 버튼은 없다**(abort해도 서버에 상품이 이미 생길 수 있어 재등록 시 중복 위험). 화면을 떠나면(언마운트) 요청은 abort된다(F10). 실패: 폼 위 `.err`에 `errorMessage`, 사진 오류면 사진 칸을 `failed`로. 사진 검증 실패(`usePhotoDraft.error`, A2): 사진 칸은 비워지고(`hasImage` false) `failed`로 오류 문구와 「다른 사진 고르기」만 보인다 — 「다시 시도」는 **서버가 사진을 거절한 경우**(`create.photoError`, 사진이 칸에 있음)에만 준다(`PhotoField`에 `onRetry`를 넘기는 것은 `photo.error === null && create.photoError`일 때뿐, D-34 임시). 이렇게 하면 검증 실패 뒤 「다시 시도」가 사진 없이 조용히 제출되지 않는다. 성공: `onCreated`. **5차(D-37, D-38) 버튼 배치:** 같은 두 동작을 두 곳에 둔다. ① 모바일 `CtaBar`: 「등록만」(기본 `Button`, `style={{ flex: '0 0 auto' }}`, D-38) + 「등록하고 할인 만들기」(`primary`)(와이어프레임 O6 `.cta`와 같다). ② 데스크톱 오른쪽 열(`.dk`, 사진 힌트 아래): 「등록만」(**기본 `Button desktopOnly`**) 다음에 「등록하고 할인 만들기」(`primary desktopOnly`) 순서. 두 데스크톱 버튼은 같은 `submit('list')`·`submit('offer')`를 부르고 `disabled`·`pending`도 모바일 버튼과 같다. 기본→확정 순서는 O7(`StoreCloseForm`: 「취소」기본 → 「폐점하기」dark 둘 다 `desktopOnly`)과 `CtaBar` README("왼쪽 보조 + 오른쪽 확정")를 따른 것이다 |
| `ProductEditForm` | `product: Product`, `onSaved(product): void` | 입력은 `productFormFromProduct(product)`로 채움. **사진은 읽기 전용**(`[차단 B-1]`, D-28): 사진이 있으면 `.ph.photo` 안에 미리보기만 그리고 「사진 바꾸기」「사진 삭제」 버튼·링크와 시트는 없다. 저장 버튼은 `diffProduct`가 비었으면 비활성. 「노출 중」 칩/「숨김」 칩, 「숨기기」 링크(숨김 상품이면 「다시 보이기」 `Button`), 토글 오류 `.err`, 저장 오류 `.err`. 토글 성공 시 칩·버튼 갱신(화면에 남음, D-14). **4차(B1, D-33): 「숨기기」가 `PRODUCT_ALREADY_INACTIVE`, 「다시 보이기」가 `PRODUCT_ALREADY_ACTIVE`를 받아도 `useToggleProduct`가 `Product`를 resolve하므로 같은 경로로 칩·버튼이 그 상태로 바뀌고 `.err`는 보이지 않는다**(코드 변경은 훅·유스케이스 쪽이며 이 컴포넌트의 `if (next !== null) setActive(next.isActive)`는 그대로). 저장 성공은 `onSaved` |
| `PhotoField` | `phase: PhotoSlotPhase`, `src: string \| null`, `errorMessage: string \| null`, `onPick(file: File)`, `onRemove?()`(이번 차수엔 O6의 「삭제」만 쓴다), `onRetry?()`, `disabled?: boolean`, `hasImage: boolean` (**4차: `onCancel` 제거**) | `.ph.photo`(4:3). `empty`: 「+ 사진 추가 · 카메라 또는 앨범」 / `filled`: 미리보기 + 「사진 바꾸기」(`Button sm`) + 「삭제」·「사진 삭제」 링크(O11은 「사진 삭제」, O6은 「삭제」) / `uploading`: 미리보기 + 「올리는 중…」(진행률 없음, D-11). **「취소」 없음** / `failed`: accent 테두리 + 오류 문구 + 「다시 시도」(**`onRetry`가 있을 때만 보임**, 전: 항상) · 「다른 사진 고르기」. 「사진 추가」·「사진 바꾸기」·「다른 사진 고르기」는 `PhotoPickSheet`를 연다 |
| `ProductLoadError` (**4차 신규, 공개 API**, C1·D-35) | `failure: ProductLoadFailure`, `onRetry(): void` | `.err[role=alert]`에 `failure.message`. `kind === 'notFound'`: `Link.link` 「매장으로」(`PRODUCT_TEXT.edit.toStore`) → `ROUTES.ownerStore`, 「다시 시도」 없음. `kind === 'loadFailed'`: `Button` 「다시 시도」(`PRODUCT_TEXT.edit.retry`) → `onRetry`. `pages/product-edit`가 상품 문구를 갖지 않도록 이 영역이 오류 표시를 맡는다 |
| `PhotoPickSheet` | `onPick(file: File): void`, `onClose(): void` | `Overlay` + `.sheet`: 제목 「사진 추가」, 버튼 「카메라로 찍기」(숨은 `<input type="file" accept="image/*" capture="environment">`를 클릭), 「앨범에서 고르기」(`accept="image/jpeg,image/png,image/webp"`), 안내 「JPG·PNG·WebP, 5MB 이하」, 링크 「취소」. 파일을 고르면 `onPick` 후 `onClose` |

- 이미지는 `<img src={image.src} alt="">`(상품명을 이미 옆에 보여 주므로 장식), `src === ''`이면 그리지 않고 `empty`로 본다. 사용자 입력은 JSX 텍스트로만 출력한다(F17). 디자인 시스템 클래스만 쓴다(F12). 4:3 비율은 `.ph.photo`가 처리한다.
- 숫자 입력은 `<input type="text" inputMode="numeric">`(쉼표 허용, `parsePrice`가 처리).

### 4.5 공개 API (`features/products/index.ts`)
```ts
export type { ProductCommands, NewProduct } from './domain/productCommands'
export { validateProductForm } from './domain/productForm'   // 테스트·다른 영역에서 필요하면. 없으면 내보내지 않는다
export { ProductCommandsToken } from './application/tokens'
export { useStoreProducts } from './application/useStoreProducts'
export { useProduct } from './application/useProduct'
export type { ProductLoadFailure } from './domain/productMessages'   // 4차: useProduct().failure 타입
export { ProductList } from './presentation/ProductList'
export { ProductLoadError } from './presentation/ProductLoadError'   // 4차 신규
export { ProductCreateForm } from './presentation/ProductCreateForm'
export { ProductEditForm } from './presentation/ProductEditForm'
```
`validateProductForm`은 pages가 쓰지 않으므로 **내보내지 않는다**(공개 API는 pages가 쓰는 것만). 구현체·wiring은 내보내지 않는다(F18).

`wiring.ts`
```ts
export function wireProducts(): Binding[] {
  return [
    bind(ProductRepositoryToken, new HttpProductRepository()),   // 소유한 entities 포트
    bind(ProductCommandsToken, new HttpProductCommands()),       // 이 영역의 포트
  ]
}
```

## 5. pages

### 5.1 `pages/owner-store` — O4 (`/owner/store`, TabBar 있음, `handle: TAB_BAR_HANDLE`)

```tsx
export function OwnerStorePage()  // 공개 API: pages/owner-store/index.ts
```
1. `const store = useOwnerStore()` (null이면 `null` 렌더, 가드 통과 후라 실제로 null은 드묾 — stores.md §5와 같은 방식).
2. `AppBar logo title="매장" right={<><OwnerTopNav /><OwnerAccountButton /></>}` (placeholders의 OwnerPlaceholder와 같은 구조).
3. `<div className="body split">`: 왼쪽 `Box title={store.name}`(`.t`) + `<div className="m">{store.pickupAddress}</div>` + `StatusTag`(`storeStatusTone/Label(store.status)`). 오른쪽 `ProductList storeId={store.id}`, 그 아래 `OwnerAccountRows`(D-19, **5차: 모바일 전용**, PC에서는 숨김), 맨 아래 `Link.link` 「상점 폐점」 → `ROUTES.ownerStoreClose`(stores.md D-12).

**레이아웃 결함 2건 수정 규격(5차 보완, 결함 수정이며 새 결정 아님, frontend-e9 3차 실측 `O4-desktop.png`·`O4-mobile.png`). 임시: 정본에 O4 간격 값이 없어 아래 값은 설계자 임시.**
- 결함 1(1280px, 「영업 중」 칩이 패널 폭으로 늘어남). 원인: `OwnerStorePage.tsx:29`의 `StatusTag`(`<span className="tag">`)가 `.box`(`bundle.css:182`, `display: grid`)의 **직접 자식**이라 grid 항목이 되어 열 폭으로 stretch된다(`justify-items` 기본값 stretch). 수정: `StatusTag`를 일반 `<div>` 한 겹으로 감싼다(`<div><StatusTag …/></div>`). 칩은 div 안에서 인라인이라 내용 폭만 쓴다. 인라인 style 불필요. (대안 `justify-self: start`는 StatusTag에 `style` prop이 없어 쓰지 않는다. 와이어프레임 O6 `.btn.dk`의 `justify-self:start`와 같은 의도.)
- 결함 2(360·1280px, 「상점 폐점」이 목록 바로 아래에 붙음). 원인: `OwnerStorePage.tsx:33~39`의 오른쪽 열 `<div>`가 일반 블록이라 `ProductList`·`OwnerAccountRows`·`Link`가 간격 없이 이어진다(`.split`의 `gap`은 열 사이에만 적용). 수정: 오른쪽 열 `<div>`에 레이아웃용 인라인 style `{ display: 'grid', gap: 'var(--s3)', alignContent: 'start' }`(와이어프레임 O6의 열과 같은 방식, 간격은 토큰만), 「상점 폐점」 `Link`는 `<div>`로 한 겹 감싸 링크가 열 폭 전체로 늘어나지 않게 한다. 새 클래스·색·px 값 없음(F12).
- 영향: 모바일에서 `OwnerAccountRows`(`.mob`)가 있으면 목록·계정 행·폐점 링크 사이가 모두 `--s3`로 일정하다. PC(`.mob` 숨김)에서는 목록과 폐점 링크 사이만 `--s3`.
4. 상점 상태가 `SUSPENDED`이면 상품 목록은 그대로 보이고 등록은 서버가 `STORE_SUSPENDED`로 거절한다(O6에서 문구).

`widgets/owner-nav` 변경(D-19): `OwnerAccountRows` 추가·공개. 「계정」 라벨(`.lbl`) + 행 둘: `Link.li` 「비밀번호 변경 ›」 → `ROUTES.accountPassword`(`state.from` = 현재 경로, `OwnerAccountMenu`와 같은 방식), `button.li` 「로그아웃 ›」 → `@/features/auth`의 `LogoutConfirmSheet`(`widgets/owner-nav/presentation/OwnerAccountRows.tsx`가 직접 import, `useOwnerDialog`로 열기. widgets → features 방향이라 F1 허용). **5차(D-19 재결정): 라벨과 행 둘 전체를 `.mob`(720px 이상에서 `display: none`, `bundle.css:559`)으로 감싸 모바일에서만 보이게 한다.** `.mob`은 `display`를 바꾸므로 `.mob`에 grid를 직접 주지 않고, 그 안에 grid 래퍼를 둔다(`.mob` 숨김이 이기도록). PC는 오른쪽 위 「계정」 버튼(O8)이 같은 기능을 맡는다. 근거: `screens.md` O4 "모바일 매장 탭에도 같은 행", `wireframe.html` O4 노트. **구현은 frontend-e9 세션이 수행한다**(`OwnerAccountRows.tsx`와 그 테스트, 이 문서는 결정만 적는다). 이미 있는 `OwnerAccountMenu`·`OwnerLogoutLink`는 바꾸지 않는다.

### 5.2 `pages/product-new` — O6 (`/owner/products/new`, TabBar 없음)

`ProductNewPage`: `AppBar title="상품 등록" left={<Link to={ROUTES.ownerStore} aria-label="뒤로">←</Link>} right={<><OwnerTopNav /><OwnerAccountButton /></>}`(4차 정정: `routes.test.tsx`가 O6에서도 TopNav 활성 「매장」을 요구하고 §5.1·§5.3과 일관. 「뒤로」는 stores.md D-11 임시와 같다), `ProductCreateForm storeId={useOwnerStore().id} onCreated`. 성공 이동(D-5, D-9): `intent === 'offer'` → `navigate(ROUTES.ownerOfferNewFor(product.id))`(O3 자리 page), `'list'`(「등록만」) → `navigate(ROUTES.ownerStore)`. 이동은 `replace` 없이(뒤로 가면 O6 폼이 비어 다시 보임).

### 5.3 `pages/product-edit` — O11 (`/owner/products/:productId`, TabBar 없음)

`ProductEditPage`: `productId = useParams().productId`, `useProduct(productId)`.
- 로딩: `AppBar title="상품 수정"` + `.body[aria-busy]` 안에 `Skeleton`. 오류(4차, C1·D-35): `useProduct`의 `failure !== null`이면 `<ProductLoadError failure={product.failure} onRetry={product.reload} />`(`.body` 안)를 그린다. 404·403 구분·문구·「매장으로」·「다시 시도」는 모두 `features/products`가 갖고 **page는 상품 문구 상수를 갖지 않는다**(`TEXT` 상수와 그 TODO 주석 삭제, `readErrorInfo` import도 삭제). page는 AppBar 제목 「상품 수정」·뒤로 링크·이동만 가진다.
- 성공: `AppBar title="상품 수정" left=← right={<><OwnerTopNav /><OwnerAccountButton /></>}` + `ProductEditForm key={product.id} product onSaved={() => navigate(ROUTES.ownerStore)}`(D-14).
- `productId`가 UUID 형식이 아니면 서버가 400 `VALIDATION_ERROR`를 주므로 오류 분기로 처리(별도 검증 없음).

## 6. app

- `routes.tsx`: `ROUTES.ownerStore` → `<OwnerStorePage />`(`handle: TAB_BAR_HANDLE` 유지), `ROUTES.ownerProductNew` → `<ProductNewPage />`, `ROUTE_PATTERNS.ownerProduct` → `<ProductEditPage />`. 주석 `// O4·O6·O11은 products 구현으로 교체됨`은 쓰지 않는다(주석 불필요).
- `placeholders.tsx`: `OwnerStorePlaceholder`·`OwnerProductNewPlaceholder`·`OwnerProductEditPlaceholder`를 지운다. 파일 머리 TODO의 `언제:`에서 `O4 구현 시, O6 구현 시, O11 구현 시`를 뺀다(남은 `O1`·`O2`·`O3`·`C2`·`C5`). 파일 자체는 지우지 않는다. `useParams`는 `OfferDetailPlaceholder`가 계속 쓴다.
- `container.ts`: `import { wireProducts } from '@/features/products/wiring'` + `...wireProducts()` 한 줄. `tests/app/container.test.ts` 토큰 목록에 `ProductRepositoryToken`, `ProductCommandsToken`을 같은 커밋에서 추가한다.
- 라우트 순서·가드·`OwnerLayout`·`OwnerStoreGate`는 바꾸지 않는다. `OwnerStoreGate`가 CLOSED 상점의 O4·O6·O11 접근을 O0로 보낸다(stores.md §3.1).

## 7. 401·TOKEN_REVOKED 연결 (FIXME `useAuthController.ts:13`) (D-21)

- 이 FIXME가 요구한 "공용 요청에서 받은 401을 `SessionStoreToken.clear()`로 잇는 것"은 stores 차수에 **이미 구현**됐다(`shared/api/client.ts:35~44` → `shared/api/authFailure.ts` → `app/providers/AuthFailureBridge.tsx`, `App.tsx:14`). products의 모든 요청(`request`)이 이 경로를 지나므로 **새 코드를 만들지 않는다**.
- 이번 구현에서 할 일: ① `features/auth/application/useAuthController.ts:12~14`의 FIXME 주석을 지운다(`features/auth` 소유 `fe-developer`가 주석만 수정, 같은 커밋). ② products 요청이 401을 받으면 세션이 정리되는지를 통합 테스트로 확인한다(§9.8). ③ `shared` 쪽 쓰기는 §2.1(multipart)뿐이며, 401 처리 코드는 바꾸지 않는다.
- stores.md §10 "삭제" 행이 이 FIXME 삭제를 약속했는데 이행되지 않았다(C-7). 낡은 문구("공용 훅이 아직 없다")를 근거로 `products 구현 시`에 걸려 있었다.

### 7.1 `AuthFailureBridge` 수정 (C-12, D-27) — 쓰기 소유: app 담당 `fe-developer`

- 결함: `cleared`가 한 번 `true`가 되면(`app/providers/AuthFailureBridge.tsx:12~16`) `App`이 다시 마운트되지 않는 한 `false`로 돌아가지 않아, 재로그인 뒤 두 번째 세션 만료의 401이 세션을 정리하지 못한다.
- 수정 방식(임시): `cleared` 플래그를 없애고 **세션 유무로 중복을 막는다**. 핸들러는 `if (!sessionStore.hasSession()) return; sessionStore.clear()`. 연속된 401은 첫 호출이 세션을 지우면 `hasSession()`이 `false`라 나머지는 무시되고(기존 "정리 1회" 유지), 재로그인으로 세션이 다시 생기면 다음 401은 다시 정리된다. 포트는 기존 `SessionStore.hasSession`·`clear`만 쓴다(새 포트·토큰 없음).
- 알려진 한계: 재로그인 직후 **옛 토큰으로 보낸 요청의 늦은 401**이 새 세션을 지울 수 있다. 이를 막으려면 401 알림이 요청에 쓴 토큰을 알려야 하는데 `shared/api` 변경이 더 커서 이번 범위에 넣지 않는다(재발 시 별도 결정).
- 쓰기 범위: `src/app/providers/AuthFailureBridge.tsx`, `tests/app/providers/AuthFailureBridge.test.tsx`, 첫 줄 주석(결함 설명 문구가 있다면 갱신). `shared/api/authFailure.ts`·`client.ts`는 바꾸지 않는다.

## 8. F1~F19 점검 메모 (설계 시점)

| 규칙 | 설계에서 지킨 방법 |
| --- | --- |
| F1·F2 | `features/products`가 다른 영역을 import하지 않는다. 다른 slice에서는 `entities/product` 공개 API·`features/products` 공개 API만 쓴다 |
| F3·F4 | `shared`·`app`에 4계층 폴더 없음. `features/products`·`entities/product`는 4계층 이름만 쓰고, 쓰지 않는 계층(entities의 presentation·infrastructure)은 만들지 않는다 |
| F5·F18 | 훅은 `useDep(토큰)`으로 포트를 받는다. infrastructure는 포트 타입만 `import type`. `index.ts`는 구현체·wiring을 내보내지 않는다. 토큰은 소유 영역 한 곳(`wireProducts`)에서만 등록 |
| F6 | domain에 `File`을 넣지 않고 `PhotoMeta`·`Blob`만 쓴다. `URL.createObjectURL`은 application 훅, `API_BASE_URL`은 infrastructure로 넘긴다 |
| F7 | 검증·diff·사진 규칙·표기(가격·상태 라벨)는 domain 함수 |
| F8·F9 | `fetch`는 `shared/api`만. DTO는 `productDto.ts`에만. 페이지·훅은 `Product`만 본다 |
| F10 | 모든 서버 호출이 `AbortSignal`을 받고, 언마운트·취소 시 abort, 정리된 뒤 상태를 바꾸지 않는다. 로딩·오류·빈 상태를 컴포넌트가 모두 그린다 |
| F11 | 분기는 `errorCode`로만(`PRODUCT_HAS_OPEN_OFFER` 등). 서버 `message`는 화면에 노출하지 않는다(`NETWORK_ERROR`의 프론트 문구 제외, D-17 4차). `PRODUCT_ALREADY_*`는 성공으로 처리(D-33) |
| F12·F13 | 새 색·클래스 없음(CSS Module도 만들지 않음). 인라인 `style`은 O6 모바일 「등록만」의 레이아웃 `flex: '0 0 auto'` 하나뿐이고 색·간격 값은 없다(D-38). 문구는 정본, 없는 것은 임시로 표시(D-16) |
| F14 | URI·필드·`error_code`는 `reference/catalog.md` + 백엔드 코드로 대조(§0). 차이는 C-번호 |
| F17 | 이미지 `src`는 `/`·`http(s)`만 허용(`toImageSrc`). 토큰은 건드리지 않는다. `innerHTML` 등 없음 |
| F19 | §10에 남길 주석 |

## 9. 테스트 목록 (`tdd-workflow` §2, Red 대상)

위치는 `tests/` 아래 `src`와 같은 경로. 가짜 구현체는 `tests/<계층>/<slice>/fakes/*.fake.ts`. 새로 만들 보조:
- `tests/entities/product/fakes/fakeProductRepository.fake.ts`: `findByStore`, `findById` = `vi.fn()`
- `tests/features/products/fakes/fakeProductCommands.fake.ts`: `create`, `update`, `deactivate`, `activate`, `uploadPhoto`, `deleteUploadedPhoto` = `vi.fn()`
- `tests/entities/product/fakes/products.ts`: `breadProduct`(id `p1`, 「식빵 모둠 5종」, 카테고리 「빵」, 12000, 노출, 사진 `[{url:'/v1/products/p1/images/i1', src:'/v1/products/p1/images/i1'}]`), `baguetteProduct`(id `p2`, 「바게트」, 「빵」, 4000, 숨김, 사진 없음), `noCategoryProduct`(카테고리·설명 null)
- `tests/support/renderWithOwnerStore.tsx`를 확장해 `ProductRepositoryToken`·`ProductCommandsToken` 가짜를 받게 한다(기존 호출은 그대로 통과).
- `URL.createObjectURL`/`revokeObjectURL`은 `vi.stubGlobal`로 가짜(`blob:preview-1`)를 준다(jsdom에 없음).

### 9.1 shared

**`tests/shared/api/client.test.ts`에 추가** (`fetch` 모킹)
- `body`가 `FormData`이면 `fetch`에 그 `FormData`가 그대로 전달되고 `Content-Type` 헤더가 없다(`Authorization`은 있다).
- `body`가 객체이면 지금처럼 `Content-Type: application/json` + JSON 문자열(기존 테스트 유지).
- `FormData` 요청의 401 + `UNAUTHORIZED`도 인증 실패 핸들러를 1번 부른다.

**`tests/shared/api/client.test.ts` — null 단언은 §9.4 `httpProductCommands.test.ts`에 둔다(요청 모양은 infrastructure 책임).**

**`tests/shared/ui/Skeleton.test.tsx`**: `.card`와 `.sk` 요소를 그리고 `aria-hidden="true"`. **`EmptyState.test.tsx`**: 제목·설명·`action`을 그린다, `description`·`action`이 없으면 그 요소가 없다.

**`tests/shared/ui/Button.test.tsx`에 추가 (D-38, [추가 1])**: `style={{ flex: '0 0 auto' }}`를 주면 렌더된 `<button>`의 `style.flex`가 `0 0 auto`이고 클래스(`btn`, `dk` 등)는 그대로다. `style`이 없으면 `style` 속성이 없다.

**`tests/shared/lib/routes.test.ts`(있으면 추가)**: `ROUTES.ownerOfferNewFor('a b')` = `/owner/offers/new?productId=a%20b`.

### 9.2 `entities/product` domain — `tests/entities/product/domain/product.test.ts`
- `productStatusLabel`: 노출 → 「노출」 / 숨김 → 「숨김」. `productStatusTone`: `ok` / `mute`.
- `formatProductPrice`: 0 → `0원`, 999 → `999원`, 1000 → `1,000원`, 12000 → `12,000원`, 99999999 → `99,999,999원`.
- `productSubtitle`: 카테고리 「빵」·12000 → 「빵 · 12,000원」 / 카테고리 null → 「12,000원」 / 카테고리 빈 문자열 → 「12,000원」.
- `primaryImage`: 이미지 0장 → null / 2장 → 첫 장.
- `uploadedImageId('p1', '/v1/products/p1/images/i1')` → `i1` / 다른 상품 id(`/v1/products/p9/images/i1`) → null / `https://example.com/a.jpg` → null / `/v1/products/p1/images/` → null / 빈 문자열 → null.

### 9.3 `features/products` domain
**`productForm.test.ts`**
- 정상 입력(`'식빵 모둠 5종'`, `'12,000'`, `'빵'`, `'오늘 구운 식빵'`) → `ok`, 값 `{name, originalPrice: 12000, category:'빵', description:'…'}`.
- 이름: `''`·`'   '` → `errors.name` / 1자 ok / 200자 ok / 201자 → `errors.name` / 앞뒤 공백은 제거되어 값에 반영.
- 가격: `''` → `errors.price`(필수) / `'0'` → 오류 / `'1'` ok / `'99999999'` ok / `'100000000'` → 오류 / `'12a'`·`'1.5'`·`'-1'` → 오류 / `' 12,000 '` → 12000.
- 카테고리: `''`·`'  '` → 값 `null`, 오류 없음 / 80자 ok / 81자 → `errors.category`.
- 설명: 빈 값 → `null`.
- 오류가 여러 칸이면 `errors`에 모두 담긴다.
- `parsePrice`: `'12,000'` → 12000 / `'abc'` → null / `''` → null / `'007'` → 7.
- `productFormFromProduct(noCategoryProduct)`: `category`·`description`이 `''`, `price`는 `'12000'`.

**`productChanges.test.ts`**
- 같은 값 → `diffProduct` = `{}`, `hasChanges` false.
- 이름만 다름 → `{name}`만. 가격만 다름 → `{originalPrice}`만.
- 카테고리를 `'빵'` → `null`로 비움 → `{category: null}` / 원래 null, 새 값 null → 키 없음.
- 설명 `'a'` → `null` → `{description: null}`.
- 원래 설명 null, 새 값 null → 키 없음(비우기가 아닌 null은 만들어지지 않는다). 카테고리·설명이 모두 안 바뀌면 `category`·`description` 키가 없다(`'category' in changes`가 false).
- 값이 `null`인 키는 `category`·`description`에서만 나온다(이름·가격은 항상 값).
- `[차단 B-1]` `hasChanges({productImage: []})` → 쓰지 않는다.

**`productPhoto.test.ts`**
- `validatePhoto`: `image/jpeg` 1바이트 → null / `image/png`·`image/webp` ok / `image/gif` → `UNSUPPORTED_TYPE` / `application/pdf` → `UNSUPPORTED_TYPE` / size 0 → `EMPTY`(형식이 맞아도) / size 5,242,880(정확히 5MiB) → null / 5,242,881 → `TOO_LARGE` / 형식 오류와 크기 초과가 겹치면 `UNSUPPORTED_TYPE`.
- `photoSlotPhase`: `{hasImage:false, uploading:false, error:null}` → `empty` / `hasImage` → `filled` / **[변경 B2] `{hasImage:false, uploading:true, error:null}` → `empty`**(전: `uploading`. 케이스 이름 「uploading → uploading」을 「사진 없이 uploading이면 empty」로) / `error` 문자열 있음 → `failed`(다른 값보다 우선) / `uploading`과 `hasImage` 둘 다 → `uploading`(유지).
- `[차단 B-1]` `planProductImages` 테스트 전부(keep·remove·replace)는 쓰지 않는다. 재설계 때 새로 적는다.

**`productMessages.test.ts`**: 위 §4.1 표의 조건별 문구(`IMAGE_TOO_LARGE` → 정본 5MB 문구 / `UNSUPPORTED_IMAGE_TYPE` / `PRODUCT_HAS_OPEN_OFFER`(`toggle`) / `STORE_SUSPENDED`·`STORE_CLOSED`·`STORE_NOT_APPROVED` / **[변경 A3] `VALIDATION_ERROR`는 서버 message가 있어도 쓰지 않고 `saveFailed` 공통 문구(create·save), load는 불러오기 문구** / `NETWORK_ERROR`는 message 그대로 / 모르는 코드 → 기본 문구, `load`는 불러오기 문구). `productCountLabel(4)` = 「상품 4개」, `productCountLabel(0)` = 「상품 0개」. **[추가 C1] `productLoadFailure`**: status 404 → `{kind:'notFound', message:'상품을 찾을 수 없어요.'}` / 403 → 같음 / 500(`UNKNOWN`) → `{kind:'loadFailed', message: 불러오기 기본 문구}` / `NETWORK_ERROR`(status 0) → `loadFailed`, message는 서버(`ApiError`)가 만든 문구 그대로.

**`productToggle.test.ts`(신규, `tests/features/products/domain/`) [추가 B1]**: `productWhenAlready(breadProduct, 'PRODUCT_ALREADY_INACTIVE')` → `{...breadProduct, isActive:false}` / `(baguetteProduct, 'PRODUCT_ALREADY_ACTIVE')` → `isActive:true` / `'PRODUCT_HAS_OPEN_OFFER'`·`'STORE_CLOSED'`·`'UNKNOWN'` → `null` / 이름·가격·사진 등 다른 필드는 그대로.

### 9.4 `features/products` infrastructure
**`productDto.test.ts`**
- `toProduct`: snake_case → camelCase, `is_active`, `product_image: null` → `images: []`.
- `toImageSrc('/v1/products/p1/images/i1', '')` → 같은 값 / `apiBase='https://api.x'` → `https://api.x/v1/products/p1/images/i1` / `https://example.com/a.jpg` → 그대로 / `javascript:alert(1)`·`data:…`·빈 문자열 → `''` / **[추가 A1]** `//evil.example/a.png`(apiBase `''`와 `https://api.x` 모두) → `''`, `/\evil.example/a.png` → `''`, `//` 단독 → `''`, 정상 상대 경로 `/v1/products/p1/images/i1`은 여전히 apiBase를 붙인다(회귀 방지). `toProduct`에 `product_image: ['//evil.example/a.png']`를 주면 `images[0].src === ''`이고 `url`은 원본 유지. `toProduct`는 `src === ''` 이미지도 `images`에 남긴다(`url` 보존).
- `toProductPage`: `items`·`page`·`size`·`total` 매핑.

**`httpProductRepository.test.ts`** (`shared/api/client`의 `request` 모킹)
- `findByStore('s1')`: 경로 `/v1/stores/s1/products?page=1&size=100`, `is_active` 쿼리 없음, 응답을 `ProductPage`로 / 상점 id가 특수문자면 인코딩.
- `findById('p1')`: 경로 `/v1/products/p1`.
- `ApiError`는 그대로 던진다.

**`httpProductCommands.test.ts`** (`request` 모킹)
- `create`: 경로·`POST`, `body`가 `FormData`. `name`·`original_price`(문자열 `'12000'`)가 있고, `category`·`description`이 `null`이면 키가 없고, 값이 있으면 있다. `photo` 있으면 `file`, 없으면 `file` 키 없음. `product_image`는 절대 안 보낸다. **어떤 키의 값도 문자열 `'null'`·`''`이 아니다(null 비전송 단언: 모든 `FormData` 값에 `'null'`이 없다).**
- `update`: `PATCH /v1/products/p1`, 본문에 `ProductChanges`의 키만(`originalPrice` → `original_price`). `{category: null}` → 본문 `{category: null}`, `{description: null}` → `{description: null}`. `{name: 'x'}` → 본문 키가 `name` 하나뿐이고 `category`·`description`·`product_image`가 없다(null 포함 어떤 형태로도 나가지 않음). `{}`이면 부르는 쪽(`saveProduct`)이 호출하지 않으므로 이 함수는 키 없는 본문 `{}`을 만들지 않는다는 단언은 `saveProduct` 쪽에서 한다.
- **"null은 비우기 외에는 나가지 않는다"**: 이름·가격·카테고리·설명을 바꾸는 여러 조합(이름만, 가격만, 카테고리 값 변경, 카테고리 비우기, 설명 비우기+이름 변경)에 대해 `update` 본문의 `null`인 값은 비운 필드에만 있다. `create` 본문(`FormData`)에는 `null`이 아예 없다(빈 값은 생략).
- `deactivate`·`activate`: `POST /v1/products/p1/deactivate`·`/activate`, 본문 없음.
- `[차단 B-1]` `uploadPhoto`·`deleteUploadedPhoto` 테스트는 쓰지 않는다.

### 9.5 `features/products` application
**`createProduct.test.ts`**: `commands.create`가 `(storeId, {name, originalPrice, category, description}, photo, signal)`로 1번 불린다 / 사진 없음이면 `photo === null` / 성공 값을 그대로 돌려준다 / 실패하면 같은 오류를 던진다(`deleteUploadedPhoto`·`uploadPhoto`는 불리지 않는다).

**`saveProduct.test.ts`** (가짜 commands)
- 변경 있음: `update(original.id, changes)`만 1번(키는 changes 그대로), 반환은 `update` 응답.
- 변경 없음(`{}`): 아무것도 부르지 않고 `original` 반환.
- `update` 실패: 같은 오류를 던진다.
- `{category: null}`은 그대로 `update`에 전달된다. 그 밖의 필드에 `null`을 새로 만들어 넣지 않는다.
- `[차단 B-1]` 사진 교체·삭제·롤백(`uploadPhoto`·`deleteUploadedPhoto`) 테스트는 쓰지 않는다.

**`toggleProduct.test.ts`**: 노출 상품 → `deactivate` / 숨김 상품 → `activate`, 확인 단계 없음 / `PRODUCT_HAS_OPEN_OFFER` 등 오류를 그대로 던진다. **[추가 B1]** 노출 상품의 `deactivate`가 `ApiError(400,'PRODUCT_ALREADY_INACTIVE')`로 reject → 던지지 않고 `{...product, isActive:false}` resolve / 숨김 상품의 `activate`가 `PRODUCT_ALREADY_ACTIVE`로 reject → `{...product, isActive:true}` resolve / abort로 reject된 오류는 그대로 던진다.

**`useStoreProducts.test.tsx`** (`renderHook` + `DepsProvider`)
- 처음 `loading` → `findByStore('s1')`가 목록으로 resolve → `success`와 `data.items`.
- `items: []`, `total: 0`도 `success`(빈 상태 판단은 화면).
- reject → `error` / `reload()`로 호출 2회.
- 언마운트하면 넘긴 `signal.aborted === true`, 이후 resolve해도 상태 불변.

**`useProduct.test.tsx`**: 같은 항목(`findById('p1')`) + `productId`가 바뀌면 `loading`으로 돌아가 다시 호출. **[추가 C1]** `failure`: `loading`·`success`에서는 `null` / `ApiError(404,'NOT_FOUND')` reject → `failure = {kind:'notFound', message:'상품을 찾을 수 없어요.'}` / 403 `FORBIDDEN` → 같음 / 500 → `{kind:'loadFailed', message: 불러오기 문구}`. 기존 `status`·`data`·`error`·`reload` 단언은 그대로.

**`useCreateProduct.test.tsx`**
- 처음 `idle`. `submit` 중 `submitting`, 성공하면 `Product` resolve, `idle`.
- 실패(`ApiError(400,'STORE_SUSPENDED')`): `null` resolve, `status='error'`, `errorMessage`가 정지 문구, `photoError` false.
- `IMAGE_TOO_LARGE`: `photoError` true, `errorMessage` = 5MB 문구. `UNSUPPORTED_IMAGE_TYPE`도 `photoError` true.
- `submitting` 중 `submit` 재호출은 `commands.create`를 추가로 부르지 않는다(1회).
- **[삭제 B2]** 「`cancel()`: 넘긴 signal이 abort되고…」 케이스(훅이 `cancel`을 돌려주지 않음).
- 실패 뒤 `reset()` → `idle`, `errorMessage` null.
- 언마운트 시 abort(유지. 언마운트 뒤 늦게 끝난 결과로 상태를 바꾸지 않는다는 단언을 함께 확인).
- **[추가 A3]** `ApiError(400,'VALIDATION_ERROR','field required')` → `errorMessage` = 공통 `saveFailed` 문구(서버 message가 들어가지 않음).

**`useSaveProduct.test.tsx`**: 성공 시 갱신된 `Product` resolve / **[변경 A3]** `VALIDATION_ERROR` 400(서버 message 「정상 가격은 진행 중인 할인 가격보다 커야 합니다.」) → `errorMessage`가 **서버 문구가 아니라 공통 `saveFailed` 문구**(케이스 이름 「서버 message가 errorMessage가 된다」를 「서버 message를 쓰지 않고 공통 문구」로) / 중복 제출 무시 / 언마운트 abort.

**`useToggleProduct.test.tsx`**
- 노출 상품 `toggle` → `deactivate` 호출, 성공하면 `isActive:false` Product resolve, `idle`.
- 숨김 상품 → `activate`.
- `PRODUCT_HAS_OPEN_OFFER` 400: `null` resolve, `status='error'`, `errorMessage` = 숨기기 거절 문구(D-4 임시).
- **[변경 B1]** `PRODUCT_ALREADY_INACTIVE`(노출 상품을 `toggle`): `null`이 아니라 `{...product, isActive:false}`를 resolve, `errorMessage` null, `status` `idle`. `PRODUCT_ALREADY_ACTIVE`(숨김 상품): `{...product, isActive:true}` resolve. (`it.each` 두 행의 기대값과 케이스 이름 「null을 resolve하고…」를 바꾼다. `status`는 `not.toBe('error')` 대신 `idle`로 단언)
- `PRODUCT_HAS_OPEN_OFFER`는 여전히 `null` + `status='error'`(유지).
- `pending` 중 재호출 무시.

**`usePhotoDraft.test.tsx`**
- 처음 `file`·`previewSrc`·`error`가 모두 null.
- 정상 파일 `pick` → `file`이 그 파일, `previewSrc='blob:preview-1'`, `error` null.
- **[변경 A2]** 정상 파일 `pick` 뒤 6MB 파일 `pick` → `error` = 5MB 문구, **`file`·`previewSrc`가 null(이전 사진 버림)**, 이전 미리보기 `blob:preview-1`을 `revokeObjectURL`(케이스 이름 「이전 상태를 유지한다」를 「이전 사진을 버리고 error만 설정」으로).
- `image/gif` `pick` → 형식 문구, `file`·`previewSrc` null(처음부터 비어 있던 경우, 유지). **[추가 A2]** 정상 파일 `pick` 뒤 `image/gif` `pick` → 형식 문구 + `file`·`previewSrc` null + revoke 1회.
- **[추가 A2]** 검증 실패 뒤 정상 파일 `pick` → `error` null, `file`이 그 파일, 새 미리보기 URL.
- 두 번째 `pick`이 성공하면 이전 미리보기 URL을 `revokeObjectURL`.
- `clear()` → `file`·`previewSrc` null, 미리보기 revoke.
- 언마운트 시 마지막 미리보기 revoke.
- `[차단 B-1]` `initial`·`remove()`·`edit`(`keep`·`replace`·`remove`) 관련 케이스는 쓰지 않는다.

### 9.6 `features/products` presentation
(`renderWithOwnerStore` + 가짜. 문구는 §4.1 표, 클래스는 `components/*/preview.html`)

**`ProductList.test.tsx`**
- 로딩: 뼈대(`.sk`) 3개, 상품 행·빈 상태 없음.
- 성공(`breadProduct`, `baguetteProduct`, total 2): 「상품 2개」, 행 2개(이름·「빵 · 12,000원」·「빵 · 4,000원」), 노출 행의 태그 「노출」(`.tag.ok`), 숨김 행의 태그 「숨김」(`.tag.mute`), 행 링크 `href="/owner/products/p1"`, 「+ 상품 등록」 링크 `href="/owner/products/new"`.
- 카테고리 없는 상품: 보조 줄이 「12,000원」.
- `items.length < total`(예: total 130, items 100): 「상품 130개」, 행 100개.
- 빈(total 0): 「아직 등록한 상품이 없어요」, 「상품 등록」 링크 → `/owner/products/new`, 상품 행 없음.
- 오류(`ApiError(500,'UNKNOWN')`): `role="alert"`에 불러오기 문구, 「다시 시도」를 누르면 `findByStore` 2번째 호출.
- `findByStore`가 `storeId`로 호출된다.

**`ProductCreateForm.test.tsx`**
- 초기: 입력 라벨 「상품명 *」·「정상 가격 *」·「카테고리」·「설명」·「상품 사진 (1장)」, 사진 칸 `empty`(「사진 추가 · 카메라 또는 앨범」), 버튼 「등록하고 할인 만들기」·「등록만」.
- 빈 상태로 제출 → `create` 호출 없음, 이름·가격 칸에 오류(`role="alert"`).
- **[추가 D-37]** 데스크톱 「등록만」: `.dk` 버튼 「등록만」이 `.cta` 밖(`.body` 안 오른쪽 열)에 하나 있고, 같은 곳에 「등록하고 할인 만들기」 `.dk`가 하나 있다(`container.querySelectorAll('.dk')` 2개, 순서: 「등록만」 → 「등록하고 할인 만들기」, 「등록만」은 `.pri`가 아니고 「등록하고 할인 만들기」는 `.pri`). 모바일 `.cta` 안에도 같은 문구 버튼이 각각 하나(jsdom은 CSS를 계산하지 않으므로 `.cta .btn` 2개 + `.dk` 2개 = 문구마다 2개). 데스크톱 「등록만」(`.dk`)을 눌러도 `create('s1', …, null)` + `onCreated(product, 'list')`. 제출 중이면 모바일·데스크톱 4개 버튼 모두 「처리 중…」·`aria-disabled="true"`.
- **[추가 D-38]** `.cta` 안의 「등록만」 버튼의 `style.flex`가 `0 0 auto`이고, 「등록하고 할인 만들기」(`.cta` 안)와 데스크톱 `.dk` 버튼들에는 `style`이 없다(jsdom은 레이아웃을 계산하지 않으므로 인라인 값만 확인. 줄바꿈 자체는 fe-qa 실측 §9.10).
- 이름 + 가격 입력 후 「등록만」 → `create('s1', {name, originalPrice, category:null, description:null}, null)`, 성공하면 `onCreated(product, 'list')`.
- 「등록하고 할인 만들기」 → `onCreated(product, 'offer')`.
- 사진 선택(파일 입력 `change`, 정상 파일) → 사진 칸 `filled`(미리보기, 「사진 바꾸기」·「삭제」), 제출 시 `create` 3번째 인자가 그 파일.
- **[변경 A2]** 6MB 파일 선택 → 사진 칸 `failed`, 5MB 문구, 미리보기 `img` 없음, 「다른 사진 고르기」 표시, **「다시 시도」는 없음**(전: 있음), 제출 시 `create` 3번째 인자는 `null`(전: `not.toBe(big)`. 케이스 이름 「…다른 사진 고르기·다시 시도」에서 「다시 시도」 제거).
- **[추가 A2]** 정상 사진을 고른 뒤 6MB 사진을 고르면 이전 사진 미리보기가 사라지고 제출 시 `create` 3번째 인자가 `null`(이전 사진이 가지 않는다).
- **[추가 A2]** 검증 실패 뒤 「다른 사진 고르기」로 정상 파일을 고르면 사진 칸이 `filled`로 돌아오고 오류 문구가 사라진다.
- 「삭제」 → 사진 칸 `empty`, 제출 시 사진 `null`.
- **[변경 B2]** 제출 중(사진 있음): 두 버튼 「처리 중…」·`aria-disabled="true"`, 사진 칸 「올리는 중…」, 입력 칸 비활성, **「취소」 버튼 없음**(`queryByText('취소')`가 null. 전: 「올리는 중…」 + 「취소」 존재 단언. 케이스 이름 「…「올리는 중…」+「취소」…」 → 「…「올리는 중…」, 취소 없음…」).
- **[추가 B2]** 제출 중(**사진 없음**): 「올리는 중…」이 없고 사진 칸은 `empty` 문구(「사진 추가 · 카메라 또는 앨범」) 그대로, 두 버튼은 「처리 중…」, 「취소」 없음.
- **[삭제 B2]** 「「취소」를 누르면 signal이 abort되고 버튼이 원상 복구된다」 케이스.
- **[추가 B2]** 제출 중 폼을 언마운트하면 `create`에 넘긴 `signal.aborted === true`(F10 유지).
- 제출 중 버튼을 한 번 더 눌러도 `create`는 1회.
- `ApiError(400,'IMAGE_TOO_LARGE')`: 사진 칸 `failed` + 5MB 문구, 입력값은 그대로 남는다(사진은 칸에 남아 있고 서버 거절이므로 「다시 시도」 표시). 「다시 시도」 → 같은 입력으로 `create` 재호출(유지). 「다른 사진 고르기」 → 시트가 열린다.
- `STORE_SUSPENDED`: 폼 위 `.err`에 정지 문구, 입력값 유지, 사진 칸은 `failed`가 아님.
- 「사진 추가」 클릭 → `PhotoPickSheet`(「카메라로 찍기」·「앨범에서 고르기」·「취소」) 열림, 「취소」로 닫히고 포커스가 열었던 버튼으로 돌아감.

**`ProductEditForm.test.tsx`**
- 초기 값: 이름·가격(`12000`)·카테고리·설명이 `breadProduct`로 채워짐, 사진은 읽기 전용 미리보기(`img[src]`, 「사진 바꾸기」·「사진 삭제」 없음, D-28), 칩 「노출 중」, 링크 「숨기기」, 「저장」 비활성(`aria-disabled`).
- 사진이 없는 상품(`baguetteProduct`)은 사진 칸에 미리보기 `img`가 없다.
- 이름을 바꾸면 「저장」 활성 → 누르면 `update('p1', {name})`(바뀐 필드만), 성공하면 `onSaved`.
- 가격에 `'abc'` 입력 후 저장 → `update` 호출 없음, 가격 칸 오류.
- 카테고리를 비우고 저장 → `update('p1', {category: null})`. 설명만 비우면 `{description: null}`만, 이름만 바꾸면 `{name}`만(null 키 없음).
- `[차단 B-1]` 「사진 삭제」·「사진 바꾸기」·`uploadPhoto`·`deleteUploadedPhoto` 케이스는 쓰지 않는다.
- 저장 중 「저장」 「처리 중…」, 중복 제출 방지.
- **[변경 A3]** 저장 실패(`VALIDATION_ERROR` 400 + 서버 message): `.err`에 **공통 `saveFailed` 문구**(서버 message가 화면에 없음), 입력값 유지, `onSaved` 미호출(케이스 이름 「.err에 서버 문구」 → 「.err에 공통 문구」).
- 「숨기기」: 확인 시트 없이 바로 `deactivate('p1')`, 성공하면 칩 「숨김」, 링크가 「다시 보이기」 `Button`으로 바뀜, 화면에 남는다(`onSaved` 미호출).
- **[추가 B1]** 「숨기기」가 `ApiError(400,'PRODUCT_ALREADY_INACTIVE')`: 칩 「숨김」, 「다시 보이기」 `Button`으로 바뀜, `.err` 없음, `findById`(reload) 추가 호출 없음. 숨김 상품(`baguetteProduct`)의 「다시 보이기」가 `PRODUCT_ALREADY_ACTIVE`: 칩 「노출 중」, 「숨기기」 링크, `.err` 없음.
- 「숨기기」 거절(`PRODUCT_HAS_OPEN_OFFER` 400): 칩·링크 그대로(「노출 중」·「숨기기」), `.err`에 임시 거절 문구.
- 숨김 상품(`baguetteProduct`): 칩 「숨김」, 「다시 보이기」 → `activate('p2')`, 성공하면 칩 「노출 중」·「숨기기」.
- 숨기기·다시 보이기 중에는 해당 컨트롤이 「처리 중…」이고 비활성.

**`PhotoField.test.tsx`**(O6에서 쓰는 모양까지만, O11 「사진 삭제」 링크 문구는 `[차단 B-1]`): `phase` 4가지별 표시(§4.4 표) — `empty`는 「사진 추가」 문구, `filled`는 미리보기·「사진 바꾸기」·삭제 링크, `uploading`은 「올리는 중…」(진행 막대·퍼센트 없음, **[변경 B2] 「취소」 없음** — 케이스 이름 「…「올리는 중…」과 「취소」가 있고…」 → 「…「올리는 중…」만 있고 취소가 없다」, `renderField` 기본 props에서 `onCancel` 제거), `failed`는 `errorMessage`·「다시 시도」·「다른 사진 고르기」. **[추가 D-34]** `failed`인데 `onRetry`를 안 넘기면 「다시 시도」가 없고 「다른 사진 고르기」만 있다. `src`가 `''`이면 이미지를 그리지 않는다. `disabled`이면 버튼 비활성.

**`PhotoPickSheet.test.tsx`**: 제목 「사진 추가」, 두 버튼과 안내 「JPG·PNG·WebP, 5MB 이하」, 「카메라로 찍기」의 입력에 `capture="environment"`, 「앨범에서 고르기」의 입력 `accept`에 세 형식. 파일 선택 → `onPick(file)` → `onClose`. 「취소」·Esc·딤 클릭 → `onClose`.

### 9.7 pages
**`tests/pages/owner-store/OwnerStorePage.test.tsx`** (`renderWithOwnerStore`, 활성 상점 「망원베이커리」)
- 상점 이름·주소·태그 「영업 중」을 그린다. 정지 상점은 태그 「상점 정지」.
- 목록은 `useOwnerStore().id`로 불러온다.
- 「상점 폐점」 링크 → `/owner/store/close`.
- **[추가 §5.1 결함 1]** 「영업 중」 태그(`.tag`)의 부모가 `.box`가 아니라 일반 `<div>`이고 그 `<div>`의 부모가 `.box`다(`tag.parentElement.classList.contains('box')`가 false, `tag.parentElement.parentElement`가 `.box`).
- **[추가 §5.1 결함 2]** 「상점 폐점」 링크의 부모는 `<div>`이고 그 `<div>`는 오른쪽 열의 직접 자식이다. 오른쪽 열 `<div>`의 인라인 style이 `display: grid`, `gap: var(--s3)`(jsdom이 `style.gap`을 읽으면 단언, 못 읽으면 `style` 속성 문자열에 `var(--s3)` 포함 단언)이다. 색(`#`·`rgb`)·`px` 값은 style에 없다.
- 「계정」 라벨 아래 「비밀번호 변경」 링크 → `/account/password`, 「로그아웃」 버튼 → 로그아웃 확인 시트. **[변경 D-19 5차]** 이 행들(라벨 포함)은 `.mob` 요소 안에 있다(`closest('.mob')`가 null이 아님). PC 숨김은 CSS(`.mob`)라 jsdom은 클래스 포함만 단언하고, 실제 숨김은 fe-qa 실측(§9.10). 이 단언은 `tests/widgets/owner-nav/presentation/OwnerAccountRows.test.tsx`에 두는 것이 정본이고(frontend-e9 담당), 이 페이지 테스트의 같은 단언은 중복이면 추가하지 않아도 된다.
- **[frontend-e9 담당] `OwnerAccountRows.test.tsx`**: ① 라벨·두 행이 `.mob` 안에 있다(라벨·링크·버튼 각각 `closest('.mob')`) ② `.mob` 바로 안의 grid 래퍼가 `.mob` 자신이 아니다(`.mob`에 인라인 `display`가 없다) ③ 「비밀번호 변경」「로그아웃」 동작은 기존과 같다 ④ PC 숨김 회귀: `bundle.css`에서 `@container app (min-width: 720px)` 블록의 `.mob { display: none }` 존재를 읽어 확인(복사본 `src/app/styles/bundle.css` 문자열 단언).
- 상품 행을 누르면 `/owner/products/p1`, 「+ 상품 등록」은 `/owner/products/new`로 이동.

**`ProductNewPage.test.tsx`**: AppBar 제목 「상품 등록」, 「뒤로」 링크 → `/owner/store`. 「등록만」 성공 → `/owner/store`로 이동. 「등록하고 할인 만들기」 성공 → `/owner/offers/new?productId=<새 상품 id>`로 이동(자리 page 「O3 할인 등록」).

**`ProductLoadError.test.tsx`(신규, `tests/features/products/presentation/`) [추가 C1]**: `failure={kind:'notFound', message:'상품을 찾을 수 없어요.'}` → `role="alert"`에 그 문구 + 「매장으로」 링크 `href="/owner/store"`, 「다시 시도」 없음 / `kind:'loadFailed'` → 문구 + 「다시 시도」 버튼, 누르면 `onRetry` 1회, 「매장으로」 없음 / `message`는 전달받은 값을 그대로 그린다(컴포넌트가 문구를 새로 만들지 않음).

**`ProductEditPage.test.tsx`**: 로딩 중 `aria-busy`·뼈대 / 성공 → 「상품 수정」 제목, 폼 채워짐 / `ApiError(404,'NOT_FOUND')`·`403` → 「상품을 찾을 수 없어요.」 + 「매장으로」 링크(**[유지, C1: 이제 `ProductLoadError`를 거쳐 그려짐. 단언은 그대로 통과해야 함. page 파일에 상품 문구 상수가 없는 것은 fe-reviewer/qa가 `git grep -n "찾을 수 없어요\|매장으로\|불러오지 못했어요" -- src/pages`가 0건인지로 확인**]) / 500 → 불러오기 오류 + 「다시 시도」 → `findById` 재호출 / 저장 성공 → `/owner/store`로 이동 / `:productId`가 `findById`에 전달됨.

### 9.8 app
**`tests/app/router/routes.test.tsx`(기존 변경)**: 자리 page 제목 단언 3건을 교체한다. `/owner/store` 행: 「O4 매장」 → 제목 「매장」 + 「상품 …개」 또는 로딩·빈 상태, TabBar 있음. `/owner/products/new`: 제목 「상품 등록」, TabBar 없음. `/owner/products/p1`: 제목 「상품 수정」, TabBar 없음. `/owner/products/new`·`/owner/products/p1`에서 TopNav 활성이 「매장」인 기존 단언은 유지.

**`tests/app/container.test.ts`**: `ProductRepositoryToken`·`ProductCommandsToken`이 `createContainer()`로 풀린다.

**`tests/app/providers/AuthFailureBridge.test.tsx`(C-12, D-27)** — 가짜 `SessionStore`(`hasSession`을 `clear()`에서 `false`로, `save()`에서 `true`로 바꾸는 상태 있는 가짜), `notifyAuthFailure()`를 직접 호출
- 세션 있음 + 첫 401 → `clear()` 1회.
- 같은 세션에서 401이 연속 3번 → `clear()` 총 1회(첫 호출 뒤 `hasSession()`이 false).
- 처음부터 세션 없음 + 401 → `clear()` 호출 없음.
- **재로그인 뒤 두 번째 401**: 첫 401로 `clear()`(1회) → `save('t2')`로 세션 복구 → 두 번째 401 → `clear()` 총 2회(세션 만료 처리됨). 이 케이스는 수정 전 코드에서 실패해야 한다(Red).
- 두 번째 세션 만료 뒤에도 연속 401은 다시 1회만 정리(총 2회 유지).
- 언마운트 후 `notifyAuthFailure()` → `clear()` 호출 없음(핸들러 해제).
- 기존 케이스는 모두 그대로 통과.

**통합: `tests/app/providers/AuthFailureBridge.test.tsx`에 추가**: 실제 `request`를 거치는 `HttpProductRepository`가 `401 UNAUTHORIZED`를 받으면 `SessionStore.clear()`가 1회 불리고, O4가 로그인 화면으로 이동한다(가짜 `fetch`). `403`이면 `clear()`가 불리지 않는다.

**`e2e/products.spec.ts`**(오케스트레이터가 흐름 변경으로 `qa-verification` §4 요청 시): 로그인(상점주) → 매장 → 「+ 상품 등록」 → 이름·가격 입력 → 「등록만」 → 목록에 새 상품이 보임 → 행을 눌러 이름 수정 → 저장 → 목록에 반영 → 「숨기기」 → 목록에서 태그 「숨김」.

### 9.9 4차 테스트 변경 요약 (fe-qa 작업표)

추가 33, 변경 9, 삭제 2. 위 본문의 **[추가]·[변경]·[삭제]** 표시가 정본이고 이 표는 파일별 합계다. `tests/features/products/fakes/*`는 바꾸지 않는다.

| 파일(`tests/` 아래) | 추가 | 변경 | 삭제 |
| --- | --- | --- | --- |
| `features/products/infrastructure/productDto.test.ts` | 5 (`toImageSrc`의 `it.each` 3행: `//evil.example/a.png`·`/\evil.example/a.png`·`//`, 정상 상대 경로 회귀 1, `toProduct`의 `//` 이미지 `src === ''`·`url` 보존 1) | 0 | 0 |
| `features/products/application/usePhotoDraft.test.tsx` | 2 (정상 뒤 gif 검증 실패, 실패 뒤 정상 pick) | 1 (「6MB 파일은 error만 설정하고 이전 상태를 유지한다」 → 이전 사진 버림·revoke) | 0 |
| `features/products/domain/productMessages.test.ts` | 4 (`productLoadFailure` 404·403·500·NETWORK_ERROR) | 1 (「VALIDATION_ERROR(save·create)는 서버 message 그대로」 → 공통 문구) | 0 |
| `features/products/domain/productToggle.test.ts` (신규) | 4 | 0 | 0 |
| `features/products/domain/productPhoto.test.ts` | 0 | 1 (「uploading → uploading」 → 사진 없이 uploading이면 empty) | 0 |
| `features/products/application/toggleProduct.test.ts` | 3 | 0 | 0 |
| `features/products/application/useToggleProduct.test.tsx` | 0 | 1 (`it.each` ALREADY_* 두 행: `null` → `Product` resolve, `idle`) | 0 |
| `features/products/application/useSaveProduct.test.tsx` | 0 | 1 (「VALIDATION_ERROR 400이면 서버 message가 errorMessage가 된다」 → 공통 문구) | 0 |
| `features/products/application/useCreateProduct.test.tsx` | 1 (VALIDATION_ERROR → 공통 문구) | 0 | 1 (「cancel()은 signal을 abort하고 idle로…」) |
| `features/products/application/useProduct.test.tsx` | 4 (`failure` null / 404 / 403 / 500) | 0 | 0 |
| `features/products/presentation/ProductCreateForm.test.tsx` | 4 (사진 없이 제출 중 「올리는 중…」·「취소」 없음·empty 유지 / 이전 사진 버린 뒤 제출 시 `null` / 검증 실패 뒤 정상 사진 복구 / 제출 중 언마운트 abort) | 2 (「6MB 파일을 고르면 사진 칸이 failed(…)」 — 「다시 시도」 없음·제출 `null`, 「두 버튼이 「처리 중…」·aria-disabled, 사진 칸은 「올리는 중…」+「취소」…」 — 취소 없음) | 1 (「「취소」를 누르면 signal이 abort되고…」) |
| `features/products/presentation/ProductEditForm.test.tsx` | 2 (ALREADY_INACTIVE·ALREADY_ACTIVE) | 1 (「저장 실패(VALIDATION_ERROR): .err에 서버 문구…」 → 공통 문구) | 0 |
| `features/products/presentation/PhotoField.test.tsx` | 1 (`onRetry` 없으면 「다시 시도」 없음) | 1 (「uploading: 「올리는 중…」과 「취소」가 있고…」 → 취소 없음, `renderField`에서 `onCancel` 제거) | 0 |
| `features/products/presentation/ProductLoadError.test.tsx` (신규) | 3 | 0 | 0 |
| `pages/product-edit/ProductEditPage.test.tsx` | 0 (기존 단언이 그대로 통과해야 함) | 0 | 0 |

합계: 추가 5+2+4+4+3+1+4+4+2+1+3 = 33, 변경 1+1+1+1+1+2+1+1 = 9, 삭제 2.

### 9.10 5차 테스트 변경 요약과 실측 항목

| 파일(`tests/` 아래) | 추가 | 변경 | 소유 |
| --- | --- | --- | --- |
| `features/products/presentation/ProductCreateForm.test.tsx` | 2 (D-37 데스크톱 「등록만」, D-38 인라인 `style.flex`) | 0 | fe-qa(Red) → products fe-developer |
| `shared/ui/Button.test.tsx` | 1 (`style` 전달) | 0 | fe-qa → shared fe-developer |
| `widgets/owner-nav/presentation/OwnerAccountRows.test.tsx` | (위 [frontend-e9 담당] 4건) | 기존 단언 조정 | **frontend-e9 세션** |
| `pages/owner-store/OwnerStorePage.test.tsx` | 0 | 1 (`.mob` 안 단언, 중복이면 생략 가능) | frontend-e9 또는 fe-qa |

**fe-qa 실측 항목(jsdom 불가, `qa-verification` §4.1):**
1. 360px O6: 하단 CTA 「등록하고 할인 만들기」가 한 줄(줄바꿈 없음), 「등록만」은 내용 폭(`flex: 0 0 auto`). 기준 스크린샷 `layout-qa/round2/shots/O6-mobile.png`. 한 줄이 안 되면 C-16.
2. 1024px O6: `.cta` 숨김, 오른쪽 열에 「등록만」(기본)·「등록하고 할인 만들기」(pri)가 세로로 보이고 둘 다 동작(E2E: 「등록만」 → 목록에 새 상품).
4. 1280px O4: 「영업 중」 칩이 내용 폭만 차지하고(패널 폭 전체로 늘어나지 않음) 360px에서도 같다. 기준 `round3/shots/O4-desktop.png`.
5. 360px·1280px O4: 상품 목록 마지막 줄과 「상점 폐점」 사이에 `--s3` 간격이 있고(모바일은 계정 행 사이도), 링크 클릭 영역이 열 폭 전체가 아니다. 기준 `O4-mobile.png`·`O4-desktop.png`.
3. 1024px O4: 「계정」 라벨·「비밀번호 변경」·「로그아웃」이 보이지 않고 오른쪽 위 「계정」 버튼만 보인다. 360px에서는 보인다.

## 10. 남길 작업 주석 (`code-annotations` §1~§3)

| ID | 위치 | 태그 | 주석 |
| --- | --- | --- | --- |
| N-1 | `features/products/domain/productMessages.ts` | TODO | `// TODO: 임시 문구다(상품 오류 문구, 빈 상태 문구, 숨기기 거절 안내, 「상품을 찾을 수 없어요.」 등).`<br>`//   왜: 정본 문구가 없다 (docs/design/frontend/products.md D-4, D-16)`<br>`//   언제: 결정 후 (사용자·디자인 시스템: content.md에 상품 문구 확정)` |
| N-2 | `features/products/infrastructure/httpProductRepository.ts` `findByStore` | TODO | `// TODO: 상품을 한 번에 100개까지만 불러온다. 101번째부터는 목록에 나오지 않는다.`<br>`//   왜: O4 명세에 더 보기·페이지 규칙이 없다 (docs/design/frontend/products.md D-15)`<br>`//   언제: 결정 후 (사용자: 상품 100개 초과 처리)` |
| N-3 | `features/offers/domain/offer.ts` `Offer` 타입, `features/offers/domain/offerFormat.ts` `formatWon` | TODO | `// TODO: 상품 정보(productId·productName·originalPrice)와 금액 표기가 entities/product의 Product·formatProductPrice와 겹친다.`<br>`//   왜: products가 entities/product를 만들었다 (docs/design/frontend/products.md D-7, §1.1)`<br>`//   언제: O3 구현 시` — `features/offers` 소유 `fe-developer`가 이번 구현에서 **주석만** 추가(코드 변경 없음) |
| N-4 | (O11 사진 재설계 때) `ProductEditForm.tsx` 사진 처리 | 이번 차수 주석 없음 | 사진이 2장 이상이면 첫 사진만 다룬다는 규칙(D-6 확정)은 O11 사진 구현 때 코드와 함께 정한다. 이번 차수에는 N-10이 대신한다 |
| N-5 | `features/products/presentation/PhotoField.tsx` 업로드 중 표시 | 일반 주석 | 확정(D-11): `// 업로드 진행률은 보이지 않고 「올리는 중…」만 보인다 (products.md D-11, 사용자 확정)`. TODO·FIXME가 아님(고칠 일 없음) |
| N-10 | `features/products/presentation/ProductEditForm.tsx` 사진 칸 | FIXME | `// FIXME: 사진을 바꾸거나 지울 수 없다. 사진은 읽기 전용으로만 보인다.`<br>`//   왜: 사용자 결정으로 이번 차수에서 사진은 보기만 한다 (docs/design/frontend/products.md §0.1 B-1, D-12)`<br>`//   언제: 다음 차수(O11 사진 바꾸기·삭제 구현 시), 늦어도 배포 전` |
| N-6 | `features/products/presentation/ProductCreateForm.tsx` | open-issues | `// open-issues: O12 사진 1장 제한은 화면에서만 지킨다 (백엔드 제한 없음)` (D-6 확정이라 정본 갱신 뒤 지운다) |
| N-7 | `features/products/application/useToggleProduct.ts` 숨기기 | open-issues | `// open-issues: O11 숨기기 확인 단계 없음, 진행 중 할인으로 서버가 거절하면 안내만 보인다 (사용자 결정 products.md D-3)` (4차: 이미 숨김·노출 응답을 성공으로 처리하는 것은 D-33이며 open-issues 항목이 아니라 주석 불필요) |
| N-12 | `pages/product-edit/presentation/ProductEditPage.tsx` | **삭제** | 3차까지 있던 `TEXT` 상수 위의 TODO(임시 문구)를 상수와 함께 지운다. 같은 TODO는 `productMessages.ts` N-1이 이미 가진다(C1) |
| N-8 | `features/products/domain/productChanges.ts` `category` 비우기 | **주석 없음(삭제)** | 명세 §5(`e3abeae`)에 `null` = 비우기가 반영되어 C-5가 해소됐으므로 TODO를 남기지 않는다. 2차안에 있던 이 행의 TODO는 쓰지 않는다 |
| N-11 | `app/providers/AuthFailureBridge.tsx` | 없음 | 수정 후 `cleared` 관련 주석을 새 방식(세션 유무)에 맞게 고친다. 한계(옛 토큰 늦은 401)는 일반 주석 한 줄(§7.1) |
| N-9 | `widgets/owner-nav/presentation/OwnerAccountRows.tsx` | **폐기(5차)** | 주석 없음. 이 TODO의 전제("모바일만 보이게 하는 클래스가 없다")가 틀렸고(`.mob` 있음), D-19가 모바일 전용으로 재결정돼 `OwnerAccountRows.tsx`에 남아 있다면 **지운다**(frontend-e9 세션이 `.mob` 래핑과 함께) |
| 삭제 | `features/auth/application/useAuthController.ts:12~14` FIXME | | 같은 커밋에서 지운다(§7, C-7) |
| 수정 | `app/router/placeholders.tsx` 머리 TODO | | `언제:`에서 `O4 구현 시, O6 구현 시, O11 구현 시`를 뺀다 |

## 11. 결정 표

| D-번호 | 항목 | 값 | 임시/확정 | 근거 |
| --- | --- | --- | --- | --- |
| D-1 | 상품 등록 + 사진 | `POST /v1/stores/{id}/products` multipart 한 요청(사진 0~1장). 둘 중 하나라도 실패하면 둘 다 롤백(서버) | **확정** | 사용자(발주서 D-a), `reference/catalog.md` §1 |
| D-2 | 상점 상품 목록 `is_active` | 미지정으로 요청. 본인 상점이면 노출·숨김 모두 | **확정** | 사용자(발주서 D-b), `reference/catalog.md` §2 |
| D-3 | O11 숨기기 확인 단계 | 없음. 누르면 바로 숨기고 「다시 보이기」로 바뀜. 진행 중 할인으로 서버가 거절(400 `PRODUCT_HAS_OPEN_OFFER`)하면 안내 문구 표시 | **확정** | 사용자(발주서 D-c). `open-issues.md` O11 "확인 필요" 해소(C-6) |
| D-4 | 숨기기 거절 안내 문구 | 「진행 중인 할인이 있어 숨길 수 없어요. 판매를 중단한 뒤 다시 숨겨 주세요.」 | **확정(적용 승인)** — 사용자가 이 임시 문구 적용을 승인("제안대로 적용"). 최종 문구는 미확정이라 N-1 TODO를 유지 | 명세에 없음. 사용자 2026-11-11(Q-3 해소) |
| D-5 | O6 「등록하고 할인 만들기」 | 등록 성공 후 O3 경로로 이동(지금은 자리 page). O3 구현 시 그대로 이어진다 | **확정** | 사용자(발주서 D-d) |
| D-6 | 사진 1장 규칙 | 화면에서만 막는다(백엔드 제한 없음). 화면은 첫 사진 1장만 다루고 나머지는 건드리지 않는다 | **확정**(2장 이상 처리 포함, Q-7 해소) | 사용자(발주서 D-e), 사용자 2026-11-11. 첫 사진 처리 코드는 O11 사진(B-1) 때 구현 |
| D-7 | `entities/product` | 이번에 만든다(타입·규칙·읽기 포트·토큰). 재사용처와 `features/offers` 중복은 §1.1·N-3 | **확정** | 사용자(발주서 D-f) |
| D-8 | page slice 이름 | `owner-store`(O4), `product-new`(O6), `product-edit`(O11). O12는 slice 없음 | 임시 | `fsd-structure` §5(뜻으로 이름) |
| D-9 | O3로 상품 넘기는 방법 | `ROUTES.ownerOfferNewFor(id)` = `/owner/offers/new?productId=<id>`. O3 설계에서 읽는 방식을 확정한다 | **확정** | 사용자 2026-11-11(Q-5 해소) |
| D-10 | 상품 등록 요청 형식 | 사진 유무와 관계없이 항상 multipart(코드 경로 하나) | 임시 | 서버가 두 형식을 받는다(`catalog.md` §1) |
| D-11 | 사진 업로드 시점과 표시 | 파일은 화면에 보관하고 미리보기만 보인다. 업로드는 「등록」을 누를 때 이뤄지며, 그동안 **사진이 있을 때만** 사진 칸이 「올리는 중…」(진행률 없음)이다. 사진 없이 등록하면 사진 칸은 그대로다. **등록 중 「취소」 버튼은 없다**(abort해도 서버에 상품이 이미 생길 수 있어 재등록 시 중복 위험, fe-reviewer 지적). 언마운트 abort(F10)는 유지. 알려진 한계: 등록 중 화면을 떠나면 서버에는 상품이 생겼는데 화면은 모를 수 있다 | **확정**(4차 개정) | 사용자 2026-11-11(C-1, Q-9 해소; 4차 B2로 「취소」 제거·사진 있을 때만). C-13 |
| D-12 | O11 사진 바꾸기·삭제 | **이번 차수 보기만, 바꾸기·삭제는 다음 차수에 재설계.** 사진 보존 백엔드 요청이 취소됐다(`../catalog.md` 17절, `../reservations.md` 17절). 현행 백엔드는 PATCH·DELETE로 빠진 업로드 사진 바이트를 지운다(`service.py:251-252`, `270-278`) | **제외(사용자 결정, 다음 차수 재설계)** | 사용자 2026-11-11. §0.1, Q-12. C-2. 아래 "기존 안 폐기" 사유(보존 요구)는 철회됐으므로 다음 차수에 다시 정한다 |
| D-13 | 저장 실패 시 새로 올린 사진 되돌리기 | 방금 올린(어디에도 쓰이지 않은) 사진만 `DELETE`로 되돌림. O6에는 해당 없음(한 요청 롤백). O11 사진 흐름과 함께 보류 | **제외(다음 차수 재설계)** | 사용자 2026-11-11. O11 사진 흐름과 함께 다음 차수 |
| D-14 | O11 저장·숨기기 뒤 이동 | 저장 성공 → O4로 이동. 숨기기·다시 보이기 → 화면에 남아 칩·버튼만 갱신 | **확정** | 사용자 2026-11-11(Q-1 해소) |
| D-15 | O4 목록 불러오는 양 | `page=1&size=100`. 100개 초과분은 보이지 않는다(개수는 `total`) | **확정** | 사용자 2026-11-11(Q-6 해소). N-2 TODO 유지(명세에 더 보기 규칙 없음) |
| D-16 | 임시 문구 | §4.1 표의 「임시」 문구 전부, 숨김 칩 「숨김」, 「뒤로」(aria-label), 「매장으로」. 4차(C1): 「상품을 찾을 수 없어요.」·「매장으로」·「다시 시도」·불러오기 실패 문구는 `pages/product-edit`가 아니라 `features/products`(`productMessages.ts`, `ProductLoadError`)에 둔다. `PRODUCT_TEXT`·`productErrorMessage`는 공개 API로 내보내지 않는다 | **확정(적용 승인)** — 사용자가 임시 문구 적용을 승인. `content.md`에 최종 문구가 정해진 것은 아니므로 N-1 TODO 유지 | 사용자 2026-11-11(Q-8 해소). 이유: 승인은 "지금 이 문구로 구현"이지 최종 확정이 아니며 `content.md`가 정본(F13) |
| D-17 | `VALIDATION_ERROR` 문구 | **서버 `message`를 표시하지 않는다.** 공통 문구(`saveFailed` 「저장하지 못했어요. 잠시 후 다시 시도해 주세요.」, load는 불러오기 문구)를 쓴다(3차: 서버 message 그대로). 서버 문구가 영어 프레임워크 문구일 수 있다(fe-reviewer 지적) | **확정**(4차 개정) | 사용자 2026-11-11(Q-2 해소 → 4차 A3로 변경). C-3 |
| D-18 | 카테고리·설명 null 처리 | **`null`은 수정(PATCH)에서 카테고리·설명을 비울 때만 보낸다.** 그 밖에는 null을 보내지 않고 필드를 생략한다(등록에서 빈 값은 생략, 수정에서 바뀌지 않은 필드는 생략). DTO·요청 모양 테스트에 단언(§9.3·§9.4) | **확정** | 사용자 2026-11-11(Q-10을 대체). `product.py:50~52`. 명세 §5(`e3abeae`)와 일치: `category`·`description` `null` = 비우기, 보내지 않으면 불변, `category` 빈 문자열은 400이므로 빈 입력은 `null`로 보낸다(C-5 해소) |
| D-19 | O4 계정 행·폐점 링크 | `widgets/owner-nav`에 `OwnerAccountRows`(비밀번호 변경·로그아웃) 추가해 O4에 둔다. **5차 재결정: 모바일에서만 보인다**(`.mob`로 감쌈, PC는 오른쪽 위 「계정」 버튼 O8). 4차까지의 "PC에서도 표시"는 "모바일만 보이게 하는 클래스가 없다"는 잘못된 전제였다(`bundle.css:559` `.mob`). 「상점 폐점」 링크는 stores.md D-12대로 O4에 둔다(모든 폭) | **확정**(5차 개정) | 사용자 2026-11-11 재결정(Q-4, C-9 허용). 근거 `screens.md` O4, `wireframe.html` O4. N-9 폐기. 구현은 frontend-e9 세션 |
| D-37 | O6 데스크톱 「등록만」 | 720px 이상에서 `.cta`가 숨겨져 PC에서 할인 없이 등록할 방법이 없었다(fe-qa E2E). 오른쪽 열에 「등록만」을 `Button desktopOnly`(기본, 보조)로 추가하고 「등록하고 할인 만들기」(`primary desktopOnly`) **앞에** 둔다(보조 → 확정, 세로로 쌓임). 동작·`disabled`·`pending`은 모바일 버튼과 같다. 정본(`wireframe.html` O6)에는 PC 「등록만」이 없다(C-15) | **확정**(5차 보완) | 사용자 2026-11-11(존재, 종류·순서·위치 모두 확정). 배치는 O7 `StoreCloseForm`의 `.dk` 둘(기본 → dark)과 `CtaBar` README(왼쪽 보조 + 오른쪽 확정)를 따름. 정본에 없음(C-15) |
| D-38 | 360px 하단 CTA 줄바꿈 | `.cta .btn { flex: 1 }`이라 두 버튼이 같은 폭을 받아 「등록하고 할인 만들기」가 「만들/기」로 줄바꿈된다. 와이어프레임 O6 `.cta`는 「등록만」에 `style="flex:0 0 auto"`를 준다. 같은 **인라인 스타일**로 처리한다: 모바일 `.cta` 안 「등록만」 `Button`에 `style={{ flex: '0 0 auto' }}`(레이아웃 값 하나, 색·간격 없음, F12 점검 §8)를 주어 내용 폭만 쓰게 하고 주 버튼이 남은 폭(약 230px)을 쓴다. 이를 위해 `shared/ui/Button`에 선택 prop `style?: CSSProperties`를 추가한다(`<button style>`로 전달, 기존 호출 영향 없음, 사용자 승인). 폐기한 안: CSS Module `.fit`+`className` prop(새 컴포넌트 클래스를 만들지 않는다는 F12 위반, 저장소에 CSS Module 없음). 문구는 바꾸지 않는다(`screens.md` 정본, F13). 디자인 시스템 CSS는 고치지 않는다 | **확정**(5차 보완) | 사용자 결정 2026-11-11(CSS Module 안 폐기, 인라인 style 확정). 근거 `wireframe.html` O6 `.cta`(flex:0 0 auto). 실측 실패 시 C-16 |
| D-20 | 공용 기반 변경 | `client.ts` FormData 지원, `Skeleton`·`EmptyState` 추가. 새 `apiPatch` 등은 만들지 않음 | 임시 | stores.md D-4(필요할 때 필요한 것만) |
| D-21 | 401·TOKEN_REVOKED | 새로 만들지 않는다. stores 차수의 `client.ts` → `authFailure` → `AuthFailureBridge`가 products 요청도 덮는다. `useAuthController.ts` FIXME만 지운다 | 임시 | C-7 |
| D-22 | O11 로딩 데이터 | `GET /v1/products/{id}`(숨김 상품도 본인에게 줌, `service.py:459~465`). 목록 데이터를 O4에서 넘기지 않는다(직접 URL 진입·새로고침 대응) | 임시 | C-8. api-map.md에 이 호출이 없음(C-10) |
| D-23 | O12 상태 표기 | 와이어프레임의 「① 사진 고르기」「② 업로드 중」「③ 올라감」「④ 실패」는 섹션 안내 표기로 보고 화면에 그리지 않는다. 상태는 `PhotoSlotPhase`로 구분 | **확정** | 사용자 2026-11-11(Q-11 해소) |
| D-24 | 이미지 `src` 계산 위치 | infrastructure(`toImageSrc`). 상대 경로면 `API_BASE_URL`을 붙이고 `http(s)`만 허용. **`//`로 시작하는 프로토콜 상대 주소는 빈 값(`''`)으로 처리**(A1, 외부 호스트 요청 방지. 설계자 추가: `/\`도 같은 이유로 `''`, 임시). 저장용 `url`은 원본 유지 | 방침 **확정**(A1, 사용자 2026-11-11) / `/\` 포함은 임시 | `catalog.md` §15·§17(상대 경로), F6·F17 |
| D-25 | O12 시트 | 라우트 없는 `Overlay` + `.sheet`. `shared/ui`에 `BottomSheet`를 만들지 않고 `features/products/presentation`에 둔다 | 임시 | stores.md §2.3(products 전용은 만들지 않음) |
| D-26 | 입력 칸 마크업 | `ProductForm`은 `shared/ui/Input`을 쓰지 않고 `label.lbl` + `input.in`(설명은 `textarea.in`)을 **직접 마크업**한다. `Input`은 바꾸지 않는다. 이유: `Input`에 `disabled`가 없어 제출 중 비활성 불가, 라벨 `*` 중복(`PRODUCT_TEXT.create.nameLabel`에 이미 `*`). 다른 화면에서 쓰이면 `shared/ui`로 올린다(3차: `Input` 사용으로 적었던 것을 정정) | **확정**(C2, 사용자 2026-11-11) | fe-architect 구조 점검 지적, 현재 구현 |
| D-27 | `AuthFailureBridge` 재로그인 뒤 401 | `cleared` 플래그를 없애고 `hasSession()`이 true일 때만 `clear()`. 이번 범위에서 고친다(§7.1). 한계: 재로그인 직후 옛 토큰 요청의 늦은 401이 새 세션을 지울 수 있음 | 방침 **확정**(이번 범위에서 고침, C-12) / 수정 방식 임시 | 사용자 2026-11-11, `AuthFailureBridge.tsx:12~16` |
| D-28 | O11 사진 칸(이번 차수) | 사진이 있으면 읽기 전용 미리보기만. 바꾸기·삭제·시트 없음. 없으면 칸을 그리지 않는다 | 임시 | B-1 차단, N-10 FIXME |
| D-29 | 범위 밖 변경 허용 | `widgets/owner-nav`의 `OwnerAccountRows`, `routes.test.tsx` 3행 교체, `app-shell.md` D-4·D-14·§2의 해당 부분 대체(app-shell.md 본문은 고치지 않고 이 문서가 대체 사실을 적음, C-9), `features/offers`·`features/auth` 주석 수정 | **확정** | 사용자 2026-11-11(C-9, C-11) |
| D-30 | `ProductForm` props | 제어 컴포넌트(`mode`, `values`, `errors`, `disabled?`, `onChange`). 필요함: 입력 4칸·`textarea`·`FieldError`가 O6·O11에서 같고 차이는 라벨 `*`뿐이라 중복을 피함. 사진·버튼·제출은 각 폼이 가짐. 골격 단계는 이 파일이 비어 있어도 되며 Green에서 만든다 | 임시 | fe-developer 보고(시그니처 불명), `ProductCreateForm.tsx`·`ProductEditForm.tsx` 골격 |
| D-31 | `PRODUCT_TEXT` | 필요함. `domain/productMessages.ts`에 화면별 중첩 `as const` 객체(§4.1 표의 키). 문구는 정본 있는 것은 그대로, 없는 것은 임시(D-4·D-16). `productCountLabel`·`productErrorMessage`는 함수로 별도 유지. Green이 `PRODUCT_ERROR_TEXT`(폼·사진·상점·저장·불러오기 문구, 임시)와 `photoErrorMessage()`를 추가했고 4차에 `notFound`·`edit.toStore`·`edit.retry`가 더해진다. 모두 공개 API 아님 | 임시 | fe-developer 보고, F13 |
| D-32 | `ProductDto`·`ProductListDto` 타입 export | 허용. `infrastructure/productDto.ts`에서 export하되 `index.ts`로는 내보내지 않는다. 같은 slice 안 infrastructure 테스트가 쓰기 위함. `product_image`는 `string[] \| null`(백엔드 실제 응답, §4.3의 `toProduct` 규칙과 같음). presentation·application에서 import하면 F9 위반 | 임시 | F9, fe-developer 보고 |
| D-33 | `PRODUCT_ALREADY_INACTIVE`·`PRODUCT_ALREADY_ACTIVE` | **성공으로 처리**: 이미 원하는 상태이므로 칩·버튼을 그 상태로 바꾼다. `toggleProduct`가 `productWhenAlready`로 그 상태의 `Product`를 resolve하고 `useToggleProduct.toggle`은 그것을 돌려준다(`null` 아님). `ProductEditForm`은 변경 없이 `setActive(next.isActive)`. 3차의 "`null` 반환 + 화면 reload"(§4.2 구 문구)는 폐기. 훅 시그니처 불변·의미 변경, `useProductRun`의 `quiet` 옵션 제거 | **확정** | 사용자 2026-11-11(B1). C-14 |
| D-34 | 사진 검증 실패 처리 | 검증 실패(`usePhotoDraft.pick`)는 이전 사진·미리보기를 버리고 사진 칸을 비운 채 `failed`(오류 문구)로 보인다(A2). 「다시 시도」는 사진이 칸에 있는 서버 거절(`IMAGE_TOO_LARGE`·`UNSUPPORTED_IMAGE_TYPE`)일 때만 준다. 이를 위해 `PhotoField`는 `onRetry`가 있을 때만 「다시 시도」를 그린다(전: 항상) | 비움은 **확정**(A2), 「다시 시도」 숨김은 **임시**(설계자 추가: 비운 뒤 「다시 시도」가 사진 없이 조용히 제출되는 것을 막으려는 것) | 사용자 2026-11-11(A2), fe-reviewer 지적 |
| D-35 | O11 불러오기 오류 문구 위치 | `useProduct`가 `failure: ProductLoadFailure \| null`(`notFound`·`loadFailed` + 문구)을 함께 돌려주고, `features/products`의 공개 컴포넌트 `ProductLoadError`가 「매장으로」「다시 시도」까지 그린다. `ProductEditPage`의 `TEXT` 상수는 삭제. `PRODUCT_TEXT`·`productErrorMessage`는 공개 API로 내보내지 않는다 | 방침 **확정**(C1) / 컴포넌트 위치·이름·버튼 문구 위치는 **임시** | 사용자 2026-11-11(C1), fe-architect 구조 점검 O11 문구 중복 지적 |
| D-36 | `useProductRun` | create·save·toggle이 공유하는 내부 훅(비공개). 중복 제출 방지·언마운트 abort·`readErrorInfo` 사용. `cancel`·`quiet` 제거(B2·B1) | 임시 | fe-architect 구조 점검(설계안 누락) |

## 12. 정합 이슈 · 차단 이슈 · 질문 목록

### 12.1 정합 이슈 (임의로 고르지 않음)

| C-번호 | 내용 | 양쪽 근거 |
| --- | --- | --- |
| C-1 | O6은 "업로드가 끝나기 전에는 등록 버튼 비활성", O12는 업로드 진행률 62%·「취소」를 말한다. 확정 D-1은 등록과 사진을 한 요청으로 보내므로 "등록 전에 업로드가 끝나는 단계"가 없고 `fetch`는 업로드 진행률을 주지 않는다. 설계는 D-11(제출 중 「올리는 중…」·「취소」)로 해석했다. **해소: 사용자가 D-11 확정**(진행률 없음). 디자인 시스템 문서 갱신은 프론트가 하지 않음 | `screens.md` O6 동작 메모(431~432줄)·O12 `wireframe.html:816~830` ↔ 사용자 결정 D-1, `reference/catalog.md` §1 |
| C-2 | 사진 바꿀 때 "새 사진 업로드 후 예전 사진 `DELETE`"(open-issues O12 ③)인데, 명세는 `PATCH`로 `product_image`에서 업로드 주소를 빼도 같은 요청 안에서 파일이 지워진다고 한다. 설계 1차는 필드 변경과 한 요청으로 끝나는 `PATCH`였다. **갱신: 사진 보존 백엔드 요청은 사용자가 취소했다(`e3abeae`, `../catalog.md` 17절). 현행 동작(바이트 삭제)이 유지되고, O11 사진 바꾸기·삭제는 이번 차수 제외(B-1)이며 D-12는 다음 차수에 재설계한다.** 추가 근거: `service.py:251-252`(PATCH가 바이트 삭제), `service.py:270-278`(DELETE도 삭제), `reservations/`에 사진 참조 0건 | `open-issues.md:17` ③, `screens.md` O12 ↔ `reference/catalog.md` §16(`PATCH` 안내), `backend/src/catalog/domain/product.py:135~138` |
| C-3 | **해소(e3abeae)**: §4·§5·§6·§6-1 에러 표에 `error_code` 열이 추가됐고 코드와 일치한다(숨기기 `PRODUCT_HAS_OPEN_OFFER`·`PRODUCT_ALREADY_INACTIVE`, 재노출 `STORE_CLOSED`·`PRODUCT_ALREADY_ACTIVE`, 권한 `FORBIDDEN` 403, `NOT_FOUND` 404, 가격·이미지 오류는 모두 `VALIDATION_ERROR`). 설계의 `errorCode` 분기·문구 표(§4.1)·테스트와 맞는다. 이전 내용: 에러 표에 `error_code` 열이 없었다. 코드는 숨기기 거절 `PRODUCT_HAS_OPEN_OFFER`, 이미 숨김 `PRODUCT_ALREADY_INACTIVE`, PATCH 가격 오류는 일반 `VALIDATION_ERROR`(코드로 구분 불가) | `reference/catalog.md` §5·§6 ↔ `domain/exceptions.py:48~57`, `domain/product.py:121,171` |
| C-4 | O11 안내문 "숨기면 이 상품으로 새 할인을 올릴 수 없고, 고객 목록에서 이 상품의 할인이 빠져요"는 진행 중 할인이 이미 있는 상품은 서버가 숨기기를 거절한다는 사실과 어긋난다(숨겨지는 시점에 빠질 진행 중 할인이 없음). 와이어프레임 문구를 그대로 쓰되(F13) 사용자 확인이 필요하다 | `wireframe.html:803~806` ↔ `service.py:288~297`, `reference/catalog.md` §6 |
| C-5 | **해소(e3abeae)**: 명세 §5가 `category`·`description` `string | null`, `null` = 비우기를 적었다. 이전 내용: `category`·`description`을 비우려면 `PATCH`에 `null`을 보내야 하는데 명세 §5는 string만 적는다. 백엔드는 `category: null`을 받는다 | `reference/catalog.md` §5 요청 본문 ↔ `product.py:50~52,115~117` |
| C-6 | `open-issues.md` O11 "숨길 때 진행 중 할인·예약이 어떻게 되는지 확인 후 확인 단계 추가(확인 필요)"는 사용자 결정 D-3으로 해소됐다. O12 ②("백엔드에서도 막을지는 확인 필요")는 D-6으로 해소됐다. 디자인 문서 갱신 필요(프론트가 쓰지 않음) | `../../design-system/open-issues.md:16~17`, `screens.md` O11·O12 |
| C-7 | stores.md §10은 `useAuthController.ts` FIXME 삭제를 약속했으나 남아 있고(`useAuthController.ts:12~14`), 401 연결은 이미 구현돼 FIXME 문구("공용 훅이 없다")가 낡았다 | `../frontend/stores.md` §10 마지막 행·§2.2 ↔ `src/features/auth/application/useAuthController.ts:12~14`, `shared/api/client.ts:35~44` |
| C-8 | **해소(e3abeae)**: 명세 §4가 숨김 상품은 상점주 본인에게만 응답하고 비소유자는 404(`NOT_FOUND`)라고 적었다. O11의 404·403 처리(§5)와 맞는다. 이전 내용: 명세 §4 `GET /v1/products/{id}`는 "공개"이고 404 한 가지만 적지만, 코드는 숨김 상품을 상점 소유자에게는 준다. O11이 이 동작에 의존한다(D-22) | `reference/catalog.md` §4 ↔ `service.py:459~465` |
| C-9 | `app-shell.md` D-4·D-14는 O4 계정 행을 "자리만"으로 두었고 `app-shell.md` §2 라우트 표는 O4·O6·O11을 자리 page로 적는다. 이번에 O4 계정 행을 채우고 자리 page를 교체하므로 app-shell.md의 해당 행과 `routes.test.tsx:23,32,33`을 바꿔야 한다(app-shell.md 수정은 이 설계자가 하지 않음). **허용됨(사용자, D-29). 대체 사실: ① `app-shell.md` D-4·D-14의 "O4 계정 행은 자리만"은 이 문서 D-19(`OwnerAccountRows`로 O4에 채움)로 대체. ② `app-shell.md` §2 라우트 표(:111,:121)의 O4·O6·O11 "자리 page"는 `OwnerStorePage`·`ProductNewPage`·`ProductEditPage`로 대체(§6). ③ `routes.test.tsx:23,32,33` 단언 3행 교체(§9.8). 반영 위치: app-shell.md는 오케스트레이터가 고칠지 사용자와 정한다** | `app-shell.md:30~32,111,121` ↔ 이 설계안 §5·§6·D-19 |
| C-10 | `api-map.md`의 O11 행은 `PATCH · deactivate · activate`만, O6 행은 `POST …/products`만 적는다. 설계가 쓰는 `GET /v1/products/{id}`(O11 로딩)·`GET /v1/stores/{id}/products`(O4는 있음)·`POST …/images`(O11 사진 교체, O12 행에만 있음)가 O11·O6 행에 없다 | `api-map.md:31·33·37·38` ↔ 이 설계안 §4.3 |
| C-11 | 요청 범위를 넘은 추가: `widgets/owner-nav` 변경(`OwnerAccountRows`), `features/offers`·`features/auth`의 주석 수정, 기존 `tests/app/router/routes.test.tsx` 변경. 모두 주석·위젯 한 부품·기존 테스트 3행 교체다. **허용됨(사용자, D-29)** | 발주서 §1 범위 |
| C-12 | `AuthFailureBridge`의 `cleared` 플래그가 한 번 true가 되면 같은 마운트 안에서 다시 로그인한 뒤의 두 번째 세션 만료를 정리하지 못한다(`App`은 로그인 사이에 다시 마운트되지 않음). products 때문에 생긴 문제는 아니지만 첫 보호 API 화면인 O4부터 자주 드러난다. **갱신: 사용자가 이번 범위에서 고치기로 함(D-27). 수정 방식·쓰기 범위·테스트는 §7.1, §9.8** | `app/providers/AuthFailureBridge.tsx:11~18` ↔ `App.tsx:14` |
| C-13 | 디자인 문서는 업로드 중 사진 칸에 「취소」를 둔다(O12 ②, 와이어프레임). 4차 결정(B2)은 등록 중 「취소」를 없앤다(abort해도 서버에 상품이 생길 수 있어 재등록 시 중복 위험). 프론트는 디자인 시스템 문서를 고치지 않는다 | `screens.md` O12·`wireframe.html:816~830` ↔ 이 설계안 D-11(4차). 디자인 문서 갱신은 소유자 몫(질문 아님, 보고만) |
| C-15 | 정본에 O6 데스크톱 「등록만」이 없다. `wireframe.html` O6 오른쪽 패널의 `.dk` 버튼은 「등록하고 할인 만들기」 하나이고 「등록만」은 모바일 `.cta`에만 있다. 프론트는 디자인 시스템을 고치지 않으므로 D-37(사용자 확정)대로 PC에 「등록만」을 더하고 배치는 임시로 한다. 정본 갱신(wireframe O6 `.dk` 추가)은 소유자 몫(질문 아님, 보고만) | `wireframe.html:722`·`:725`, `screens.md` O6(버튼: 둘) ↔ D-37 |
| C-16 | `.btn`에 `white-space: nowrap`이 없고 `.cta .btn`은 `flex: 1`이다. 좁은 폭(360px)에서 긴 문구 버튼이 줄바꿈될 수 있고 이는 정본 CSS의 성질이다. D-38은 와이어프레임의 `flex:0 0 auto` 처리로 풀되, fe-qa 실측(§9.10-1)에서 360px에 한 줄이 안 되면 정본 변경(`.cta .btn`에 `white-space: nowrap` 등)이 필요하다. 프론트는 `bundle.css`를 고치지 않으므로 그때는 정본 소유자에게 요청하고 프론트 쪽은 D-38 그대로 둔다 | `bundle.css:117~131`(`.cta`), `:211~226`(`.btn`) ↔ D-38, `O6-mobile.png` |
| C-14 | 명세는 숨기기·재노출 오류 `PRODUCT_ALREADY_INACTIVE`·`PRODUCT_ALREADY_ACTIVE`를 400 오류로 적는다. 프론트는 이를 "이미 원하는 상태"라서 성공으로 처리한다(D-33). 명세·백엔드 변경은 없다 | `reference/catalog.md` §6·§6-1 ↔ D-33 |

### 12.2 차단 이슈

| B-번호 | 내용 | 차단 범위 | 풀리는 조건 |
| --- | --- | --- | --- |
| B-1 | O11 「사진 바꾸기」「사진 삭제」: **사용자 결정으로 이번 차수 제외**(2026-11-11, 확정). 사진 보존 백엔드 요청이 취소되어(`e3abeae`) 백엔드 변경을 기다리는 것이 아니다. O11 사진은 보기만 한다 | §0.1 표(파일·심볼·테스트 경계, 변경 없음). O6 등록·O11 사진 외 수정·숨기기·다시 보이기는 대상 아님 | 다음 차수에 사진 교체 방식을 재결정(Q-12) → D-12·D-13 재설계 |

그 밖의 구현을 막는 결정은 없다.

### 12.3 질문 목록

Q-1~Q-11은 사용자가 2026-11-11에 제안(임시값)대로 확정해 모두 **해소**됐다. 새 질문 1건(Q-12, 이번 차수 구현을 막지 않음).

| Q-번호 | 상태 | 질문 |
| --- | --- | --- |
| Q-12 | 열림(다음 차수) | O11 사진 바꾸기·삭제를 다음 차수에 설계할 때, 이전 사진 보존 요구는 철회된 채 현행 동작(교체·삭제 시 파일 삭제, D97)을 받아들이는가, 아니면 다시 정하는가? 확인 필요 |

| Q-번호 | 상태 | 결과 |
| --- | --- | --- |
| Q-1 | 해소 | D-14 확정 |
| Q-2 | 해소 | D-17 확정 |
| Q-3 | 해소 | D-4 확정(임시 문구 적용 승인, 최종 문구는 N-1로 남김) |
| Q-4 | 해소(재결정, 5차) | D-19 확정: 모바일 전용(`.mob`), N-9 폐기. 4차의 "PC에서도 표시"는 대체됨 |
| Q-5 | 해소 | D-9 확정 |
| Q-6 | 해소 | D-15 확정(N-2 유지) |
| Q-7 | 해소 | D-6 확정(첫 장만. 코드는 B-1 뒤) |
| Q-8 | 해소 | D-16 확정(임시 문구 적용 승인, 최종 문구는 N-1로 남김) |
| Q-9 | 해소 | D-11 확정 |
| Q-10 | 해소(대체) | D-18 확정: null은 비우기에서만 |
| Q-11 | 해소 | D-23 확정 |

## 13. 구현 순서 제안 (오케스트레이터용)

`tdd-workflow` 순서로 아래 계층부터: ① `shared`(`client.ts` FormData, `Skeleton`·`EmptyState`, `routes`) → ② `entities/product` → ③ `features/products`(domain → application → infrastructure → presentation, `wiring.ts`) → ④ `widgets/owner-nav`(`OwnerAccountRows`) → ⑤ `pages/owner-store`·`product-new`·`product-edit` → ⑥ `app`(라우트·container·placeholders) + `useAuthController.ts` FIXME 삭제, `features/offers` 주석 추가, ⑦ `AuthFailureBridge` 수정(§7.1, 독립이라 ①과 병렬 가능). `[차단 B-1]` 항목은 맡기지 않는다. O11 사진 칸은 읽기 전용 + N-10 FIXME로 마친다. ①과 ②는 병렬 가능, ③은 ② 뒤, ④는 ③과 병렬 가능. 쓰기 소유권은 slice별 `fe-developer` 한 명, 공용 파일(`routes.ts`·`container.ts`·`placeholders.tsx`·`routes.test.tsx`)은 오케스트레이터가 조정한다.
