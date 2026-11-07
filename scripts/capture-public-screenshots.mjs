import {fileURLToPath} from 'node:url';
// Actual local application screenshots; synthetic sources only, no mocked results.
import {createRequire} from 'node:module';
import {mkdir} from 'node:fs/promises';
const require=createRequire(new URL('../frontend/package.json',import.meta.url));
const {chromium}=require('@playwright/test');
const browser=await chromium.launch();
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.goto('http://127.0.0.1:8000');
 await page.getByLabel('Dataset',{exact:true}).selectOption('synthetic-bank-stress');
 await page.getByRole('heading',{name:'Start with the evidence.'}).waitFor();
 await mkdir(new URL('../docs/screenshots/',import.meta.url),{recursive:true});
 const shot=async name=>{await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:fileURLToPath(new URL(`../docs/screenshots/${name}.png`,import.meta.url)),animations:'disabled'});};
 await shot('datasets');
 await page.getByRole('button',{name:'Open Graph Explorer'}).click();await page.getByTestId('network-graph').waitFor();await shot('graph-explorer');
 await page.getByRole('button',{name:'Benchmarks',exact:true}).click();await shot('benchmarks');
 await page.getByRole('button',{name:'Results & Analysis',exact:true}).click();await page.getByRole('heading',{name:'Critical node rankings'}).waitFor();await shot('results');
 console.log('Four actual, synthetic-data screenshots captured.');
}finally{await browser.close();}
