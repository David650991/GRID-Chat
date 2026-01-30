from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Wait for server to start
        try:
            page.goto("http://localhost:5000", timeout=5000)
        except:
            print("Retrying connection...")
            time.sleep(2)
            page.goto("http://localhost:5000")

        # Check title
        print(f"Title: {page.title()}")

        # Check specific new classes
        if page.is_visible(".auth-card"):
            print("SUCCESS: .auth-card found.")
        else:
            print("FAILURE: .auth-card not found.")

        if page.is_visible(".auth-form"):
            print("SUCCESS: .auth-form found.")
        else:
            print("FAILURE: .auth-form not found.")

        # Check input placeholders
        username_ph = page.get_attribute("input[name='username']", "placeholder")
        print(f"Username placeholder: {username_ph}")

        # Check button text
        btn_text = page.inner_text(".auth-btn")
        print(f"Button text: {btn_text}")

        # Take a screenshot for artifact verification
        page.screenshot(path="login_page_verify.png")
        print("Screenshot saved to login_page_verify.png")

        browser.close()

if __name__ == "__main__":
    run()
