import os
import time
import requests
import zipfile
import shutil
import tempfile
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException


# Constants
USERNAME = "Mizuno2074"  # Change to your Twitter username
OUTPUT_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "TwitterScrapperThings")
LOG_FILE = os.path.join(OUTPUT_FOLDER, "scrappedimagesXS.log")
IMAGE_FOLDER = os.path.join(OUTPUT_FOLDER, "imagesXS")
ZIP_FILE = os.path.join(OUTPUT_FOLDER, "imagesXS.zip")
IMAGE_HANDLE_LOG = os.path.join(OUTPUT_FOLDER, "ImageHandleLogsXS.txt")
ACCOUNTS_LOG = os.path.join(OUTPUT_FOLDER, "AccountsXS.txt")
MAX_SCROLL_ATTEMPTS = 5
SCROLL_PAUSE_TIME = 3


# Ensure the output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# Set up Edge options with advanced stealth
def setup_driver():
    # Path to Edge WebDriver in Downloads folder
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads", "msedgedriver.exe")
    service = Service(downloads_path)
    
    # Create a temporary profile directory
    temp_profile = tempfile.mkdtemp(prefix="edge_temp_profile_")
    
    edge_options = webdriver.EdgeOptions()
    edge_options.add_argument(f"user-data-dir={temp_profile}")
    
    # Anti-detection measures (reduced to prevent crashes)
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_experimental_option("useAutomationExtension", False)
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    
    # Realistic user agent
    edge_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0")
    
    # Stability options
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--disable-gpu")
    
    # Disable save password and autofill prompts
    edge_options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "autofill.profile_enabled": False
    })
    
    driver = webdriver.Edge(service=service, options=edge_options)
    
    # Execute CDP commands to hide WebDriver
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })
    
    return driver, temp_profile


# Save progress to files
def save_progress(image_links, image_handles):
    # Save image links
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        for link in image_links:
            f.write(link + "\n")

    # Save image handles
    with open(IMAGE_HANDLE_LOG, "w", encoding="utf-8") as f:
        for i, (img_url, handles) in enumerate(image_handles.items(), start=1):
            f.write(f"Image {i} : {', '.join(handles) if handles else 'No handles found'}\n")

    # Save all unique handles
    all_handles = set()
    for handles in image_handles.values():
        all_handles.update(handles)

    with open(ACCOUNTS_LOG, "w", encoding="utf-8") as f:
        for i, handle in enumerate(all_handles, start=1):
            f.write(f"Acc {i} : {handle}\n")


# Extract Twitter handles from tweet content
def extract_handles(tweet_element):
    handles = set()
    try:
        # Find all elements that contain Twitter handles (e.g., @username)
        handle_elements = tweet_element.find_elements(By.XPATH, ".//span[contains(text(), '@')]")
        for element in handle_elements:
            text = element.text.strip()
            if text.startswith("@"):
                handles.add(text)
    except Exception as e:
        print(f"⚠ Error extracting handles: {e}")
    return handles


