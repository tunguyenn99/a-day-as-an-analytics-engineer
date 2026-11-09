// Re-capture the README evidence screenshots from a running local platform
// (`make platform-local`). Usage:
//   cd tools/docs && npm install && npm run screenshots
// Env: GRAFANA_USER/GRAFANA_PASSWORD (default admin / local-only-change-me),
//      AIRFLOW_USER/AIRFLOW_PASSWORD (Airflow is skipped when unset),
//      OUT_DIR (default docs/images), CHROME_PATH (use a system Chrome instead
//      of `npx playwright install chromium`).
const path = require("path");
const { chromium } = require("playwright");

const OUT = process.env.OUT_DIR || path.resolve(__dirname, "../../docs/images");
const GRAFANA = process.env.GRAFANA_URL || "http://localhost:3000";
const PROMETHEUS = process.env.PROMETHEUS_URL || "http://localhost:9090";
const AIRFLOW = process.env.AIRFLOW_URL || "http://localhost:8080";
// Default range matches the historical dataset.
const RANGE = "from=1325376000000&to=1451606399000";

async function shot(page, url, file, waitFor) {
  // "load", not "networkidle": the Loki logs panel streams continuously.
  await page.goto(url, { waitUntil: "load" });
  if (waitFor) await page.waitForSelector(waitFor, { timeout: 30000 });
  await page.waitForTimeout(4000); // let panels finish querying and rendering
  await page.screenshot({ path: path.join(OUT, file), fullPage: true });
  console.log("saved", file);
}

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || undefined,
  });
  const auth = Buffer.from(
    `${process.env.GRAFANA_USER || "admin"}:${process.env.GRAFANA_PASSWORD || "local-only-change-me"}`,
  ).toString("base64");
  const grafana = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await grafana.setExtraHTTPHeaders({ Authorization: `Basic ${auth}` });
  await shot(grafana, `${GRAFANA}/d/web-analytics?${RANGE}&kiosk`, "grafana-dashboard.png", ".react-grid-layout");
  await shot(grafana, `${GRAFANA}/d/analytics-operations?kiosk`, "grafana-operations.png", ".react-grid-layout");

  const prom = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await shot(prom, `${PROMETHEUS}/targets`, "prometheus-targets.png");
  await shot(prom, `${PROMETHEUS}/alerts`, "prometheus-alerts.png");

  if (process.env.AIRFLOW_USER && process.env.AIRFLOW_PASSWORD) {
    const airflow = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
    await airflow.goto(`${AIRFLOW}/login/`);
    await airflow.fill("#username", process.env.AIRFLOW_USER);
    await airflow.fill("#password", process.env.AIRFLOW_PASSWORD);
    await airflow.click("input[type=submit]");
    await shot(airflow, `${AIRFLOW}/dags/web_analytics_medallion/grid?tab=graph`, "airflow-dag.png");
  } else {
    console.log("skip airflow-dag.png (set AIRFLOW_USER and AIRFLOW_PASSWORD)");
  }
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
