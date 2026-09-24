// Read-only canonical component rendering. This evidence harness never mounts the product app.
import {readFile,writeFile,mkdir,unlink} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const canonical=process.env.FORWARDER_CANONICAL||'D:/1-webapp/15-forwarder-golden-20260921';
const target=path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/,'$1'));
const {build}=await import(pathToFileURL(path.join(canonical,'node_modules/esbuild/lib/main.js')));
const files=['src/index.css','tailwind.config.ts','src/components/ui/button.tsx','src/components/ui/input.tsx','src/components/ui/card.tsx','src/components/ui/tabs.tsx','src/components/ui/table.tsx','src/components/ui/badge.tsx','src/components/ui/switch.tsx','src/components/ui/textarea.tsx','src/components/ui/select.tsx','src/components/ui/dialog.tsx','src/components/Header.tsx','src/components/ApplicationNavigation.tsx','src/components/CustomerPortalLayout.tsx'];
const hashes={}; for(const f of files)hashes[f]=createHash('sha256').update(await readFile(path.join(canonical,f))).digest('hex');
const ui=canonical+'/src/components/ui';
const source=`
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {Button} from '${ui}/button';
import {Input} from '${ui}/input';
import {Textarea} from '${ui}/textarea';
import {Card,CardHeader,CardTitle,CardDescription,CardContent} from '${ui}/card';
import {Tabs,TabsList,TabsTrigger} from '${ui}/tabs';
import {Table,TableHeader,TableBody,TableRow,TableHead,TableCell} from '${ui}/table';
import {Badge} from '${ui}/badge';
import {Switch} from '${ui}/switch';
const Form=()=> <Card><CardHeader><CardTitle>اطلاعات حمل نمایشی</CardTitle><CardDescription>نمونهٔ ایزوله از کنترل‌های واقعی کد فعلی Forwarder</CardDescription></CardHeader><CardContent><div className="grid gap-4"><label className="grid gap-2 text-sm">عنوان نمونه<Input defaultValue="پرونده حمل نمایشی"/></label><label className="grid gap-2 text-sm">مقصد نمونه<Input defaultValue="مقصد آزمایشی"/></label><label className="grid gap-2 text-sm">توضیح<Textarea defaultValue="فقط برای مقایسه ظاهر؛ داده‌ها ساختگی‌اند."/></label><div className="flex items-center gap-3"><Switch checked aria-label="وضعیت نمونه"/><span>فعال</span></div><div className="flex flex-wrap gap-2"><Button>ثبت نمونه</Button><Button variant="outline">انصراف</Button><Button variant="ghost">جزئیات</Button></div></div></CardContent></Card>;
const App=()=> <><p className="bg-muted px-4 py-2 text-sm text-center">مرجع محلی · رندر componentهای فعلی با داده‌های ساختگی · صفحه واقعی محصول نیست</p><header className="border-b bg-white/90 px-6 py-4 flex justify-between items-center"><b className="text-lg">Forwarder</b><Button variant="outline" size="sm">خانه</Button></header><main className="mx-auto max-w-6xl px-4 py-8"><div className="mb-6"><h1 className="text-2xl font-semibold">مرجع ظاهر Forwarder فعلی</h1><p className="mt-2 text-sm text-muted-foreground">رنگ، فرم، دکمه، کارت، زبانه و جدول از کد canonical</p></div><section id="reference-navigation" className="mb-6"><Tabs defaultValue="one" dir="rtl"><TabsList><TabsTrigger value="one">نمای کلی</TabsTrigger><TabsTrigger value="two">اطلاعات</TabsTrigger><TabsTrigger value="three">اسناد</TabsTrigger></TabsList></Tabs></section><div className="grid gap-6 md:grid-cols-2"><section id="reference-form"><Form/></section><section id="reference-panel"><Card><CardHeader><CardTitle>خلاصه پرونده نمایشی</CardTitle><CardDescription>الگوی Card با فاصله داخلی ۲۴ پیکسل</CardDescription></CardHeader><CardContent><div className="flex flex-wrap gap-2 mb-6"><Badge>در حال حمل</Badge><Badge variant="secondary">تکمیل‌شده</Badge><Badge variant="outline">در انتظار بررسی</Badge></div><Table><TableHeader><TableRow><TableHead className="text-right">کالای نمایشی</TableHead><TableHead className="text-right">مقدار</TableHead></TableRow></TableHeader><TableBody><TableRow><TableCell>کالای آزمایشی اول</TableCell><TableCell>۱۰ کارتن</TableCell></TableRow><TableRow data-state="selected"><TableCell>کالای آزمایشی دوم</TableCell><TableCell>۲۰ پالت</TableCell></TableRow></TableBody></Table></CardContent></Card><p className="mt-4 text-sm text-muted-foreground">ناوبری واقعی Header و CustomerPortalLayout با context برنامه کار می‌کند؛ این پوسته بازسازی چیدمان است، نه رندر آن دو component.</p></section></div></main></>;
process.stdout.write(renderToStaticMarkup(<App/>));`;
const bundle=path.join(target,'.reference-render.cjs');
await build({stdin:{contents:source,loader:'tsx',resolveDir:canonical},bundle:true,platform:'node',format:'cjs',outfile:bundle,alias:{'@':canonical+'/src'},jsx:'automatic',nodePaths:[canonical+'/node_modules']});
const markup=execFileSync(process.execPath,[bundle],{encoding:'utf8'}); await unlink(bundle);
await writeFile(path.join(target,'reference-current.html'),`<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; connect-src 'none'; script-src 'none'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:"><link rel="icon" href="data:,"><title>Forwarder current — isolated source render</title><link rel="stylesheet" href="reference-current.css"><style>@font-face{font-family:Vazirmatn;src:url('./assets/Vazirmatn.ttf');font-weight:100 900}*{transition:none!important}</style></head><body>${markup}</body></html>`);
// Content includes the JSX source as well as canonical source for the exact canonical utilities.
const input=path.join(target,'.reference-content.tsx'); await writeFile(input,source);
execFileSync(process.execPath,[canonical+'/node_modules/tailwindcss/lib/cli.js','-c',canonical+'/tailwind.config.ts','-i',canonical+'/src/index.css','--content',input+','+target+'/reference-current.html','-o',target+'/reference-current.css','--minify'],{cwd:canonical,stdio:'pipe'}); await unlink(input);
await mkdir(path.join(target,'../evidence/browser-v2-1'),{recursive:true});
await writeFile(path.join(target,'../evidence/browser-v2-1/reference-source.json'),JSON.stringify({canonical,head:execFileSync('git',['-C',canonical,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),hashes,renderedComponents:['Button','Input','Textarea','Card','Tabs','Table','Badge','Switch'],sourceOnly:['Select','Dialog','Header','ApplicationNavigation','CustomerPortalLayout'],data:'SYNTHETIC_ONLY',runtimeMounted:false},null,2)+'\n');
