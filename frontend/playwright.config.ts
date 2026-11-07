import { defineConfig, devices } from '@playwright/test';
const url=process.env.FNB_WEB_URL ?? 'http://127.0.0.1:5173';
const python=process.env.FNB_PYTHON ?? (process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python');
export default defineConfig({testDir:'./tests/e2e',timeout:120000,expect:{timeout:15000},workers:1,
  use:{baseURL:url,trace:'retain-on-failure'},
  webServer:process.env.FNB_E2E_MANAGED==='1'?{command:`"${python}" -m uvicorn app.api.main:app --host 127.0.0.1 --port 4173`,url:`${url}/api/v1/health`,reuseExistingServer:false,timeout:30000}:undefined,
  reporter:[['list'],['json',{outputFile:'test-results/browser-results.json'}]],
  projects:[{name:'chromium',use:{...devices['Desktop Chrome']}}]});
