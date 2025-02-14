import asyncio
import json
import time
from selenium_driverless import webdriver
from selenium_driverless.scripts.network_interceptor import (
    NetworkInterceptor,
    InterceptedRequest,
    RequestPattern,
)
from curl_cffi import requests
from rich import print


def extract_flight_info(response_data):
    trips = response_data["data"]["trips"]

    lowest_value_outbound = trips[0]["fareInformation"]["lowestAmount"]
    lowest_value_inbound = trips[1]["fareInformation"]["lowestAmount"]
    
    return lowest_value_outbound, lowest_value_inbound
 

class FlightSearchMoney:
    def __init__(self):
        self.requests_headers = None


    def create_flight_search_url(
        self, origin, destination, departure_date, return_date
    ):
        """
        Create Azul search URL with the given parameters


        Args:
            origin (str): Origin airport code (e.g., 'BEL')
            destination (str): Destination airport code (e.g., 'GRU')
            departure_date (str): Departure date in format 'MM/DD/YYYY'
            return_date (str): Return date in format 'MM/DD/YYYY'

        Returns:
            str: Complete search URL
        """
        base_url = "https://www.voeazul.com.br/br/pt/home/selecao-voo"

        # Build query parameters
        params = [
            f"c[0].ds={origin}",
            f"c[0].std={departure_date}",
            f"c[0].as={destination}",
            f"c[1].ds={destination}",
            f"c[1].std={return_date}",
            f"c[1].as={origin}",
            "p[0].t=ADT",
            "p[0].c=1",
            "p[0].cp=false",
            "f.dl=3",
            "f.dr=3",
            "cc=BRL",
        ]

        # Join parameters and add timestamp
        query_string = "&".join(params)
        timestamp = str(int(time.time() * 1000))

        # Construct final URL
        final_url = f"{base_url}?{query_string}&{timestamp}"

        return final_url

    async def _on_request(self, data: InterceptedRequest):
        if (
            "https://b2c-api.voeazul.com.br/reservationavailability/api/reservation/availability/v5/availability"
            in data.request.url
            and data.request.method == "POST"
        ):
            self.requests_headers = (data.request.headers, json.loads(data.request.post_data))
        # Find the specific request to the availability endpoint


    async def get_request_headers(
        self, origin, destination, departure_date, return_date
    ):
        url = self.create_flight_search_url(
            origin, destination, departure_date, return_date
        )
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
            url="https://b2c-api.voeazul.com.br/reservationavailability/api/reservation/availability/v5/availability",
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
    flight_search = FlightSearchMoney()
    result = asyncio.run(
        flight_search.get_flight_info(origin, destination, departure_date, return_date)
    )
    parsed_result = extract_flight_info(result)
    print("Menor valor de ida: ", parsed_result[0])
    print("Menor valor de volta: ", parsed_result[1])
