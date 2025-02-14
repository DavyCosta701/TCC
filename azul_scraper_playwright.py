import time
from playwright.sync_api import sync_playwright

class AzulScraperPlaywright:
    def __init__(self):
        self.browser = None
        self.page = None

    def get_azul_data(self, departure_city, arrival_city, departure_date, arrival_date):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=False)
            self.page = self.browser.new_page()
            self.page.goto("https://www.voeazul.com.br/br/pt/home", wait_until='load')
            # Accept cookies
            self.page.click("#onetrust-accept-btn-handler")
            self.page.click("#Origem1")
            origem_box  = self.page.locator("#Origem1")
            origem_box.fill(departure_city)
            self.page.click("#Destino1")
            destino_box = self.page.locator("#Destino1")
            destino_box.fill(arrival_city)  
            self.page.keyboard.press("Enter")
            self.page.click("#datepicker_temp1")
            data_ida = self.page.locator("#startDate")
            data_ida.fill(departure_date)
            self.page.click("#datepicker_temp2")
            data_chegada = self.page.locator("#endDate")
            data_chegada.fill(arrival_date)
            self.page.click("#search-button")
            
            

            time.sleep(10)

if __name__ == "__main__":
    scraper = AzulScraperPlaywright()
    scraper.get_azul_data("São Paulo", "Rio de Janeiro", "2025-02-11", "2025-02-12")
