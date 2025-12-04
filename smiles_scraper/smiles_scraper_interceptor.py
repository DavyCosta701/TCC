import asyncio
import json
from datetime import datetime

from curl_cffi import requests
from rich import print
from selenium_driverless import webdriver
from selenium_driverless.scripts.network_interceptor import (
    InterceptedRequest,
    NetworkInterceptor,
    RequestPattern,
)


def extract_flight_info(response_data):
    """
    Extract the lowest flight prices from Smiles API response

    Args:
        response_data: API response with flight data

    Returns:
        dict: Dictionary with lowest prices for outbound and inbound flights
    """
    try:
        if "requestedFlightSegmentList" not in response_data:
            print("Missing requestedFlightSegmentList in response")
            return {"error": "Invalid response structure"}

        segments = response_data["requestedFlightSegmentList"]
        if len(segments) < 2:
            print(f"Not enough segments in response. Found: {len(segments)}")
            return {"error": "Not enough segment data"}

        # Extract bestPricing from each segment
        outbound_pricing = segments[0].get("bestPricing", {})
        inbound_pricing = segments[1].get("bestPricing", {})

        result = {
            "lowest_outbound_miles": outbound_pricing.get("miles", float("inf")),
            "lowest_outbound_money": outbound_pricing.get("money", float("inf")),
            "lowest_inbound_miles": inbound_pricing.get("miles", float("inf")),
            "lowest_inbound_money": inbound_pricing.get("money", float("inf")),
        }

        # Also include smilesMoney option if available (miles + money combo)
        if "smilesMoney" in outbound_pricing:
            result["outbound_smiles_money"] = {
                "miles": outbound_pricing["smilesMoney"].get("miles", 0),
                "money": outbound_pricing["smilesMoney"].get("money", 0),
            }

        if "smilesMoney" in inbound_pricing:
            result["inbound_smiles_money"] = {
                "miles": inbound_pricing["smilesMoney"].get("miles", 0),
                "money": inbound_pricing["smilesMoney"].get("money", 0),
            }

        return result

    except Exception as e:
        print(f"Error extracting flight info: {str(e)}")
        return {"error": f"Data extraction error: {str(e)}"}


