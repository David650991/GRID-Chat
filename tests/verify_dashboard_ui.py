from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        # 1. Login (Register flow might fail if user exists, so try login directly)
        page.goto("http://localhost:5000/login")
        page.fill("input[name='username']", "testdashboard")
        page.fill("input[name='password']", "password123")
        page.click("button[type='submit']")

        # Handle potential "User not found" -> Go to register
        if "login" in page.url:
             if page.is_visible("text=Usuario o contraseña incorrectos"):
                 print("User doesn't exist, registering...")
                 page.goto("http://localhost:5000/register")
                 page.fill("input[name='username']", "testdashboard")
                 page.fill("input[name='password']", "password123")
                 page.click("button[type='submit']")
                 # Login again
                 page.fill("input[name='username']", "testdashboard")
                 page.fill("input[name='password']", "password123")
                 page.click("button[type='submit']")

        # 2. Check Dashboard (Index)
        print(f"Title: {page.title()}")
        # Check new classes
        if page.is_visible(".dashboard-layout"):
            print("SUCCESS: .dashboard-layout found.")
        else:
            print("FAILURE: .dashboard-layout not found.")

        if page.is_visible(".rooms-grid"):
            print("SUCCESS: .rooms-grid found.")
        else:
            print("FAILURE: .rooms-grid not found.")

        # 3. Check Chat Interface
        try:
            # Find a room card to click
            if page.is_visible(".room-card"):
                page.click(".room-card") # Enter first room

                page.wait_for_selector(".chat-main")
                print("SUCCESS: Entered chat room, .chat-main found.")

                if page.is_visible("textarea.composer-input"):
                    print("SUCCESS: textarea.composer-input found.")
                else:
                    print("FAILURE: textarea.composer-input not found.")

                # Test sidebar visibility
                if page.is_visible(".sidebar"):
                    print("SUCCESS: .sidebar is visible.")
            else:
                print("WARNING: No room cards found to test chat entry.")

        except Exception as e:
            print(f"Chat verify error: {e}")

        # Screenshot for verification
        page.screenshot(path="final_verify.png")
        browser.close()

if __name__ == "__main__":
    run()
