# Template Extractor 개선 계획서

## 목표

현재 `/template/upload` 추출 결과가 원본 PPT 템플릿의 구조를 충분히 보존하지 못하는 문제를 해결한다.

핵심 목표는 다음과 같다.

1. 원본 PPT의 **레이아웃 구조**를 최대한 유지한 채 `elements.json` 계약으로 변환한다.
2. 원본 슬라이드 크기가 `13.33 x 7.5`가 아니어도 **비율 기반 좌표 정규화**로 안정적으로 추출한다.
3. 현재 누락되는 `GROUP`, `line`, `FREEFORM` 계열을 처리해 템플릿 적용 결과의 붕괴를 줄인다.
4. LLM 없이 동작하는 **순수 parser pipeline**으로 유지한다.

---

## 현재 상태 정리

`/template/upload` 경로는 현재 LLM을 호출하지 않는다.

- 업로드 파일 저장
- `TemplateExtractor.extract()` 호출
- 추출 JSON 저장

즉, 현재 문제는 생성 문제가 아니라 **파싱/정규화 문제**다.

---

## 실제 문제 원인

### 1. 원본 슬라이드 크기를 무시하고 있음

현재 extractor는 EMU를 inch로 바꾼 뒤, 곧바로 현재 시스템 캔버스 `13.33 x 7.5`에 clamp 한다.

이 방식은 원본 PPT가 `20 x 11.25` 같은 다른 크기일 때 좌표가 틀어진다.

필요한 방식은 다음이다.

- 원본 `prs.slide_width`, `prs.slide_height`를 먼저 읽는다.
- 모든 좌표를 원본 비율 기준으로 정규화한다.
- 마지막에만 타깃 캔버스 `13.33 x 7.5`에 맞춘다.

### 2. `GROUP`을 통째로 버리고 있음

현재 extractor는 `GROUP`을 무시한다.

하지만 실제 템플릿에서는 그룹 안에 다음 요소가 자주 들어 있다.

- 텍스트 박스
- 장식용 freeform
- 구획용 line

즉, 그룹을 버리면 템플릿 골격이 대량으로 사라진다.

### 3. `line`을 전혀 처리하지 못함

실제 샘플 PPTX 스캔 결과, `line`이 다수 존재한다.

- 로컬 샘플 기준 `line`: 185개

구분선, 분할선, 프레임 라인, 섹션 경계가 많아서 이 요소가 빠지면 디자인이 눈에 띄게 무너진다.

### 4. `FREEFORM`이 많이 쓰이지만 현재 전부 버림

실제 샘플 PPTX 스캔 결과, `FREEFORM`도 다수 존재한다.

- 로컬 샘플 기준 `FREEFORM`: 158개
- 이 중 `PICTURE` fill: 98개
- 이 중 `SOLID` fill: 60개

이 freeform은 성격이 둘로 갈린다.

- 이미지 마스크/장식 역할
- 채워진 배경판/탭/강조 조각 역할

둘을 같은 방식으로 처리하면 안 된다.

### 5. 현재 `elements.json` 표현력이 부족함

현재 계약은 다음만 지원한다.

- `text_box`
- `shape`
- `bullet_list`

그리고 `shape.shape_type`도 다음만 허용한다.

- `rectangle`
- `round_rectangle`

즉, 현재 계약으로는 `line`조차 직접 표현할 수 없다.

---

## 변경 범위 결정

이번 변경에서 반영할 항목은 아래와 같이 확정한다.

### 확정

- `line` 타입 추가
- `GROUP` 재귀 추출
- 원본 슬라이드 크기 기준 **비율 좌표 정규화**
- `FREEFORM` 정규화 처리
- 추출 로그/디버그 정보 보강
- 기존 템플릿 JSON 재추출

### 보류

- `ellipse` 타입 추가 보류

사유:

- 현재 로컬 샘플 PPTX에서는 ellipse 사용 흔적이 거의 없다.
- 지금 당장 추가하지 않아도 실제 품질 향상에 미치는 영향이 낮다.

### 반려

- `image` 타입 추가 반려

사유:

- 현재 템플릿 파이프라인의 목표는 텍스트/패널 기반 레이아웃 재사용이다.
- 이미지까지 타입을 확장하면 계약, 렌더러, 적용 단계 모두가 커진다.
- 이번 수정의 우선순위는 레이아웃 복원이며, 이미지는 범위 밖이다.

### `FREEFORM`에 대한 결정

`FREEFORM`은 **새 타입을 추가하지 않는다**.

대신 extractor에서 아래 규칙으로 **기존 지원 타입으로 정규화**한다.

