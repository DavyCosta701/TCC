import asyncio
import json
import time

from curl_cffi import requests
from rich import print
from selenium_driverless import webdriver
from selenium_driverless.scripts.network_interceptor import (
    InterceptedRequest,
    NetworkInterceptor,
    RequestPattern,
)


def extract_flight_info(response_data):
    trips = response_data["data"]["trips"]

    lowest_value_outbound = trips[0]["fareInformation"]["lowestPoints"]
    lowest_value_inbound = trips[1]["fareInformation"]["lowestPoints"]

    return lowest_value_outbound, lowest_value_inbound


class FlightSearchMoneyLatam:
    def __init__(self):
        self.requests_headers = None

    def create_flight_search_url(
        self, origin, destination, departure_date, return_date
    ):
        """
        Create LATAM search URL with the given parameters

        Args:
            origin (str): Origin airport code (e.g., 'BEL')
            destination (str): Destination airport code (e.g., 'GRU')
            departure_date (str): Departure date in format 'MM/DD/YYYY'
            return_date (str): Return date in format 'MM/DD/YYYY'

        Returns:
            str: Complete search URL
        """
        base_url = "https://www.latamairlines.com/br/pt/oferta-voos"

        # Convert dates to ISO format with timezone
        from datetime import datetime
        outbound = datetime.strptime(departure_date, "%m/%d/%Y").strftime("%Y-%m-%dT12:00:00.000Z")
        inbound = datetime.strptime(return_date, "%m/%d/%Y").strftime("%Y-%m-%dT12:00:00.000Z")

        # Build query parameters
        params = [
            f"origin={origin}",
            f"destination={destination}", 
            f"outbound={outbound}",
            f"inbound={inbound}",
            "adt=1",
            "chd=0",
            "inf=0",
            "trip=RT",
            "cabin=Economy",
            "redemption=true",
            "sort=RECOMMENDED"
        ]

        # Join parameters
        query_string = "&".join(params)

        # Construct final URL
        final_url = f"{base_url}?{query_string}"

        return final_url

    async def _on_request(self, data: InterceptedRequest):
        if (
            "https://www.latamairlines.com/bff/air-offers/v2/offers/search/redemption?child=0&outFrom=2025-02-13&inFrom=2025-03-04&inFlightDate=null&inOfferId=null&cabinType=Economy&outFlightDate=null&destination=GRU&sort=RECOMMENDED&redemption=true&outOfferId=null&adult=1&infant=0&origin=BEL"
            in data.request.url
            and data.request.method == "POST"
        ):
            self.requests_headers = (
                data.request.headers,
                json.loads(data.request.post_data),
            )
            print(self.requests_headers)
        # Find the specific request to the availability endpoint

    async def get_request_headers(
        self, origin, destination, departure_date, return_date
    ):
        url = self.create_flight_search_url(
            origin, destination, departure_date, return_date
        )
        print(url)
        options = webdriver.ChromeOptions().add_argument("--headless=new")

        async with webdriver.Chrome(options=options) as driver:
            async with NetworkInterceptor(
                driver,
                on_request=self._on_request,
                patterns=[RequestPattern.AnyRequest],
            ) as _:
                asyncio.ensure_future(driver.get(url))

                await driver.sleep(10)

    async def get_flight_info(self, origin, destination, departure_date, return_date):
        await self.get_request_headers(origin, destination, departure_date, return_date)

        resp = requests.post(
            url="https://b2c-api.voeazul.com.br/tudoAzulReservationAvailability/api/tudoazul/reservation/availability/v5/availability",
            headers=self.requests_headers[0],
            json=self.requests_headers[1],
            impersonate="chrome123",
        )
        with open("debug/resp_money.json", "w") as f:
            json.dump(resp.json(), f)
        return resp.json()


if __name__ == "__main__":
    origin = "BEL"
    destination = "GRU"
    departure_date = "02/15/2025"
    return_date = "03/25/2025"
    flight_search = FlightSearchMoneyLatam()
    result = asyncio.run(
        flight_search.get_request_headers(origin, destination, departure_date, return_date)
    )
    # parsed_result = extract_flight_info(result)
    # print("Menor valor de ida: ", parsed_result[0])
    # print("Menor valor de volta: ", parsed_result[1])
