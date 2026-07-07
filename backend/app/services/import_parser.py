"""결정적 추출: 업로드 파일을 "rows of cells"로만 정규화한다.

의미 해석(날짜/금액/카테고리)은 하지 않는다 — 그건 LLM 정규화 단계의 몫이다.
지원: csv, xlsx, xls(암호화 포함, msoffcrypto), pdf(pdfplumber).
"""

import io


class ImportParseError(Exception):
    """추출 단계에서 복구 불가한 오류 (지원하지 않는 형식/암호 실패 등)."""


def _is_encrypted_office(content: bytes) -> bool:
    try:
        import msoffcrypto

        return msoffcrypto.OfficeFile(io.BytesIO(content)).is_encrypted()
    except Exception:
        return False


def _decrypt_office(content: bytes, password: str) -> bytes:
    import msoffcrypto

    office = msoffcrypto.OfficeFile(io.BytesIO(content))
    try:
        office.load_key(password=password)
        out = io.BytesIO()
        office.decrypt(out)
        return out.getvalue()
    except Exception as e:  # noqa: BLE001 - 비밀번호 오류를 명확한 메시지로 변환
        raise ImportParseError(f"파일 복호화 실패 (비밀번호 확인): {e}") from e


def _extract_pdf(content: bytes) -> list[list[str]]:
    import pdfplumber

    rows: list[list[str]] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    rows.append([("" if c is None else str(c)) for c in row])
            if not (page.extract_tables() or []):
                text = page.extract_text() or ""
                for line in text.splitlines():
                    if line.strip():
                        rows.append(line.split())
    return rows


def extract_rows(
    content: bytes, filename: str, password: str | None = None,
) -> list[list[str]]:
    """업로드 파일에서 셀 단위 행 목록을 추출한다."""
    import pandas as pd

    name = filename.lower()

    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), header=None, dtype=str, keep_default_na=False)
        return df.astype(str).values.tolist()

    if name.endswith(".pdf"):
        return _extract_pdf(content)

    if name.endswith((".xlsx", ".xls")):
        data = content
        if password:
            data = _decrypt_office(content, password)
        elif _is_encrypted_office(content):
            raise ImportParseError("암호화된 파일입니다. 비밀번호를 입력하세요")

        engine = "openpyxl" if name.endswith(".xlsx") else "xlrd"
        try:
            df = pd.read_excel(io.BytesIO(data), header=None, dtype=str, engine=engine)
        except ImportParseError:
            raise
        except Exception as e:  # noqa: BLE001 - 엔진 자동 선택으로 폴백
            try:
                df = pd.read_excel(io.BytesIO(data), header=None, dtype=str)
            except Exception:
                raise ImportParseError(f"엑셀 파싱 실패: {e}") from e
        df = df.fillna("")
        return df.astype(str).values.tolist()

    raise ImportParseError(f"지원하지 않는 파일 형식: {filename}")
