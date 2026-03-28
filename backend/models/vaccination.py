from sqlalchemy import Column, String, Integer
from models.database import Base

class VaccinationSchedule(Base):
    __tablename__ = "vaccination_schedule"

    id = Column(Integer, primary_key=True, index=True)
    age_label = Column(String, nullable=False)       # "Birth", "6 weeks" etc
    age_weeks = Column(Integer, nullable=True)        # 0, 6, 10, 14, 36, 52
    vaccine_name = Column(String, nullable=False)
    dose = Column(String, nullable=True)
    route_site = Column(String, nullable=True)
    remarks = Column(String, nullable=True)