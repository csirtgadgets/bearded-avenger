from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .indicator import Indicator

Base = declarative_base()


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    tag = Column(String, index=True)

    indicator_id = Column(Integer, ForeignKey('indicators.id', ondelete='CASCADE'))
    indicator = relationship(
        Indicator,
    )

