
from datetime import datetime
import json
from curl_cffi import requests
from rich import print


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

cookies = {
    'test_club_smiles': 'old',
    'ak_bmsc': 'F6420FA9A8A68C0C519A52C9FDB5DC07~000000000000000000000000000000~YAAQlG8VAnAt+OCZAQAAiUCS/R08ss+/dAXdCUeQTPyeBEHXJF1TAisILyBFItK8zS5dPKWAUGZqufDdELjgdHIe4I/Hbzu37cg4VYsfAQq9k1FSYN3JpV2TcS94hR492a+f6SAT1DVR2J743umERxdWUCBzNY77H/P0MGXx8c/dXKKTEkWGixy6ZgnSI+F2XoFWGF0uqYaQvo3IzpT5lA5PwQFODvm5sDCgQpUrqzx5UX9PumU8HCe4pyMV/+8AL3CE/4JROsXtr1jeKfZKUotYQX88Oeu43ZRjmkfKZqz+GK+j77i+dge+tFDIc32a62al5zou+vUgQ2kScYr+alt9A+YYDoojJEnmn10sqHqEVuILHkYgfTR3ETB6XsXI73eandY3fs5QRH+O5cQ=',
    'AMP_MKTG_ef9f1f5d78': 'JTdCJTdE',
    '_ga': 'GA1.1.1821529371.1760895799',
    '_gcl_au': '1.1.1270925211.1760895799',
    '_clck': '11700vp%5E2%5Eg0a%5E0%5E2118',
    'OptanonAlertBoxClosed': '2025-10-19T17:43:20.177Z',
    'voxusmediamanager_cd_attr_status': 'true',
    'voxusmediamanager_acs': 'true',
    'measurement_id': 'G-BBTY3LETEV',
    '_hjSessionUser_3832769': 'eyJpZCI6ImZiNmQ2OWFlLTIzYTItNTk2Yy1iZTljLTUzYWJlNTA3NDI2OSIsImNyZWF0ZWQiOjE3NjA4OTU3OTkyNjAsImV4aXN0aW5nIjp0cnVlfQ==',
    'user_unic_ac_id': '83974f59-72f2-f970-9f3f-1869cafb94f9',
    'advcake_trackid': 'a882f2f7-607f-f12b-f610-2e4ad592541d',
    '_tt_enable_cookie': '1',
    '_ttp': '01K7YS3TZQHBV460SQ07CQ0N43_.tt.2',
    '_pin_unauth': 'dWlkPU5UZGtZVFprWWpVdE1HTTBOeTAwTlRBM0xUazNaV1F0TlRneVlXUmxNVEl3TVRoaQ',
    '__zlcmid': '1UCo09fS2qbmERn',
    'voxus_last_entry_before_impression': '1760896111',
    '_abck': 'DDCE4D8240C974F0B2B394606F92897F~-1~YAAQ0CkMF1X47eCZAQAAoiKX/Q5PhkXVuvKWe6+ft8AwPohrlAN0JfBkEFXpBGbnxbJp5mi+CvDYDbeT/IRSrMmbgEKXvYzqrSJ0EiRwdaeUNv98baF1pZhMUYaa5R37hqD+Jcc6Vyl33AurIbkrJ10tWkXjnZAsG3ahBZPhiClA9ftZPfVT5sIeKzTDZjNZkYn1ofvOK8NbmIjNt7sTPFT9eBi1Mf9dE7bv/twVvJ9tPjO4exXzkB8dhh28D+ScUqOlqqEH/yCT2m59etEYUCcOjBcPSxFgE3ra9EwzI3fvKTPPNqIEgHOnYZtdcq9dSzvJZmF0JX5Q8DksTFvNxslfK8qF+rRLQ6Zu4pgpudlJWYE/DZr1ppRCe1q5LIQeT/xa28cXaui82qz5kfHsf/UlEQ8Me71++6kNZrvCqn6Vmuj7e7mFh7AeVVkoaT3e280el648WIZ7i9vQGbQXiI+wmaBwq4SSWcITrEsj6oUxXvESXZ8u7BDAyGZOt1LC6HoGRsAnkaoTMdP5PKmYQHeEoWIkSqDV0qkK56QN+tKfP25XODKEisCV92TJkVq1N36UaqS/ADK6YWZWoho3plRPvqfO0+5X6idI5sTbjJ00MN49haNqudPW15b1ROJvAJdFmiqyFx7Ko0SHYP7Lso3yvprukyDSwPsZCSh4uYP3XAD4JSEWkLa225m8zpiiJ8Gt2v63/rHWhTvKRT//kaeeXHRctV+2psUk0Y4s+a/Jo/EeUcVEB4+Q5g7P0MBFR3dung==~-1~-1~-1~AAQAAAAE%2f%2f%2f%2f%2f8RxTI76Iucwotej2qUrO61AprqsEdo9rnCMBCVW6ELTQoCVivvmOGZRVwaMQLBS12rISU5AMfYtydxmyskM+sTkv1ZJS0X6IMJt~-1',
    'bm_ss': 'ab8e18ef4e',
    'bm_so': '7F9B475B254BDA49F28F24966DDF9A4C5726E8128BC13B6A8450196EBF0B182E~YAAQlG8VAlhl/OCZAQAA84Xa/QWJLN/KRRpXcrlYLcWjeoEMXmi5Mph2yLyKxMm5ppfbGew6g//4h93OGJex0wbtDqmEJDJJIik8rQahg92bdll5S7XX/Zugj4ZJ5gRmfc+glvmtifWYOoQRwJIoUinF9hs39FBhacYs3f8UBdbkR/jMyRAMebF49CtRPzWRmpA2WIJP5Ilnul02GEshTNFylDsBijQfkdecjYZZhDt1wHji7rjjceTeNKhzfKc1Vxkp6taqNWCsVN4FY+JGSh+iFPN4ohyf6oZPzKKkJ6SMon4SB6omCcNP4H3KaVO5wyCsIu+ZzW5KGUT0Y5mhdi2MFWpT8739t6wX70Mxu/o0LynzuREQL4VoG0H9aI5XOyEewYc0fYG2tR/9gj3ejXXufeYnrTaXL0Y6N1CX/7S3V9QS4hdnv4jM6EaBBzgeoVYl+1uQ7M1VoJmaqt+FcF0=',
    '_hjSession_3832769': 'eyJpZCI6IjU0OTYxODRjLTk5M2YtNGUyNy1iZGE5LTg4YzdjYmE0NjIyNiIsImMiOjE3NjA5MDA1MzcwNTksInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowfQ==',
    'voxusmediamanager_id': '17499921844210.451659645302434637fozbw4iq2m',
    'vx_identifier': '7',
    'voxusmediamanager_ip': '190.89.241.60',
    'bm_s': 'YAAQlG8VAp5n/OCZAQAAs7Xa/QQCbCP0CYuCeRPQZEMrQlE2UUCm2yvw8oOYkPcx6h8sYdB86Km7cMbQLvCezm1uhn2lTXsYdvEMu65mAhM2viLXkASAjWxEOy6AzM0bV8JEpjqr5asapD5DWhWmL/alF8LFyuokrHrCSK4Esru2DtCYqsy113vKMpdzyzAP+cG9t5V81377QJTxQi/+gkSGNEYGdA3vhBA0+YqoFQYlW+q/CqwoREcSRIPzF9w6DttyRZcSF7sUF3hzfgWxRr5mXhsS3bjrcRAJ1X/9/s3Ar3lvbvsHqDfo8Wfa4jfTPUeyFd4oKUnx5GhYpFURrnul5U9GaiiPy8Zlj0jlPUw92ZpEX1HGzfwX1WVdYuUMTTNHTp+wtNXT+0Osn0cYafzSvcxya1KOEBupyigFwqeXDp6vr9EMasXl3KK1+vZ47heFmcDJ9tdKFUBPpIbvHB854ITHR0AjMqu7lJcNPTEHu2jZiTi1sbT+L9C8h7hTnrVJCmbvkVdVwJg8kQTlJVrVkVPiL0wc4v6u52SDhJ9EFXLIy6D8f0RpD4Ze8q+trvSnmD2ybQv5MLgRT7E=',
    'bm_sz': '107E8174E6456C37285AA71C1B66ACF2~YAAQlG8VAp9n/OCZAQAAs7Xa/R3vGfQqcB8sWZXeeYdr/KCE/B5irSk5wK+rKf1vF6v3d4YNcsZ3sM7Kg4MUA7XidJCPb1Zg4oiUL1CFJnZSFjLzKT5n9wg03PrsfHVPDK8euf1xSj6jvjVgLDfA5IOtI1hGECj0Rm+xfkMnbuc8KRicZE8FbgESlQCYKUIXzixXymIRO9E3sCjJrbZxQM4fqLznNZq5XXq1oC/YCcC5GTgSWj45XoIzDcAIBBEHV6qynzowGn4PtFo7jESkF8UG9UUMGDMz8w8YrXKEkTFe4Rn6mmcehj9oPHpCmCWpvCUUng54EA/tnog8sEdGpAN7nbHmtQjepzNGNq6kssIGj4T88Asvs4Je7bu88cYNqDloOAdzXz+8hOxbfuHAdH/OlOK8tpd3TQb4UC8WNt3w5gkR13sSweBm8oTnf0VYSgNLgeg=~4276804~3420486',
    '_uetsid': '270c1100ad1311f08b7be978ed248bd9',
    '_uetvid': '270c4bb0ad1311f0872269b5c57bc888',
    'ttcsid': '1760900538698::A6raAMCNM2vC69fnz5AX.2.1760900559798.0',
    'ttcsid_CB46OC3C77U9V9OUJ0KG': '1760900538697::6MDmZ91r6BUgmLhaXMzK.2.1760900559798.0',
    'OptanonConsent': 'isGpcEnabled=0&datestamp=Sun+Oct+19+2025+16%3A02%3A40+GMT-0300+(Hor%C3%A1rio+Padr%C3%A3o+de+Bras%C3%ADlia)&version=202502.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=c15f000f-de4f-4ae6-8681-f17786234d19&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0004%3A1%2CC0002%3A1%2CC0003%3A1&intType=1&geolocation=BR%3BPA&AwaitingReconsent=false',
    '_ga_BBTY3LETEV': 'GS2.1.s1760900532$o2$g1$t1760900561$j31$l0$h0',
    '_ga_L25DPPG37X': 'GS2.1.s1760900532$o2$g1$t1760900561$j31$l0$h617733569',
    '_clsk': '1z0qvr0%5E1760900561715%5E4%5E1%5Eh.clarity.ms%2Fcollect',
    'bm_sv': '70BA4201A382DB3BF63C11C2208BF231~YAAQlG8VAilr/OCZAQAA7fna/R0ApfHxO/49f5rWTHtjREhu1Wg3uN7IZU4+JZwWVm9hU5qVEY3CpsTW/zVB0LY8W5A+3976fAYDeDm7aIwju0ER5ZAghV9FOd9SOqEy08qC8MFjIvyaoy1A0s5AdUfOv6P5fmiv6FiyicF3/LYPP029XIBcs/Qw9j3PfBEQZx2DMM2d9n2NYmdZrQ1g5axuV8rcJmLgzsiShTknO35BMjB/9PlC8zDjac/vu1M/uaI6Ow==~1',
    'fs_lua': '1.1760900561503',
    'fs_uid': '#o-22R5SZ-na1#b89e6b77-2e14-46d9-a9c5-0fbab70feb6d:03cdd255-b3ca-4604-84f0-d2c746425323:1760900531003::5#/1792431818',
    'AMP_ef9f1f5d78': 'JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjJlYjEzNzNhYy1mMDNjLTQwN2YtOTM1Ni02OGI5MDY5ZTdmNzYlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzYwOTAwNTM2MDExJTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc2MDkwMDU2MTgyOSUyQyUyMmxhc3RFdmVudElkJTIyJTNBMjUlMkMlMjJwYWdlQ291bnRlciUyMiUzQTYlN0Q=',
    'cto_bundle': '1WxzTV80cyUyRm5uWUtnckpQSnVRRjRHU3RYbHBKUEtlQ0RXU09sUUxMbVUza21KZXA3Wlg3cDJwaVlNd1JiMm9KQTJIVnQ0MXlXVGNoUkw1b1FGNyUyRnU4TVBRZXdFcGJJZUJCdnFKR3dBaklFQ2JlTUV6OFRXdjQ4ZG9vekNRaTVjaE1zVVBvMTFOZHhiUEN1bjh0M1d5bHJQUGFlbkFuUk96U095TXFNRnJoNVhNSDRBJTNE',
}

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'pt-BR,pt;q=0.9',
    'channel': 'WEB',
    'dnt': '1',
    'origin': 'https://www.smiles.com.br',
    'priority': 'u=1, i',
    'referer': 'https://www.smiles.com.br/',
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    'x-api-key': 'aJqPU7xNHl9qN3NVZnPaJ208aPo2Bh2p2ZV844tw',
      'cookie': 'test_club_smiles=old; ak_bmsc=F6420FA9A8A68C0C519A52C9FDB5DC07~000000000000000000000000000000~YAAQlG8VAnAt+OCZAQAAiUCS/R08ss+/dAXdCUeQTPyeBEHXJF1TAisILyBFItK8zS5dPKWAUGZqufDdELjgdHIe4I/Hbzu37cg4VYsfAQq9k1FSYN3JpV2TcS94hR492a+f6SAT1DVR2J743umERxdWUCBzNY77H/P0MGXx8c/dXKKTEkWGixy6ZgnSI+F2XoFWGF0uqYaQvo3IzpT5lA5PwQFODvm5sDCgQpUrqzx5UX9PumU8HCe4pyMV/+8AL3CE/4JROsXtr1jeKfZKUotYQX88Oeu43ZRjmkfKZqz+GK+j77i+dge+tFDIc32a62al5zou+vUgQ2kScYr+alt9A+YYDoojJEnmn10sqHqEVuILHkYgfTR3ETB6XsXI73eandY3fs5QRH+O5cQ=; AMP_MKTG_ef9f1f5d78=JTdCJTdE; _ga=GA1.1.1821529371.1760895799; _gcl_au=1.1.1270925211.1760895799; _clck=11700vp%5E2%5Eg0a%5E0%5E2118; OptanonAlertBoxClosed=2025-10-19T17:43:20.177Z; voxusmediamanager_cd_attr_status=true; voxusmediamanager_acs=true; measurement_id=G-BBTY3LETEV; _hjSessionUser_3832769=eyJpZCI6ImZiNmQ2OWFlLTIzYTItNTk2Yy1iZTljLTUzYWJlNTA3NDI2OSIsImNyZWF0ZWQiOjE3NjA4OTU3OTkyNjAsImV4aXN0aW5nIjp0cnVlfQ==; user_unic_ac_id=83974f59-72f2-f970-9f3f-1869cafb94f9; advcake_trackid=a882f2f7-607f-f12b-f610-2e4ad592541d; _tt_enable_cookie=1; _ttp=01K7YS3TZQHBV460SQ07CQ0N43_.tt.2; _pin_unauth=dWlkPU5UZGtZVFprWWpVdE1HTTBOeTAwTlRBM0xUazNaV1F0TlRneVlXUmxNVEl3TVRoaQ; __zlcmid=1UCo09fS2qbmERn; voxus_last_entry_before_impression=1760896111; _abck=DDCE4D8240C974F0B2B394606F92897F~-1~YAAQ0CkMF1X47eCZAQAAoiKX/Q5PhkXVuvKWe6+ft8AwPohrlAN0JfBkEFXpBGbnxbJp5mi+CvDYDbeT/IRSrMmbgEKXvYzqrSJ0EiRwdaeUNv98baF1pZhMUYaa5R37hqD+Jcc6Vyl33AurIbkrJ10tWkXjnZAsG3ahBZPhiClA9ftZPfVT5sIeKzTDZjNZkYn1ofvOK8NbmIjNt7sTPFT9eBi1Mf9dE7bv/twVvJ9tPjO4exXzkB8dhh28D+ScUqOlqqEH/yCT2m59etEYUCcOjBcPSxFgE3ra9EwzI3fvKTPPNqIEgHOnYZtdcq9dSzvJZmF0JX5Q8DksTFvNxslfK8qF+rRLQ6Zu4pgpudlJWYE/DZr1ppRCe1q5LIQeT/xa28cXaui82qz5kfHsf/UlEQ8Me71++6kNZrvCqn6Vmuj7e7mFh7AeVVkoaT3e280el648WIZ7i9vQGbQXiI+wmaBwq4SSWcITrEsj6oUxXvESXZ8u7BDAyGZOt1LC6HoGRsAnkaoTMdP5PKmYQHeEoWIkSqDV0qkK56QN+tKfP25XODKEisCV92TJkVq1N36UaqS/ADK6YWZWoho3plRPvqfO0+5X6idI5sTbjJ00MN49haNqudPW15b1ROJvAJdFmiqyFx7Ko0SHYP7Lso3yvprukyDSwPsZCSh4uYP3XAD4JSEWkLa225m8zpiiJ8Gt2v63/rHWhTvKRT//kaeeXHRctV+2psUk0Y4s+a/Jo/EeUcVEB4+Q5g7P0MBFR3dung==~-1~-1~-1~AAQAAAAE%2f%2f%2f%2f%2f8RxTI76Iucwotej2qUrO61AprqsEdo9rnCMBCVW6ELTQoCVivvmOGZRVwaMQLBS12rISU5AMfYtydxmyskM+sTkv1ZJS0X6IMJt~-1; bm_ss=ab8e18ef4e; bm_so=7F9B475B254BDA49F28F24966DDF9A4C5726E8128BC13B6A8450196EBF0B182E~YAAQlG8VAlhl/OCZAQAA84Xa/QWJLN/KRRpXcrlYLcWjeoEMXmi5Mph2yLyKxMm5ppfbGew6g//4h93OGJex0wbtDqmEJDJJIik8rQahg92bdll5S7XX/Zugj4ZJ5gRmfc+glvmtifWYOoQRwJIoUinF9hs39FBhacYs3f8UBdbkR/jMyRAMebF49CtRPzWRmpA2WIJP5Ilnul02GEshTNFylDsBijQfkdecjYZZhDt1wHji7rjjceTeNKhzfKc1Vxkp6taqNWCsVN4FY+JGSh+iFPN4ohyf6oZPzKKkJ6SMon4SB6omCcNP4H3KaVO5wyCsIu+ZzW5KGUT0Y5mhdi2MFWpT8739t6wX70Mxu/o0LynzuREQL4VoG0H9aI5XOyEewYc0fYG2tR/9gj3ejXXufeYnrTaXL0Y6N1CX/7S3V9QS4hdnv4jM6EaBBzgeoVYl+1uQ7M1VoJmaqt+FcF0=; _hjSession_3832769=eyJpZCI6IjU0OTYxODRjLTk5M2YtNGUyNy1iZGE5LTg4YzdjYmE0NjIyNiIsImMiOjE3NjA5MDA1MzcwNTksInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowfQ==; voxusmediamanager_id=17499921844210.451659645302434637fozbw4iq2m; vx_identifier=7; voxusmediamanager_ip=190.89.241.60; bm_s=YAAQlG8VAp5n/OCZAQAAs7Xa/QQCbCP0CYuCeRPQZEMrQlE2UUCm2yvw8oOYkPcx6h8sYdB86Km7cMbQLvCezm1uhn2lTXsYdvEMu65mAhM2viLXkASAjWxEOy6AzM0bV8JEpjqr5asapD5DWhWmL/alF8LFyuokrHrCSK4Esru2DtCYqsy113vKMpdzyzAP+cG9t5V81377QJTxQi/+gkSGNEYGdA3vhBA0+YqoFQYlW+q/CqwoREcSRIPzF9w6DttyRZcSF7sUF3hzfgWxRr5mXhsS3bjrcRAJ1X/9/s3Ar3lvbvsHqDfo8Wfa4jfTPUeyFd4oKUnx5GhYpFURrnul5U9GaiiPy8Zlj0jlPUw92ZpEX1HGzfwX1WVdYuUMTTNHTp+wtNXT+0Osn0cYafzSvcxya1KOEBupyigFwqeXDp6vr9EMasXl3KK1+vZ47heFmcDJ9tdKFUBPpIbvHB854ITHR0AjMqu7lJcNPTEHu2jZiTi1sbT+L9C8h7hTnrVJCmbvkVdVwJg8kQTlJVrVkVPiL0wc4v6u52SDhJ9EFXLIy6D8f0RpD4Ze8q+trvSnmD2ybQv5MLgRT7E=; bm_sz=107E8174E6456C37285AA71C1B66ACF2~YAAQlG8VAp9n/OCZAQAAs7Xa/R3vGfQqcB8sWZXeeYdr/KCE/B5irSk5wK+rKf1vF6v3d4YNcsZ3sM7Kg4MUA7XidJCPb1Zg4oiUL1CFJnZSFjLzKT5n9wg03PrsfHVPDK8euf1xSj6jvjVgLDfA5IOtI1hGECj0Rm+xfkMnbuc8KRicZE8FbgESlQCYKUIXzixXymIRO9E3sCjJrbZxQM4fqLznNZq5XXq1oC/YCcC5GTgSWj45XoIzDcAIBBEHV6qynzowGn4PtFo7jESkF8UG9UUMGDMz8w8YrXKEkTFe4Rn6mmcehj9oPHpCmCWpvCUUng54EA/tnog8sEdGpAN7nbHmtQjepzNGNq6kssIGj4T88Asvs4Je7bu88cYNqDloOAdzXz+8hOxbfuHAdH/OlOK8tpd3TQb4UC8WNt3w5gkR13sSweBm8oTnf0VYSgNLgeg=~4276804~3420486; _uetsid=270c1100ad1311f08b7be978ed248bd9; _uetvid=270c4bb0ad1311f0872269b5c57bc888; ttcsid=1760900538698::A6raAMCNM2vC69fnz5AX.2.1760900559798.0; ttcsid_CB46OC3C77U9V9OUJ0KG=1760900538697::6MDmZ91r6BUgmLhaXMzK.2.1760900559798.0; OptanonConsent=isGpcEnabled=0&datestamp=Sun+Oct+19+2025+16%3A02%3A40+GMT-0300+(Hor%C3%A1rio+Padr%C3%A3o+de+Bras%C3%ADlia)&version=202502.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=c15f000f-de4f-4ae6-8681-f17786234d19&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0004%3A1%2CC0002%3A1%2CC0003%3A1&intType=1&geolocation=BR%3BPA&AwaitingReconsent=false; _ga_BBTY3LETEV=GS2.1.s1760900532$o2$g1$t1760900561$j31$l0$h0; _ga_L25DPPG37X=GS2.1.s1760900532$o2$g1$t1760900561$j31$l0$h617733569; _clsk=1z0qvr0%5E1760900561715%5E4%5E1%5Eh.clarity.ms%2Fcollect; bm_sv=70BA4201A382DB3BF63C11C2208BF231~YAAQlG8VAilr/OCZAQAA7fna/R0ApfHxO/49f5rWTHtjREhu1Wg3uN7IZU4+JZwWVm9hU5qVEY3CpsTW/zVB0LY8W5A+3976fAYDeDm7aIwju0ER5ZAghV9FOd9SOqEy08qC8MFjIvyaoy1A0s5AdUfOv6P5fmiv6FiyicF3/LYPP029XIBcs/Qw9j3PfBEQZx2DMM2d9n2NYmdZrQ1g5axuV8rcJmLgzsiShTknO35BMjB/9PlC8zDjac/vu1M/uaI6Ow==~1; fs_lua=1.1760900561503; fs_uid=#o-22R5SZ-na1#b89e6b77-2e14-46d9-a9c5-0fbab70feb6d:03cdd255-b3ca-4604-84f0-d2c746425323:1760900531003::5#/1792431818; AMP_ef9f1f5d78=JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjJlYjEzNzNhYy1mMDNjLTQwN2YtOTM1Ni02OGI5MDY5ZTdmNzYlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzYwOTAwNTM2MDExJTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc2MDkwMDU2MTgyOSUyQyUyMmxhc3RFdmVudElkJTIyJTNBMjUlMkMlMjJwYWdlQ291bnRlciUyMiUzQTYlN0Q=; cto_bundle=1WxzTV80cyUyRm5uWUtnckpQSnVRRjRHU3RYbHBKUEtlQ0RXU09sUUxMbVUza21KZXA3Wlg3cDJwaVlNd1JiMm9KQTJIVnQ0MXlXVGNoUkw1b1FGNyUyRnU4TVBRZXdFcGJJZUJCdnFKR3dBaklFQ2JlTUV6OFRXdjQ4ZG9vekNRaTVjaE1zVVBvMTFOZHhiUEN1bjh0M1d5bHJQUGFlbkFuUk96U095TXFNRnJoNVhNSDRBJTNE',
}

