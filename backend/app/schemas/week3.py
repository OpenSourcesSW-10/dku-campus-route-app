from pydantic import BaseModel


class ErrorResponse(BaseModel):
    # HTTPException detail에 들어갈 오류 코드 문서화용 응답.
    detail: str