- 얇고 긴 freeform: `line`으로 변환
- 채워진 solid freeform: `shape`로 변환
- 텍스트가 있는 freeform: `text_box` 또는 `bullet_list`로 변환, 필요 시 배경 `shape` 추가
- picture-filled freeform: skip

즉, `FREEFORM`은 많이 쓰이지만 **새 계약 타입으로 확장할 필요는 아직 없다**.

---

## 계약 변경 계획

### 파일

- `fastapi-app/elements.json`
- `fastapi-app/app/schemas/generate.py`
- `fastapi-app/app/services/pptx_service.py`

### 새 element 타입 추가

`line` 타입을 계약에 추가한다.

권장 스키마는 다음과 같다.

```json
{
  "type": "line",
  "x": 0.9,
  "y": 1.7,
  "w": 11.0,
  "h": 0.0,
  "line_color": "#D9D9D9",
  "line_width": 1.5
}
```

설계 이유:

- 현재 시스템은 `x, y, w, h` 좌표 구조를 중심으로 동작한다.
- 실제 샘플의 line은 대부분 수평/수직 구분선이다.
- `x, y, w, h`로도 충분히 표현 가능하다.

### 스키마 변경

`app/schemas/generate.py`에 `LineElement`를 추가한다.

예상 구조:

```python
class LineElement(BaseModel):
    type: Literal["line"] = "line"
    x: float
    y: float
    w: float
    h: float
    line_color: str = "#D9D9D9"
    line_width: float = 1.0
```

검증 규칙:

- `w == 0 and h == 0` 는 불가
- `w` 또는 `h` 중 하나가 0인 것은 허용
- 캔버스 범위는 유지

주의:

기존 `PositionedElement` 검증은 `w <= 0 or h <= 0`를 막고 있으므로, `LineElement`는 별도 검증 로직이 필요하다.

### 렌더러 변경

`app/services/pptx_service.py`에 `line` 렌더링을 추가한다.

처리 방식:

- `MSO_AUTO_SHAPE_TYPE.LINE` 사용
- `line_color`, `line_width` 반영
- `x, y, w, h`를 그대로 line bounding box로 사용

---

## 추출기 변경 계획

### 파일

- `fastapi-app/app/services/template_extractor.py`

### 1. 원본 슬라이드 크기 기반 비율 정규화

지금 방식:

- EMU -> inch
- 바로 `13.33 x 7.5` clamp

변경 방식:

1. 원본 슬라이드 크기 읽기
2. 원본 좌표를 원본 캔버스 비율로 계산
3. 타깃 캔버스 `13.33 x 7.5`로 재매핑
4. 마지막에만 clamp

예시:

```python
x = round((shape.left / prs.slide_width) * SLIDE_WIDTH_INCHES, 2)
y = round((shape.top / prs.slide_height) * SLIDE_HEIGHT_INCHES, 2)
w = round((shape.width / prs.slide_width) * SLIDE_WIDTH_INCHES, 2)
h = round((shape.height / prs.slide_height) * SLIDE_HEIGHT_INCHES, 2)
```

### 2. `GROUP` 재귀 추출

현재 `GROUP`은 skip 되고 있다.

변경 후에는 다음을 수행한다.

1. group 내부 child shape를 재귀 순회
2. 부모 group의 transform을 반영해 child 좌표를 전역 좌표로 환산
3. child를 일반 shape처럼 추출

주의:

단순히 `group.left + child.left`만 더하면 틀릴 수 있다.

그룹 내부 좌표는 로컬 좌표계일 수 있으므로, 필요하면 group XML transform 기준으로 아래를 반영한다.

- offset
- extents
- scale

즉, **group transform-aware recursion**으로 구현한다.

### 3. `line` 추출

`AUTO_SHAPE` 중 `line`을 별도 처리한다.

처리 규칙:

- `auto_shape_type == line`이면 `LineElement`로 추출
- 색상은 line/fill이 아니라 line stroke 기준으로 읽는다
- line width도 가능하면 stroke width를 반영한다

### 4. `FREEFORM` 정규화

`FREEFORM`은 새 타입으로 내보내지 않고 아래 규칙으로 정규화한다.

#### case A: picture-filled freeform

- skip

사유:

- 이번 범위에서 image 타입은 반려

#### case B: thin freeform

조건 예시:

- `w`가 충분히 크고 `h`가 매우 작음
- 또는 `h`가 충분히 크고 `w`가 매우 작음

처리:

- `line`으로 변환

#### case C: solid-filled freeform

처리:

- bounding box 기준 `shape`로 변환
- 기본은 `rectangle`
- 둥근 모서리 판단이 명확하면 `round_rectangle`

주의:

정확한 벡터 모양은 손실되지만, 현재 계약에서 가장 현실적인 복원 방식이다.