class SmilesFlightSearch:
    def __init__(self):
        self.requests_headers = None
        self.requests_cookies = None
        self._max_cookie_keys = 0
        self._cookie_source_url = None
        self.api_base_url = None

    def _get_intercepted_header(self, header_name, default=None):
        """Return sanitized header captured from the browser session."""
        if not self.requests_headers:
            return default

        target = header_name.lower()
        for key, value in self.requests_headers.items():
            if key.lower() == target:
                if isinstance(value, str):
                    return value.replace("\r", " ").replace("\n", " ").strip()
                return value

        return default

    def create_flight_search_url(
        self,
        origin,
        destination,
        departure_date_timestamp,
        return_date_timestamp,
        adults=1,
        children=0,
        infants=0,
        cabin="ECONOMIC",
    ):
        """
        Create Smiles search URL with the given parameters

        Args:
            origin (str): Origin airport code (e.g., 'SDU')
            destination (str): Destination airport code (e.g., 'CGH')
            departure_date_timestamp (int): Departure date in milliseconds timestamp
            return_date_timestamp (int): Return date in milliseconds timestamp
            adults (int): Number of adults
            children (int): Number of children
            infants (int): Number of infants
            cabin (str): Cabin class (ECONOMIC, BUSINESS, etc.)

        Returns:
            str: Complete search URL
        """
        base_url = "https://www.smiles.com.br/mfe/emissao-passagem/"

        params = [
            f"adults={adults}",
            f"cabin={cabin}",
            f"children={children}",
            f"departureDate={departure_date_timestamp}",
            f"infants={infants}",
            "isElegible=false",
            "isFlexibleDateChecked=false",
            f"returnDate={return_date_timestamp}",
            "searchType=g3",
            "segments=1",
            "tripType=1",
            f"originAirport={origin}",
            "originCity=",
            "originCountry=",
            "originAirportIsAny=false",
            f"destinationAirport={destination}",
            "destinCity=",
            "destinCountry=",
            "destinAirportIsAny=false",
            "novo-resultado-voos=true",
        ]

        query_string = "&".join(params)
        final_url = f"{base_url}?{query_string}"

        return final_url

    async def _on_request(self, data: InterceptedRequest):
        """Intercept requests to capture headers and cookies"""

        if not data.request.headers:
            return

        request_url = data.request.url or ""

        if "smiles.com.br" not in request_url:
            return

        cookie_value = None
        for key, value in data.request.headers.items():
            if key.lower() == "cookie":
                cookie_value = value
                break

        if not cookie_value:
            return

        cookie_pairs = [c.strip() for c in cookie_value.split(";") if "=" in c]
        cookie_keys = {c.split("=", 1)[0] for c in cookie_pairs}
        cookie_count = len(cookie_keys)

        is_api_request = "api-air-flightsearch" in request_url

        # Only update if we found a richer cookie jar or finally sniffed the API call itself
        if not is_api_request and cookie_count <= self._max_cookie_keys:
            return

        # Check if cookies contain anti-bot protection tokens (baseline sanity)
        if "bm_sz=" not in cookie_value and "_abck=" not in cookie_value:
            return

        self.requests_headers = data.request.headers
        self.requests_cookies = cookie_value
        self._max_cookie_keys = cookie_count
        self._cookie_source_url = request_url

        if is_api_request:
            self.api_base_url = request_url.split("?")[0]
            print(f"[SUCCESS] Detected API URL: {self.api_base_url}")

        print(f"\n[SUCCESS] Captured cookies from: {request_url}")
        print(f"[SUCCESS] Cookie count: {cookie_count}")
        print(f"[SUCCESS] Cookie preview: {cookie_value[:150]}...")
        print("[SUCCESS] Headers and cookies captured successfully!")

    async def initialize_headers(
        self,
        origin,
        destination,
        departure_date_timestamp,
        return_date_timestamp,
    ):
        """
        Initialize headers by opening the browser just once
        Opens the flight search page and captures cookies from first request
        """
        if self.requests_headers is not None:
            return

        url = self.create_flight_search_url(
            origin, destination, departure_date_timestamp, return_date_timestamp
        )
        # Use normal (non-headless) mode so you can see what's happening
        options = webdriver.ChromeOptions()

        print("\nOpening browser in normal mode to capture cookies...")
        print("The browser window will open - waiting for cookies...\n")

        async with webdriver.Chrome(options=options) as driver:
            async with NetworkInterceptor(
                driver,
                on_request=self._on_request,
                patterns=[RequestPattern.AnyRequest],
            ) as _:
                asyncio.ensure_future(driver.get(url))
                # Wait just long enough to capture initial cookies
                await driver.sleep(10)

        if not self.requests_headers:
            print("\nWarning: Could not capture headers and cookies.")
        else:
            print("\nHeaders and cookies initialized successfully!")

    def get_flight_info(
        self,
        origin,
        destination,
        departure_date,
        return_date,
        adults=1,
        children=0,
        infants=0,
        cabin="ECONOMIC",
    ):
        """
        Get flight information using pre-initialized headers

        Args:
            origin (str): Origin airport code
            destination (str): Destination airport code
            departure_date (str): Departure date in format 'YYYY-MM-DD'
            return_date (str): Return date in format 'YYYY-MM-DD'
            adults (int): Number of adults
            children (int): Number of children
            infants (int): Number of infants
            cabin (str): Cabin class

        Returns:
            dict: Response data from API
        """
        if not self.requests_headers:
            raise ValueError("Headers not initialized. Call initialize_headers first.")

        if not self.requests_cookies:
            raise ValueError("Cookies not captured. Run initialize_headers again.")

        try:
            params = {
                "cabin": cabin,
                "originAirportCode": origin,
                "destinationAirportCode": destination,
                "departureDate": departure_date,
                "returnDate": return_date,
                "memberNumber": "",
                "adults": str(adults),
                "children": str(children),
                "infants": str(infants),
                "forceCongener": "false",
            }

            accept_language = self._get_intercepted_header(
                "accept-language", "pt-BR,pt;q=0.9"
            )
            user_agent = self._get_intercepted_header(
                "user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            sec_ch_ua = self._get_intercepted_header(
                "sec-ch-ua",
                '"Google Chrome";v="141", "Chromium";v="141", "Not?A_Brand";v="8"',
            )
            sec_ch_mobile = self._get_intercepted_header("sec-ch-ua-mobile", "?0")
            sec_ch_platform = self._get_intercepted_header(
                "sec-ch-ua-platform", '"Windows"'
            )

            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": accept_language,
                "channel": "WEB",
                "dnt": "1",
                "origin": "https://www.smiles.com.br",
                "priority": "u=1, i",
                "referer": "https://www.smiles.com.br/",
                "sec-ch-ua": sec_ch_ua,
                "sec-ch-ua-mobile": sec_ch_mobile,
                "sec-ch-ua-platform": sec_ch_platform,
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": user_agent,
                "x-api-key": "aJqPU7xNHl9qN3NVZnPaJ208aPo2Bh2p2ZV844tw",
            }

            # Define the necessary cookies that the API endpoint actually uses
            # Based on comparison between document cookies and API endpoint cookies
            necessary_cookie_keys = {
                "test_club_smiles",
                "_ga",
                "_gcl_au",
                "OptanonAlertBoxClosed",
                "voxusmediamanager_cd_attr_status",
                "voxusmediamanager_acs",
                "measurement_id",
                "_hjSessionUser_3832769",
                "user_unic_ac_id",
                "advcake_trackid",
                "_tt_enable_cookie",
                "_ttp",
                "_pin_unauth",
                "__zlcmid",
                "bm_ss",
                "ak_bmsc",
                "AMP_MKTG_ef9f1f5d78",
                "_hjSession_3832769",
                "_clck",
                "lmd_orig",
                "lmd_traf",
                "voxusmediamanager_id",
                "cto_bundle",
                "vx_identifier",
                "voxus_last_entry_before_impression",
                "_abck",
                "bm_so",
                "_clsk",
                "bm_s",
                "bm_sz",
                "OptanonConsent",
                "_ga_BBTY3LETEV",
                "_ga_L25DPPG37X",
                "AMP_ef9f1f5d78",
                "_uetsid",
                "_uetvid",
                "ttcsid",
                "ttcsid_CB46OC3C77U9V9OUJ0KG",
                "fs_lua",
                "fs_uid",
                "bm_sv",
            }

            # Convert cookie string to dictionary and filter only necessary cookies
            all_cookies = {}
            for cookie in self.requests_cookies.split(";"):
                cookie = cookie.strip()
                if "=" in cookie:
                    key, value = cookie.split("=", 1)
                    all_cookies[key.strip()] = value.strip()

            # Filter to only necessary cookies
            cookies_dict = {
                k: v for k, v in all_cookies.items() if k in necessary_cookie_keys
            }

            print(f"\n[DEBUG] Making API request")
            print(f"[DEBUG] Origin: {origin} -> Destination: {destination}")
            print(f"[DEBUG] Dates: {departure_date} to {return_date}")
            print(f"[DEBUG] Cookie source: {self._cookie_source_url}")
            print(f"[DEBUG] Total cookies captured: {len(all_cookies)}")
            print(f"[DEBUG] Necessary cookies for API: {len(cookies_dict)}")
            print(f"[DEBUG] Filtered cookie keys: {list(cookies_dict.keys())[:10]}...")

            missing_cookie_keys = [
                k for k in necessary_cookie_keys if k not in cookies_dict
            ]
            if missing_cookie_keys:
                print(
                    f"[WARN] Missing {len(missing_cookie_keys)} cookies: {missing_cookie_keys[:5]}..."
                )

            # Use captured API URL or default to blue
            api_url = (
                self.api_base_url
                or "https://api-air-flightsearch-blue.smiles.com.br/v1/airlines/search"
            )
            print(f"[DEBUG] Using API URL: {api_url}")

            # Pass cookies as a dictionary
            resp = requests.get(
                url=api_url,
                params=params,
                headers=headers,
                cookies=cookies_dict,
                impersonate="chrome120",
            )

            print(f"[DEBUG] Response status code: {resp.status_code}")

            response_data = resp.json()

            if "requestedFlightSegmentList" not in response_data:
                print(
                    f"Warning: Response missing expected fields. Status code: {resp.status_code}"
                )
                print(f"Response preview: {str(response_data)[:200]}...")
                return {"error": f"Invalid API response. Status: {resp.status_code}"}

            return response_data

        except Exception as e:
            print(f"API request error: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}


async def main():
    origin = "SDU"
    destination = "CGH"
    departure_date = "2026-03-15"
    return_date = "2026-03-20"

    # Convert dates to timestamps (milliseconds)
    from datetime import datetime

    dep_dt = datetime.strptime(departure_date, "%Y-%m-%d")
    ret_dt = datetime.strptime(return_date, "%Y-%m-%d")
    departure_timestamp = int(dep_dt.timestamp() * 1000)
    return_timestamp = int(ret_dt.timestamp() * 1000)

    flight_search = SmilesFlightSearch()

    # Initialize headers once
    await flight_search.initialize_headers(
        origin, destination, departure_timestamp, return_timestamp
    )

    # Get flight info
    flight_data = flight_search.get_flight_info(
        origin, destination, departure_date, return_date
    )

    # Print results
    print("\n=== SMILES FLIGHT SEARCH RESULTS ===")
    print(f"Route: {origin} -> {destination}")
    print(f"Departure: {departure_date}")
    print(f"Return: {return_date}")
    print("\nBest Prices:")

    if "error" in flight_data:
        print(f"Error: {flight_data['error']}")
    else:
        flight_info = extract_flight_info(flight_data)

        if "error" in flight_info:
            print(f"Error: {flight_info['error']}")
        else:
            print(f"\nOutbound:")
            print(f"  Miles: {flight_info['lowest_outbound_miles']}")
            print(f"  Money: R$ {flight_info['lowest_outbound_money']:.2f}")
            if "outbound_smiles_money" in flight_info:
                print(
                    f"  Smiles Money: {flight_info['outbound_smiles_money']['miles']} miles + R$ {flight_info['outbound_smiles_money']['money']:.2f}"
                )

            print(f"\nInbound:")
            print(f"  Miles: {flight_info['lowest_inbound_miles']}")
            print(f"  Money: R$ {flight_info['lowest_inbound_money']:.2f}")
            if "inbound_smiles_money" in flight_info:
                print(
                    f"  Smiles Money: {flight_info['inbound_smiles_money']['miles']} miles + R$ {flight_info['inbound_smiles_money']['money']:.2f}"
                )

            total_miles = (
                flight_info["lowest_outbound_miles"]
                + flight_info["lowest_inbound_miles"]
            )
            total_money = (
                flight_info["lowest_outbound_money"]
                + flight_info["lowest_inbound_money"]
            )
            print(f"\nTotal:")
            print(f"  Miles: {total_miles}")
            print(f"  Money: R$ {total_money:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
