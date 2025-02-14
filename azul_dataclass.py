from dataclasses import dataclass

@dataclass
class FlightInfoAzul:
  departureStation: str
  arrivalStation: str
  departureDate: str
  arrivalDate: str
  airCompany: str
  lowestValueOutboundMoney: float
  lowestValueInboundMoney: float
  lowestValueOutboundMiles: int
  lowestValueInboundMiles: int 
  totalMiles: int
  totalMoney: float

