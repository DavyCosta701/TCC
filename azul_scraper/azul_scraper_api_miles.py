import asyncio
import json
import time

import arrow  # Added Arrow for date manipulation
from curl_cffi import requests
from rich import print
from selenium_driverless import webdriver
from selenium_driverless.scripts.network_interceptor import (
    InterceptedRequest,
    NetworkInterceptor,
    RequestPattern,
)
from rich import print


def extract_flight_info(response_data):
    """
    Extract all flights and their prices from the response data

    Args:
        response_data: API response with flight data

    Returns:
        dict: Dictionary with flight information
    """
    try:
        # Check if the response has a valid structure
        if "data" not in response_data or "trips" not in response_data["data"]:
            print("Missing data or trips in response")
            return {"error": "Invalid response structure"}

        trips = response_data["data"]["trips"]
        if len(trips) < 2:
            print(f"Not enough trips in response. Found: {len(trips)}")
            return {"error": "Not enough trip data"}

        outbound_trip = trips[0] or {}
        inbound_trip = trips[1] or {}
        if not isinstance(outbound_trip, dict):
            outbound_trip = {}
        if not isinstance(inbound_trip, dict):
            inbound_trip = {}

        result = {
            "outbound_flights": [],
            "inbound_flights": [],
            "lowest_outbound": outbound_trip.get("fareInformation", {}).get(
                "lowestPoints", float("inf")
            ),
            "lowest_inbound": inbound_trip.get("fareInformation", {}).get(
                "lowestPoints", float("inf")
            ),
        }

        # Process outbound flights
        outbound_dates = outbound_trip.get("flightDates") or []
        if outbound_dates:
            first_outbound = outbound_dates[0] or {}
            for flight in first_outbound.get("flights", []) or []:
                if not isinstance(flight, dict):
                    continue
                flight_data = {
                    "flight_number": flight.get("flightNumber", "Unknown"),
                    "departure": flight.get("departureTime", "Unknown"),
                    "arrival": flight.get("arrivalTime", "Unknown"),
                    "duration": flight.get("duration", "Unknown"),
                    "prices": {},
                }

                # Get price for each fare category
                for fare in flight.get("fares", []) or []:
                    if not isinstance(fare, dict):
                        continue
                    if fare.get("points") is not None:
                        flight_data["prices"][fare.get("fareName", "Unknown")] = fare[
                            "points"
                        ]

                result["outbound_flights"].append(flight_data)

        # Process inbound flights
        inbound_dates = inbound_trip.get("flightDates") or []
        if inbound_dates:
            first_inbound = inbound_dates[0] or {}
            for flight in first_inbound.get("flights", []) or []:
                if not isinstance(flight, dict):
                    continue
                flight_data = {
                    "flight_number": flight.get("flightNumber", "Unknown"),
                    "departure": flight.get("departureTime", "Unknown"),
                    "arrival": flight.get("arrivalTime", "Unknown"),
                    "duration": flight.get("duration", "Unknown"),
                    "prices": {},
                }

                # Get price for each fare category
                for fare in flight.get("fares", []) or []:
                    if not isinstance(fare, dict):
                        continue
                    if fare.get("points") is not None:
                        flight_data["prices"][fare.get("fareName", "Unknown")] = fare[
                            "points"
                        ]

                result["inbound_flights"].append(flight_data)

        if not result["outbound_flights"] and not result["inbound_flights"]:
            print("No flight details available in response")

        return result

    except Exception as e:
        print(f"Error extracting flight info: {str(e)}")
        return {"error": f"Data extraction error: {str(e)}"}


def generate_date_range(base_date_str, format_str="MM/DD/YYYY"):
    """
    Generate a list of dates including the base date, 2 days before and 2 days after.

    Args:
        base_date_str (str): Base date in format 'MM/DD/YYYY'
        format_str (str): Format of the date string

    Returns:
        list: List of date strings in the same format
    """
    base_date = arrow.get(base_date_str, format_str)
    date_range = []

    for day_offset in range(-2, 3):  # -2, -1, 0, 1, 2
        date = base_date.shift(days=day_offset)
        date_range.append(date.format(format_str))

    return date_range


