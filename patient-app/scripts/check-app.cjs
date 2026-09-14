const { chromium } = require("@playwright/test");
const path = require("path");
process.chdir(path.resolve(__dirname, "../.."));
const fs = require("fs");
const assert = require("assert/strict");
(async () => {
  const browser = await chromium.launch({
    executablePath:
      process.env.CARELANE_CHROME ||
      "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: true,
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.setDefaultTimeout(90000);
  await page.goto("http://localhost:8081", { timeout: 120000 });
  await page.getByText("Hello, Demo Patient").waitFor();
  fs.mkdirSync("reports/app", { recursive: true });
  await page.screenshot({
    path: "reports/app/home-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Start symptom guide", exact: true })
    .click();
  await page.getByRole("button", { name: "Itchy skin", exact: true }).click();
  await page
    .getByRole("button", { name: "Explore suggested departments", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Explore Dermatology", exact: true })
    .waitFor();
  await page.screenshot({ path: "reports/app/guidance.png", fullPage: true });
  await page
    .getByRole("button", { name: "Explore Dermatology", exact: true })
    .click();
  await page
    .getByRole("button", { name: "View Dr. Rohan Sethi", exact: true })
    .click();
  await page
    .getByRole("button", { name: /^Book /, disabled: false })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Confirm demo appointment", exact: true })
    .click();
  await page.getByText("Your demo appointment is saved.").waitFor();
  await page.screenshot({ path: "reports/app/booking.png", fullPage: true });
  await page.reload();
  await page.getByRole("button", { name: "My visits", exact: true }).click();
  await page
    .getByRole("button", { name: "Check in to demo queue", exact: true })
    .click();
  await page.getByText("YOU’RE CHECKED IN", { exact: true }).waitFor();
  await page
    .getByRole("button", { name: "Open demo desk", exact: true })
    .click();
  await page.screenshot({ path: "reports/app/queue.png", fullPage: true });
  for (let n = 0; n < 3; n++) {
    await page
      .getByRole("button", { name: "Call next demo patient", exact: true })
      .click();
    await page.waitForTimeout(1200);
  }
  await page.getByText("YOUR TURN", { exact: true }).waitFor();
  await page
    .getByRole("button", { name: "Complete demo visit", exact: true })
    .click();
  await page.getByText("VISIT COMPLETE", { exact: true }).waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Home", exact: true }).click();
  await page.screenshot({
    path: "reports/app/home-mobile.png",
    fullPage: true,
  });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
    false,
    "Mobile must not overflow",
  );
  await page.getByRole("button", { name: "Find care", exact: true }).click();
  await page.getByLabel("Search doctors", { exact: true }).fill("zzzz");
  await page.getByText("No doctors found", { exact: true }).waitFor();
  await page
    .getByRole("button", { name: "Clear filters", exact: true })
    .click();
  await page
    .getByRole("button", { name: "View Dr. Anaya Mehra", exact: true })
    .waitFor();
  await page.route("**/api/**", (route) => route.abort());
  await page.getByRole("button", { name: "Home", exact: true }).click();
  await page
    .getByRole("button", { name: "Start symptom guide", exact: true })
    .click();
  await page.getByRole("button", { name: "Itchy skin", exact: true }).click();
  await page
    .getByRole("button", { name: "Explore suggested departments", exact: true })
    .click();
  await page.getByText(/We could not reach the demo service/).waitFor();
  assert.deepEqual(errors, []);
  const result = {
    passed: true,
    checks: [
      "Home loads",
      "Real trained model returns Dermatology",
      "Doctor filter and slots",
      "Booking survives reload",
      "Check in",
      "Queue advances from 3 to ready to complete",
      "390px layout has no page overflow",
      "Search empty state",
      "Offline error",
    ],
    browserErrors: errors,
  };
  fs.writeFileSync(
    "reports/app/browser-checks.json",
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result));
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
