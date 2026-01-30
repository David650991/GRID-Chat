from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Setup users... (omitting login details repetition for brevity, assume robust setup)
        # Create USER 1
        ctx1 = browser.new_context()
        p1 = ctx1.new_page()
        try:
            p1.goto("http://localhost:5000/register")
            p1.fill("input[name='username']", "userX")
            p1.fill("input[name='password']", "pass")
            p1.click("button[type='submit']")
        except: pass
        p1.goto("http://localhost:5000/login")
        p1.fill("input[name='username']", "userX")
        p1.fill("input[name='password']", "pass")
        p1.click("button[type='submit']")

        # Create USER 2
        ctx2 = browser.new_context()
        p2 = ctx2.new_page()
        try:
            p2.goto("http://localhost:5000/register")
            p2.fill("input[name='username']", "userY")
            p2.fill("input[name='password']", "pass")
            p2.click("button[type='submit']")
        except: pass
        p2.goto("http://localhost:5000/login")
        p2.fill("input[name='username']", "userY")
        p2.fill("input[name='password']", "pass")
        p2.click("button[type='submit']")

        # Enter Room
        # Wait for room card
        p1.wait_for_selector(".room-card")
        p1.click(".room-card >> nth=0")

        p2.wait_for_selector(".room-card")
        p2.click(".room-card >> nth=0")

        # Send Message
        # Selector specific to Send button in composer
        p1.wait_for_selector(".composer-toolbar button.btn-primary")
        p1.fill("#message_input", "Mensaje Test 1")
        p1.click(".composer-toolbar button.btn-primary") # Specific selector!

        time.sleep(2)

        if p2.is_visible("text=Mensaje Test 1"):
            print("SUCCESS: User 2 received message.")
        else:
            print("FAILURE: User 2 did not receive message.")
            p2.screenshot(path="failure_debug.png")

        p1.fill("#message_input", "Mensaje Test 2")
        p1.click(".composer-toolbar button.btn-primary")

        time.sleep(2)
        p2.screenshot(path="chat_flow_success.png")

        browser.close()

if __name__ == "__main__":
    run()
