import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def keep_alive():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Set a real user-agent to avoid detection as a bot
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        url = "https://zs-monitor-zs.streamlit.app/"
        print(f"Visiting {url}")
        driver.get(url)
        
        # Wait for page load and potential WebSocket handshake
        print("Waiting for page to load...")
        time.sleep(30)  # Wait 30 seconds to ensure everything loads
        
        print(f"Page Title: {driver.title}")
        print("Successfully visited the page.")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    keep_alive()
