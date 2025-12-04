from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless")  # Без UI, для Airflow
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Запуск браузера
driver = webdriver.Chrome(options=options)

driver.get("https://www.rottentomatoes.com")

print(driver.title)

driver.quit()
