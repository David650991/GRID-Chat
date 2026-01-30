from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # User 1
        ctx1 = browser.new_context()
        p1 = ctx1.new_page()
        try:
            p1.goto("http://localhost:5000/register")
            p1.fill("input[name='username']", "modular1")
            p1.fill("input[name='password']", "pass")
            p1.click("button[type='submit']")
        except: pass
        p1.goto("http://localhost:5000/login")
        p1.fill("input[name='username']", "modular1")
        p1.fill("input[name='password']", "pass")
        p1.click("button[type='submit']")

        # User 2
        ctx2 = browser.new_context()
        p2 = ctx2.new_page()
        try:
            p2.goto("http://localhost:5000/register")
            p2.fill("input[name='username']", "modular2")
            p2.fill("input[name='password']", "pass")
            p2.click("button[type='submit']")
        except: pass
        p2.goto("http://localhost:5000/login")
        p2.fill("input[name='username']", "modular2")
        p2.fill("input[name='password']", "pass")
        p2.click("button[type='submit']")

        # Enter Room
        p1.wait_for_selector(".room-card")
        p1.click(".room-card >> nth=0")

        p2.wait_for_selector(".room-card")
        p2.click(".room-card >> nth=0")

        # Send Message
        # We look for ANY button with text "ENVIAR" inside the composer-toolbar logic or just by text
        p1.wait_for_selector("text=ENVIAR")
        p1.fill("#message_input", "Mensaje Modular 1")
        p1.click("text=ENVIAR")

        time.sleep(2)

        if p2.is_visible("text=Mensaje Modular 1"):
            print("SUCCESS: User 2 received message.")
        else:
            print("FAILURE: User 2 did not receive message.")
            p2.screenshot(path="debug_modular_fail.png")

        browser.close()

if __name__ == "__main__":
    run()
