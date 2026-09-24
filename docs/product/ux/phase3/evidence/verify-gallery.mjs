import {readFile,writeFile} from 'node:fs/promises';
const file=new URL('VISUAL-COMPARISON.html',import.meta.url);
const html=await readFile(file,'utf8');
let updated=html.replaceAll('browser-v2-1/aligned-allocation-form.png','browser-v2-1/aligned-allocation-controls.png');
if(!updated.includes('rel="icon"'))updated=updated.replace("img-src 'self';","img-src 'self' data:;").replace('<title>','<link rel="icon" href="data:,"><title>');
if(updated!==html)await writeFile(file,updated);
const {chromium}=await import('file:///D:/1-webapp/15-forwarder-golden-20260921/node_modules/@playwright/test/index.mjs');
const browser=await chromium.launch({channel:'chrome',headless:true});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 page.on('requestfailed',r=>errors.push(r.url()));
 await page.goto('http://127.0.0.1:4183/');await page.evaluate(()=>document.fonts.ready);
 await page.locator('.section-nav [data-expert-section="allocation"]').click();await page.locator('[data-dialog="allocation"]').click();
 await page.locator('.dialog').screenshot({path:new URL('browser-v2-1/aligned-allocation-controls.png',import.meta.url).pathname.replace(/^\/(\w:)/,'$1')});
 await page.goto('http://127.0.0.1:4184/evidence/VISUAL-COMPARISON.html');await page.evaluate(()=>document.fonts.ready);
 for(const img of await page.locator('img').all()){await img.scrollIntoViewIfNeeded();await img.evaluate(x=>x.decode());}
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:new URL('browser-v2-1/comparison-gallery.png',import.meta.url).pathname.replace(/^\/(\w:)/,'$1')});
 const result={errors,images:await page.locator('img').count(),failed:await page.locator('img').evaluateAll(xs=>xs.filter(x=>!x.naturalWidth).map(x=>x.src))};
 if(result.errors.length||result.failed.length)throw Error(JSON.stringify(result));
 await writeFile(new URL('browser-v2-1/gallery-review.json',import.meta.url),JSON.stringify({...result,result:'PASS',testedAt:new Date().toISOString()},null,2)+'\n');
 console.log(JSON.stringify(result));
}finally{await browser.close();}
