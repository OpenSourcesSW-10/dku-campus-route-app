from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    # SQLAlchemy 모델 객체를 Pydantic 응답으로 변환 가능하게 설정.
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    # 단순 성공 메시지를 내려줄 때 사용하는 공통 응답.
    message: str