#### case D: freeform + text

처리:

- 텍스트는 `text_box` 또는 `bullet_list`
- solid fill이 있으면 배경 `shape` 추가

### 5. 기존 도형 처리 유지 + 개선

`TEXT_BOX`, `PLACEHOLDER`, 일반 `AUTO_SHAPE` 처리는 유지하되, 다음을 개선한다.

- fill/stroke 읽기 안정화
- 글꼴 추출 fallback 보강
- 원본 순서(z-order) 보존
- clamp는 마지막 단계에서만 사용

### 6. 선 두께 0 문제 처리

현재 line은 `width == 0` 또는 `height == 0`인 경우가 많다.

처리 방향:

- `line` 타입에서는 zero-height/zero-width 허용
- `shape`로 억지 변환하지 않음

---

## 타입별 최종 정책

### 유지

- `text_box`
- `shape`
- `bullet_list`

### 신규 추가

- `line`

### 새 타입 추가 없이 정규화

- `FREEFORM`
- `GROUP`

### 보류

- `ellipse`

### 반려

- `image`

---

## 구현 순서

### 1단계: 계약과 스키마 확장

- `elements.json`에 `line` 타입 추가
- `app/schemas/generate.py`에 `LineElement` 추가
- `SlideElement` union 갱신

### 2단계: 렌더러 확장

- `app/services/pptx_service.py`에 `line` 렌더링 추가

### 3단계: 좌표계 정규화 수정

- 원본 slide size 기반 비율 좌표 변환 적용
- 기존 clamp 로직을 최종 safety 단계로만 사용

### 4단계: group recursion

- group child 재귀 순회
- 부모 transform 반영

### 5단계: shape extraction 개선

- `line` 추출 추가
- `FREEFORM` 정규화 로직 추가
- 기존 `AUTO_SHAPE` 처리 보강

### 6단계: 디버그/추적 보강

- 추출 시 skip 이유 로그
- 어떤 source shape가 어떤 target element로 변환됐는지 로그
- 문제 템플릿 재현을 위한 debug payload 저장 옵션 추가

### 7단계: 기존 템플릿 재추출

- `black.json` 포함 기존 template JSON을 다시 생성
- 이전 추출 결과와 비교

---

## 검증 계획

### 필수 검증

1. `20 x 11.25` 원본 PPT를 추출해도 좌표가 `13.33 x 7.5`에 비례 대응되는지 확인
2. `GROUP` 내부 텍스트/장식이 실제로 살아나는지 확인
3. `line`이 실제 JSON에 남는지 확인
4. `FREEFORM`이 의도대로 `line` 또는 `shape`로 정규화되는지 확인
5. 추출 결과가 `SlideContent/PageLayout` 검증을 통과하는지 확인
6. 템플릿 적용 결과가 이전보다 구조적으로 안정적인지 확인

### 테스트 항목

- unit test: 좌표 정규화
- unit test: line 추출
- unit test: freeform 정규화
- unit test: group recursion
- integration test: `/template/upload` -> JSON 저장 -> `/template/{name}` 조회
- regression test: `black.json` 재추출 후 요소 수 비교

---

## 성공 기준

아래 조건을 만족하면 이번 변경을 성공으로 본다.

1. `black.json` 같은 템플릿에서 기존보다 훨씬 많은 구조 요소가 보존된다.
2. line 구분선과 주요 패널 구조가 실제 템플릿 적용 결과에 반영된다.
3. 원본 슬라이드 크기가 달라도 위치 왜곡이 줄어든다.
4. `FREEFORM` 다수가 적절히 정규화되어 템플릿 형태가 무너지지 않는다.
5. `ellipse`, `image` 없이도 현재 템플릿 샘플 품질이 충분히 개선된다.

---

## 이번 변경에서 하지 않을 것

이번 단계에서는 아래를 하지 않는다.

- `image` 타입 추가
- `ellipse` 타입 추가
- chart/table/image의 템플릿 표현 확장
- 템플릿 업로드 과정에 LLM 개입

---

## 영향 파일 목록

- `fastapi-app/elements.json`
- `fastapi-app/app/schemas/generate.py`
- `fastapi-app/app/services/pptx_service.py`
- `fastapi-app/app/services/template_extractor.py`
- 필요 시 `fastapi-app/app/services/json_validation.py`
- 템플릿 재생성 결과물
  - `fastapi-app/template/*.json`

---

## 최종 결정 요약

- `line`: 추가
- `freeform`: 새 타입 추가 안 함, extractor에서 정규화
- `ellipse`: 보류
- `image`: 반려
- `GROUP`: 반드시 재귀 처리
- 좌표: 원본 슬라이드 크기 기준 비율 정규화