# Scrape image links and associated handles from Twitter/X
def scrape_images(driver):
    driver.get("https://x.com/i/flow/login")
    input("🔹 Please log in manually and press Enter when you are on the home page...")


    while "x.com/i/flow/login" in driver.current_url:
        print("⚠ Still on login page! Please complete login first.")
        time.sleep(3)


    print("✅ Logged in! Redirecting to likes...")
    driver.get(f"https://x.com/{USERNAME}/likes")
    time.sleep(5)  # Allow initial page load


    image_links = set()
    image_handles = {}  # Dictionary to store image links and associated handles
    scroll_attempts = 0


    try:
        while scroll_attempts < MAX_SCROLL_ATTEMPTS:
            try:
                old_height = driver.execute_script("return document.body.scrollHeight")
            except WebDriverException as e:
                print(f"⚠ Browser crashed or became unresponsive: {e}")
                print(f"💾 Saving progress before exit...")
                break

            # Scroll down
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                time.sleep(SCROLL_PAUSE_TIME)
            except WebDriverException as e:
                print(f"⚠ Error scrolling: {e}")
                break

            try:
                new_height = driver.execute_script("return document.body.scrollHeight")
            except WebDriverException as e:
                print(f"⚠ Browser crashed: {e}")
                print(f"💾 Saving progress...")
                break

            if new_height == old_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0

            # Scrape image links and handles
            try:
                tweets = driver.find_elements(By.XPATH, "//article[@data-testid='tweet']")
                for tweet in tweets:
                    images = tweet.find_elements(By.XPATH, ".//img[contains(@src, 'pbs.twimg.com/media/')]")
                    handles = extract_handles(tweet)
                    for img in images:
                        img_url = img.get_attribute("src")
                        if img_url:
                            image_links.add(img_url)
                            image_handles[img_url] = handles
            except WebDriverException as e:
                print(f"⚠ Error scraping tweets: {e}")
                break

            print(f"🔹 Scraped {len(image_links)} image links so far...")
            
            # Save progress periodically (every 50 images)
            if len(image_links) % 50 == 0:
                save_progress(image_links, image_handles)
                print(f"💾 Progress saved at {len(image_links)} images")

    except Exception as e:
        print(f"⚠ Unexpected error: {e}")
    finally:
        # Always save progress before exiting
        save_progress(image_links, image_handles)
        print(f"✅ Scraped {len(image_links)} image links. Saved to {LOG_FILE}")
        print(f"✅ Saved image handles to {IMAGE_HANDLE_LOG}")
        
        all_handles = set()
        for handles in image_handles.values():
            all_handles.update(handles)
        print(f"✅ Saved {len(all_handles)} unique handles to {ACCOUNTS_LOG}")

    return image_links, image_handles


# Download images from the scraped links
def download_images():
    if not os.path.exists(LOG_FILE):
        print("⚠ Log file not found!")
        return


    os.makedirs(IMAGE_FOLDER, exist_ok=True)


    with open(LOG_FILE, "r", encoding="utf-8") as f:
        image_links = f.read().splitlines()


    for i, url in enumerate(image_links, start=1):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                file_extension = query_params.get("format", ["jpg"])[0]


                filename = os.path.join(IMAGE_FOLDER, f"image_{i}.{file_extension}")
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"✅ Downloaded: {filename}")
            else:
                print(f"⚠ Failed to download: {url}")
        except Exception as e:
            print(f"⚠ Error downloading {url}: {e}")


    # Zip the images
    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(IMAGE_FOLDER):
            for file in files:
                zipf.write(os.path.join(root, file), file)


    print(f"✅ All images downloaded and zipped into {ZIP_FILE}")


# Check for missing images
def check_missing_images(total_images):
    existing_numbers = set()
    for filename in os.listdir(IMAGE_FOLDER):
        if filename.startswith("image_") and filename.split(".")[0][6:].isdigit():
            existing_numbers.add(int(filename.split(".")[0][6:]))


    missing_numbers = sorted(set(range(1, total_images + 1)) - existing_numbers)


    if missing_numbers:
        print(f"⚠ Missing files: {missing_numbers}")
        with open(os.path.join(OUTPUT_FOLDER, "missing_images549.log"), "w") as f:
            for num in missing_numbers:
                f.write(f"image_{num}\n")
        print("✅ Missing numbers saved to missing_images.log")
    else:
        print("✅ No missing files found!")


# Main function to run the entire process
def main():
    driver, temp_profile = setup_driver()
    try:
        image_links, image_handles = scrape_images(driver)
    except Exception as e:
        print(f"⚠ Fatal error in main: {e}")
        image_links = set()
    finally:
        try:
            driver.quit()
        except:
            pass
        # Delete the temporary profile after scraping
        try:
            shutil.rmtree(temp_profile)
            print(f"✅ Temporary profile deleted: {temp_profile}")
        except Exception as e:
            print(f"⚠ Error deleting temporary profile: {e}")


    download_images()
    total_images = len(image_links)
    check_missing_images(total_images)


if __name__ == "__main__":
    main()