params = {
    'cabin': 'ECONOMIC',
    'originAirportCode': 'SDU',
    'destinationAirportCode': 'CGH',
    'departureDate': '2025-10-30',
    'returnDate': '2025-11-30',
    'memberNumber': '',
    'adults': '1',
    'children': '0',
    'infants': '0',
    'forceCongener': 'false',
}

response = requests.get(
    'https://api-air-flightsearch-blue.smiles.com.br/v1/airlines/search',
    params=params,
    cookies=cookies,
    headers=headers)

response_data = response.json()

# Save full response
with open(f'smiles_output/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json', 'w') as f:
    json.dump(response_data, f)

# Extract and print flight info
flight_info = extract_flight_info(response_data)
print("\n=== SMILES FLIGHT SEARCH RESULTS ===")
print(f"Route: {params['originAirportCode']} -> {params['destinationAirportCode']}")
print(f"Departure: {params['departureDate']}")
print(f"Return: {params['returnDate']}")
print("\nBest Prices:")

if "error" in flight_info:
    print(f"Error: {flight_info['error']}")
else:
    print(f"\nOutbound:")
    print(f"  Miles: {flight_info['lowest_outbound_miles']}")
    print(f"  Money: R$ {flight_info['lowest_outbound_money']:.2f}")
    if "outbound_smiles_money" in flight_info:
        print(f"  Smiles Money: {flight_info['outbound_smiles_money']['miles']} miles + R$ {flight_info['outbound_smiles_money']['money']:.2f}")

    print(f"\nInbound:")
    print(f"  Miles: {flight_info['lowest_inbound_miles']}")
    print(f"  Money: R$ {flight_info['lowest_inbound_money']:.2f}")
    if "inbound_smiles_money" in flight_info:
        print(f"  Smiles Money: {flight_info['inbound_smiles_money']['miles']} miles + R$ {flight_info['inbound_smiles_money']['money']:.2f}")

    total_miles = flight_info['lowest_outbound_miles'] + flight_info['lowest_inbound_miles']
    total_money = flight_info['lowest_outbound_money'] + flight_info['lowest_inbound_money']
    print(f"\nTotal:")
    print(f"  Miles: {total_miles}")
    print(f"  Money: R$ {total_money:.2f}")