class FlightSearchMiles:
    def __init__(self):
        self.requests_headers = None
        self.requests_body_template = None

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
            "cc=PTS",
        ]

        # Join parameters and add timestamp
        query_string = "&".join(params)
        timestamp = str(int(time.time() * 1000))

        # Construct final URL
        final_url = f"{base_url}?{query_string}&{timestamp}"

        return final_url

    async def _on_request(self, data: InterceptedRequest):
        if (
            "https://b2c-api.voeazul.com.br/tudoAzulReservationAvailability/api/tudoazul/reservation/availability/v6/availability"
            in data.request.url
            and data.request.method == "POST"
        ):
            self.requests_headers = data.request.headers
            self.requests_body_template = json.loads(data.request.post_data)

    async def initialize_headers(
        self, origin, destination, departure_date, return_date
    ):
        """
        Initialize headers by opening the browser just once
        """
        if (
            self.requests_headers is not None
            and self.requests_body_template is not None
        ):
            return  # Already initialized

        url = self.create_flight_search_url(
            origin, destination, departure_date, return_date
        )
        options = webdriver.ChromeOptions().add_argument("--headless=new")

        print("Opening browser to initialize headers...")
        async with webdriver.Chrome(options=options) as driver:
            async with NetworkInterceptor(
                driver,
                on_request=self._on_request,
                patterns=[RequestPattern.AnyRequest],
            ) as _:
                asyncio.ensure_future(driver.get(url))
                await driver.sleep(10)

        if not self.requests_headers or not self.requests_body_template:
            print(
                "Warning: Could not capture request headers/body. The browser might not have intercepted the API call."
            )
        else:
            print("Headers initialized successfully")

    def _update_request_body(self, origin, destination, departure_date, return_date):
        """
        Update the request body template with new dates
        """
        if not self.requests_body_template:
            raise ValueError("Headers not initialized. Call initialize_headers first.")

        # Make a deep copy to avoid modifying the template
        body = json.loads(json.dumps(self.requests_body_template))

        # Format dates for API (YYYY-MM-DD format)
        # Convert MM/DD/YYYY to YYYY-MM-DD
        dep_date_obj = arrow.get(departure_date, "MM/DD/YYYY")
        ret_date_obj = arrow.get(return_date, "MM/DD/YYYY")
        dep_date_api = dep_date_obj.format("YYYY-MM-DD")
        ret_date_api = ret_date_obj.format("YYYY-MM-DD")

        # Update the dates in the request body
        try:
            # Check the structure of the body and update accordingly
            if "criteria" in body:
                # Update criteria-based structure
                if len(body["criteria"]) >= 2:
                    # Update outbound
                    body["criteria"][0]["departureStation"] = origin
                    body["criteria"][0]["arrivalStation"] = destination
                    body["criteria"][0]["std"] = departure_date
                    body["criteria"][0]["departureDate"] = dep_date_api

                    # Update inbound
                    body["criteria"][1]["departureStation"] = destination
                    body["criteria"][1]["arrivalStation"] = origin
                    body["criteria"][1]["std"] = return_date
                    body["criteria"][1]["departureDate"] = ret_date_api
                else:
                    print("Warning: criteria array does not have enough entries")
            elif "trips" in body:
                # Original trips-based structure (keep as fallback)
                for i, trip in enumerate(body["trips"]):
                    if i == 0:  # Outbound
                        trip["origin"] = origin
                        trip["destination"] = destination
                        trip["departureDate"] = dep_date_api
                    elif i == 1:  # Inbound
                        trip["origin"] = destination
                        trip["destination"] = origin
                        trip["departureDate"] = ret_date_api
            else:
                print("Warning: Could not identify the structure of the request body")
                print(f"Body keys: {list(body.keys())}")

        except (KeyError, IndexError) as e:
            print(f"Error updating request body: {e}")
            print(f"Request body structure: {json.dumps(body, indent=2)}")
            raise ValueError(f"Could not update request body: {e}")

        return body

    async def get_flight_info(self, origin, destination, departure_date, return_date):
        """
        Get flight information using pre-initialized headers
        """
        if not self.requests_headers:
            await self.initialize_headers(
                origin, destination, departure_date, return_date
            )

        try:
            # Update request body with new dates
            request_body = self._update_request_body(
                origin, destination, departure_date, return_date
            )

            # Clean headers
            cleaned_headers = {}
            for k, v in self.requests_headers.items():
                if k.startswith(":"):
                    continue
                if k.lower() in [
                    "content-length",
                    "host",
                    "connection",
                    "accept-encoding",
                    "user-agent",
                ]:
                    continue
                if k.lower().startswith("sec-ch-ua"):
                    continue
                cleaned_headers[k] = v

            resp = requests.post(
                url="https://b2c-api.voeazul.com.br/tudoAzulReservationAvailability/api/tudoazul/reservation/availability/v6/availability",
                headers=cleaned_headers,
                json=request_body,
                impersonate="chrome124",
            )

            try:
                response_data = resp.json()
            except json.JSONDecodeError:
                print(f"Failed to parse JSON response. Status: {resp.status_code}")
                print(f"Response text: {resp.text[:500]}...")  # Print first 500 chars
                return {"error": f"Invalid JSON response. Status: {resp.status_code}"}

            if "data" not in response_data:
                print(
                    f"Warning: Response missing 'data' field. Status code: {resp.status_code}"
                )
                print(f"Response preview: {str(response_data)[:200]}...")
                return {
                    "error": f"Invalid API response (no data field). Status: {resp.status_code}"
                }

            return response_data

        except Exception as e:
            print(f"API request error: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}

    async def search_date_range(
        self, origin, destination, base_departure_date, base_return_date
    ):
        """
        Search flights for a range of dates around the base dates

        Args:
            origin (str): Origin airport code
            destination (str): Destination airport code
            base_departure_date (str): Base departure date in MM/DD/YYYY format
            base_return_date (str): Base return date in MM/DD/YYYY format

        Returns:
            dict: Results with all flight prices for each date combination
        """
        departure_dates = generate_date_range(base_departure_date)
        return_dates = generate_date_range(base_return_date)

        # Initialize headers just once
        await self.initialize_headers(
            origin, destination, base_departure_date, base_return_date
        )

        results = {}

        for dep_date in departure_dates:
            results[dep_date] = {}

            for ret_date in return_dates:
                try:
                    print(
                        f"Searching for {origin} to {destination}: {dep_date} -> {ret_date}"
                    )
                    flight_data = await self.get_flight_info(
                        origin, destination, dep_date, ret_date
                    )

                    if "error" in flight_data:
                        results[dep_date][ret_date] = flight_data
                    else:
                        flight_info = extract_flight_info(flight_data)
                        results[dep_date][ret_date] = flight_info

                except Exception as e:
                    print(f"Error searching {dep_date} -> {ret_date}: {str(e)}")
                    results[dep_date][ret_date] = {"error": str(e)}

                # Small delay to prevent rate limiting
                await asyncio.sleep(2)

        return results


if __name__ == "__main__":
    origin = "BEL"
    destination = "GRU"
    departure_date = "01/30/2026"
    return_date = "02/02/2026"
    flight_search = FlightSearchMiles()

    # Search only for the specified dates (not date range)
    flight_data = asyncio.run(
        flight_search.get_flight_info(origin, destination, departure_date, return_date)
    )

    # Print the results
    print("\n=== AZUL MILES SEARCH RESULTS ===")
    print(f"Route: {origin} -> {destination}")
    print(f"Departure: {departure_date}")
    print(f"Return: {return_date}")

    if "error" in flight_data:
        print(f"\nError: {flight_data['error']}")
    else:
        flight_info = extract_flight_info(flight_data)

        if "error" in flight_info:
            print(f"\nError: {flight_info['error']}")
        else:
            print("\nBest Prices:")
            print(f"  Outbound: {flight_info['lowest_outbound']} points")
            print(f"  Inbound: {flight_info['lowest_inbound']} points")

            total_points = (
                flight_info["lowest_outbound"] + flight_info["lowest_inbound"]
            )
            print(f"\nTotal: {total_points} points")
