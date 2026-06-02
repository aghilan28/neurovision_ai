import asyncio
import os
from playwright.async_api import async_playwright

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Set a large viewport for high-res capture
        context = await browser.new_context(viewport={'width': 1600, 'height': 1200}, record_video_dir="runtime_verification_media/videos/")
        page = await context.new_page()

        base_path = os.path.abspath("runtime_frontend_preview")
        screens = [
            ("dashboard.html", "01_command_center.png"),
            ("upload.html", "02_eeg_intake.png"),
            ("analysis.html", "03_analysis_execution.png"),
            ("prediction.html", "04_prediction_review.png"),
            ("reports.html", "05_evidence_center.png"),
            ("clinical.html", "06_clinical_workspace.png"),
            ("operational.html", "07_operational_workspace.png"),
            ("autonomous.html", "08_autonomous_workspace.png"),
            ("research.html", "09_research_workspace.png"),
        ]

        os.makedirs("runtime_verification_media/screenshots", exist_ok=True)

        for html_file, screenshot_name in screens:
            url = f"file://{os.path.join(base_path, html_file)}"
            await page.goto(url)
            # Wait a bit for animations to settle (though we want to see the brain)
            await asyncio.sleep(1)
            await page.screenshot(path=f"runtime_verification_media/screenshots/{screenshot_name}", full_page=True)

            # Special capture for the brain animation if on dashboard
            if html_file == "dashboard.html":
                # Wait longer to ensure we get a good frame of the animation
                await asyncio.sleep(2)
                await page.screenshot(path="runtime_verification_media/screenshots/01_command_center_brain_zoom.png", clip={'x': 280, 'y': 150, 'width': 800, 'height': 500})

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())
