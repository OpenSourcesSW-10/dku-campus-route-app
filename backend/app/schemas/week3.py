from pydantic import BaseModel


class ErrorResponse(BaseModel):
    # HTTPException detail에 들어갈 오류 코드를 문서화하기 위한 응답이다.
    detail: str
