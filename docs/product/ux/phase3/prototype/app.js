(() => {
  "use strict";

  const app = document.querySelector("#app");
  const dialogLayer = document.querySelector(".dialog-layer");
  const toastRegion = document.querySelector(".toast-region");
  const dialogTemplate = document.querySelector("#dialog-template");

  const state = {
    role: "expert",
    expertSection: "overview",
    customerSection: "summary",
    adminSection: "catalog",
    scenario: "normal",
    routeView: "planned",
    documentContext: "all",
    catalogActive: { truck: true, rail: true, reeferWagon: false, container40: true },
  };

  const expertSections = [
    ["overview", "◉", "نمای کلی", "۲"],
    ["relations", "◎", "مشتری‌ها و درخواست‌ها", "۳"],
    ["cargo", "▣", "کالاها", "۴"],
    ["route", "↝", "مسیر", "۴"],
    ["transport", "▤", "اجرای حمل", "۵"],
    ["allocation", "⇄", "تخصیص کالا", "۱"],
    ["documents", "▧", "اسناد", "۶"],
    ["timeline", "◷", "اجرا و Timeline", "۹"],
    ["issues", "!", "مشکلات و پیگیری‌ها", "۲"],
    ["deliveries", "✓", "تحویل‌ها", "۳"],
    ["closure", "◇", "تکمیل و بستن", "۲"],
  ];

  const customerSections = [
    ["summary", "خلاصه"],
    ["timeline", "مسیر و رویدادها"],
    ["cargo", "کالای من"],
    ["documents", "اسناد من"],
    ["delivery", "تحویل"],
  ];

  const adminSections = [
    ["catalog", "تعاریف مرجع سازمان"],
    ["route-times", "زمان مرجع مسیر"],
    ["closure-rules", "الزامات بستن پرونده"],
    ["closure-exceptions", "بررسی استثنای بستن"],
  ];

  const status = (label, tone = "current") => `<span class="status ${tone}">${label}</span>`;
  const button = (label, attrs = "", kind = "") => `<button type="button" class="button ${kind}" ${attrs}>${label}</button>`;

  function shipmentHero() {
    return `
      <section class="shipment-hero" aria-label="خلاصه ثابت پرونده حمل S-100">
        <div class="hero-main">
          <div>
            <div class="hero-title"><h1>پرونده حمل S-100</h1>${status("در حال حمل", "current")}</div>
            <p>حمل مشترک قطعات صنعتی · چین به ایران · مسئول پرونده: نرگس احمدی</p>
          </div>
          <div class="hero-meta">${status("TARGET_PHASE3_UX", "shared")}${status("داده ساختگی", "internal")}</div>
        </div>
        <div class="hero-grid">
          <div class="hero-stat"><small>مرحله فعلی</small><strong>خورگوس ← آکتائو</strong><em>حمل ریلی · مرحله ۲ از ۴</em></div>
          <div class="hero-stat"><small>آخرین موقعیت گزارش‌شده</small><strong>نزدیک آلماتی</strong><em>گزارش شرکت حمل · ۱۴:۳۰</em></div>
          <div class="hero-stat"><small>ETA مقصد نهایی</small><strong>۲۳ تا ۲۸ روز</strong><em>بازه تخمینی، نه زمان قطعی</em></div>
          <div class="hero-stat"><small>نقطه مهم بعدی</small><strong>آکتائو</strong><em>۲ تا ۳ روز</em></div>
          <div class="hero-stat"><small>تازگی اطلاعات</small><strong>تازه</strong><em>آخرین همگام‌سازی ۶ دقیقه قبل</em></div>
        </div>
      </section>`;
  }

  function expertShell(content) {
    return `
      <div class="workspace-layout">
        <aside class="workspace-aside" aria-label="بخش‌های پرونده حمل">
          <div class="aside-head"><strong>پرونده حمل S-100</strong><span>حرکت بین حوزه‌ها بدون از دست‌دادن زمینه</span></div>
          <nav class="section-nav">
            ${expertSections.map(([key, icon, label, count]) => `
              <button type="button" data-expert-section="${key}" class="${state.expertSection === key ? "is-active" : ""}" ${state.expertSection === key ? 'aria-current="page"' : ""}>
                <span class="nav-icon" aria-hidden="true">${icon}</span><span>${label}</span><span class="nav-count">${count}</span>
              </button>`).join("")}
          </nav>
        </aside>
        <main id="main-content" class="workspace-main">
          ${shipmentHero()}
          ${state.scenario === "stale" ? staleBanner() : ""}
          ${content}
        </main>
      </div>`;
  }

  function staleBanner() {
    return `<div class="card tint-amber" role="alert" style="margin-bottom:14px">
      <div class="card-head"><div><h2>اطلاعات پایش به‌روز نیست</h2><p>آخرین ارزیابی موفق: دیروز، ۱۸:۴۰</p></div>${status("قدیمی / STALE", "stale")}</div>
      <p class="no-margin">ممکن است موارد جدید نیازمند توجه هنوز دیده نشده باشند. نبود هشدار در این وضعیت به معنی سلامت عملیات نیست.</p>
    </div>`;
  }

  function expertOverview() {
    return `
      <section class="card tint-blue next-action">
        <div class="action-line">
          <div><p class="eyebrow">قدم بعدی پیشنهادی · قانون مشخص</p><h2>۱۰ کارتن فیلتر صنعتی را به واحد حمل تخصیص دهید</h2><p>مرحله خورگوس ← آکتائو فعال است و این مقدار هنوز بدون واحد حمل مانده است.</p></div>
          ${button("باز کردن تخصیص", 'data-expert-section="allocation"', "primary")}
        </div>
      </section>

      <div class="section-title"><div><h2>تصویر کاری همین حالا</h2><p>اطلاعات ناقص از مشکل واقعی جداست.</p></div></div>
      <div class="grid two">
        <section class="card">
          <div class="card-head"><div><h2>نیازمند توجه</h2><p>مواردی که اثر عملیاتی یا زمان‌دار دارند</p></div>${status("۲ مورد", "attention")}</div>
          <div class="attention-list">
            <article class="attention-item problem"><span class="rail"></span><div><h3>تأخیر در تحویل سند واگن</h3><p>اثر: احتمال ۱ روز توقف در آکتائو · پیگیری تا امروز ۱۷:۰۰</p></div>${button("بررسی", 'data-expert-section="issues"', "small")}</article>
            <article class="attention-item"><span class="rail"></span><div><h3>۱۰ کارتن هنوز تخصیص نیافته است</h3><p>کالای مشتری B · مرحله جاری · مانع شروع واحد سوم</p></div>${button("تخصیص", 'data-dialog="allocation"', "small")}</article>
          </div>
        </section>
        <section class="card">
          <div class="card-head"><div><h2>اطلاعات در انتظار تکمیل</h2><p>کار ادامه دارد؛ این موارد مشکل عملیاتی نیستند</p></div>${status("۳ مورد", "incomplete")}</div>
          <div class="attention-list">
            <article class="attention-item incomplete"><span class="rail"></span><div><h3>HS Code کالای مشتری C کامل نشده</h3><p>تا پیش از مرحله گمرک الزامی نیست.</p></div>${button("مشاهده کالا", 'data-expert-section="cargo"', "small")}</article>
            <article class="attention-item incomplete"><span class="rail"></span><div><h3>پلاک کامیون TR-24 دریافت نشده</h3><p>نوع وسیله و شرکت حمل مشخص است.</p></div>${button("اجرای حمل", 'data-expert-section="transport"', "small")}</article>
          </div>
        </section>
      </div>

      <div class="grid three" style="margin-top:14px">
        <section class="card"><div class="card-head"><div><h3>پیشرفت پرونده</h3><p>وضعیت‌های معنادار، بدون درصد ساختگی</p></div></div><ul class="metric-list"><li><span>تعریف کالا و مشتری</span>${status("کامل", "complete")}</li><li><span>برنامه مسیر</span>${status("کامل", "complete")}</li><li><span>تخصیص کالا</span>${status("ناقص", "incomplete")}</li><li><span>اجرای حمل</span>${status("در جریان", "current")}</li><li><span>بستن پرونده</span>${status("مسدود", "blocked")}</li></ul></section>
        <section class="card"><div class="card-head"><div><h3>مشتری‌ها و وضعیت تحویل</h3><p>وضعیت Shipment از یک مشتری تبعیت نمی‌کند</p></div></div><ul class="metric-list"><li><span>پارس موتور آریا</span>${status("تحویل‌شده", "complete")}</li><li><span>آرمان تجهیز شرق</span>${status("در حال حمل", "current")}</li><li><span>راهکار پلیمر سپهر</span>${status("در انتظار گمرک", "attention")}</li></ul></section>
        <section class="card"><div class="card-head"><div><h3>فعالیت معنادار اخیر</h3><p>جزئیات کامل در Timeline</p></div>${button("Timeline", 'data-expert-section="timeline"', "small")}</div><ul class="metric-list"><li><span>۱۴:۳۰</span><b>گزارش موقعیت اصلاح شد</b></li><li><span>۱۲:۱۰</span><b>پیگیری Carrier ثبت شد</b></li><li><span>دیروز</span><b>انتقال ۴۰ کارتن انجام شد</b></li></ul></section>
      </div>`;
  }

  function expertRelations() {
    return `
      <div class="page-heading"><div><p class="eyebrow">DEFINE · منبع تجاری</p><h1>مشتری‌ها و درخواست‌های مرتبط</h1><p>مشتری‌های پرونده از مالک هر Cargo به دست می‌آیند؛ Shipment فهرست عضویت مستقل مشتری ندارد.</p></div><div class="heading-actions">${button("افزودن از درخواست", 'data-dialog="link-request"', "primary")}</div></div>
      <section class="card tint-blue" style="margin-bottom:14px"><div class="card-head"><div><h2>پیوند تجاری حفظ شده است</h2><p>Request نیاز مشتری است؛ Shipment اجرای عملیاتی. پذیرش قیمت، Shipment را خودکار نمی‌سازد.</p></div>${status("۳ مشتری · ۳ درخواست", "shared")}</div></section>
      <div class="grid three">
        ${customerRelationCard("A", "پارس موتور آریا", "RQ-8421", "۲ قلم کالا", "تحویل‌شده", "complete")}
        ${customerRelationCard("B", "آرمان تجهیز شرق", "RQ-8428", "۱ قلم کالا", "در حال حمل", "current")}
        ${customerRelationCard("C", "راهکار پلیمر سپهر", "RQ-8434", "۱ قلم کالا", "در انتظار گمرک", "attention")}
      </div>
      <div class="section-title"><div><h2>مرز حریم خصوصی</h2><p>اشتراک وسیله، دامنه دید مشتری‌ها را گسترش نمی‌دهد.</p></div></div>
      <div class="table-wrap"><table><thead><tr><th>واقعیت</th><th>کارشناس</th><th>مشتری A</th><th>مشتری B/C</th></tr></thead><tbody>
        <tr><td>هویت و Cargo مشتری A</td><td>قابل مشاهده</td><td>${status("قابل مشاهده", "complete")}</td><td>${status("پنهان", "internal")}</td></tr>
        <tr><td>وضعیت مشترک مرحله حمل</td><td>کامل</td><td>${status("نسخه امن", "shared")}</td><td>${status("نسخه امن", "shared")}</td></tr>
        <tr><td>علت داخلی نقص سند مشتری B</td><td>قابل مشاهده</td><td>${status("پنهان", "internal")}</td><td>${status("فقط مالک مربوط", "customer")}</td></tr>
      </tbody></table></div>`;
  }

  function customerRelationCard(letter, name, request, cargo, stage, tone) {
    return `<article class="card"><div class="card-head"><div><p class="eyebrow">مشتری ${letter}</p><h2>${name}</h2></div>${status(stage, tone)}</div><dl class="detail-list"><div class="detail-row"><dt>درخواست منبع</dt><dd>${request}</dd></div><div class="detail-row"><dt>کالای این مشتری</dt><dd>${cargo}</dd></div><div class="detail-row"><dt>دسترسی Customer</dt><dd>فقط داده خود</dd></div></dl></article>`;
  }

  function expertCargo() {
    return `
      <div class="page-heading"><div><p class="eyebrow">DEFINE · اقلام کالا</p><h1>کالاها</h1><p>هویت، مشتری مالک و درخواست منبع هر Cargo مستقل باقی می‌ماند؛ نقص اطلاعات با حادثه عملیاتی یکی نیست.</p></div><div class="heading-actions">${button("افزودن کالا", 'data-dialog="add-cargo"', "primary")}</div></div>
      <div class="table-wrap"><table><thead><tr><th>کالا و مالک</th><th>درخواست مشتری</th><th>برنامه حمل</th><th>واقعی</th><th>جزئیات استاندارد</th><th>مقصد</th></tr></thead><tbody>
        <tr><td><div class="cell-title">قطعات موتور A1</div><div class="cell-sub">پارس موتور آریا · RQ-8421</div></td><td><b>۱۰۰</b> کارتن</td><td><b>۱۰۰</b> کارتن</td><td><b>۱۰۰</b> کارتن</td><td>HS 8409.91 · پالت/کارتن</td><td>تهران / قزوین</td></tr>
        <tr><td><div class="cell-title">فیلتر صنعتی B1</div><div class="cell-sub">آرمان تجهیز شرق · RQ-8428</div></td><td><b>۱۰۰</b> کارتن</td><td><b>۹۰</b> کارتن</td><td><b>۸۷</b> کارتن</td><td>HS 8421.99 · کارتن</td><td>قزوین</td></tr>
        <tr><td><div class="cell-title">رزین پلیمری C1</div><div class="cell-sub">راهکار پلیمر سپهر · RQ-8434</div></td><td><b>۱۲</b> جامبوبگ</td><td><b>۱۲</b> جامبوبگ</td><td><b>—</b></td><td>${status("HS Code هنوز تکمیل نشده", "incomplete")}</td><td>کرج</td></tr>
        <tr><td><div class="cell-title">بوش فلزی A2</div><div class="cell-sub">پارس موتور آریا · RQ-8421</div></td><td><b>۲۴</b> پالت</td><td><b>۲۴</b> پالت</td><td><b>۲۴</b> پالت</td><td>HS 8483.30 · پالت</td><td>تهران</td></tr>
      </tbody></table></div>
      <div class="section-title"><div><h2>مقایسه مقدار درخواستی، برنامه و واقعی</h2><p>اختلاف‌ها روبه‌روی هم دیده می‌شوند و هیچ مقدار قبلی بازنویسی نمی‌شود.</p></div></div>
      <section class="card">
        <div class="card-head"><div><h2>فیلتر صنعتی B1</h2><p>آرمان تجهیز شرق · واحد: کارتن</p></div>${status("۳ کارتن کمتر از برنامه", "attention")}</div>
        <div class="grid three"><div><span class="subtle">درخواست مشتری</span><h2>۱۰۰</h2><div class="progress-track"><span style="width:100%"></span></div></div><div><span class="subtle">برنامه حمل</span><h2>۹۰</h2><div class="progress-track warn"><span style="width:90%"></span></div></div><div><span class="subtle">واقعی</span><h2>۸۷</h2><div class="progress-track ok"><span style="width:87%"></span></div></div></div>
      </section>`;
  }

  function expertRoute() {
    return `
      <div class="page-heading"><div><p class="eyebrow">DEFINE · مسیر و مراحل</p><h1>مسیر برنامه‌ریزی‌شده و واقعی</h1><p>واقعیت اجرا جای برنامه را پاک نمی‌کند؛ انحراف مسیر نیز تا وقتی اثر عملیاتی ندارد، مشکل محسوب نمی‌شود.</p></div><div class="view-toggle" aria-label="نوع مسیر"><button type="button" data-route-view="planned" class="${state.routeView === "planned" ? "is-active" : ""}">برنامه‌ریزی‌شده</button><button type="button" data-route-view="actual" class="${state.routeView === "actual" ? "is-active" : ""}">واقعی</button></div></div>
      ${state.routeView === "planned" ? plannedRoute() : actualRoute()}
      <div class="section-title"><div><h2>شاخه مقصدها پس از هاب تهران</h2><p>شاخه‌ها به‌شکل فهرست مسیرهای مقصد نمایش داده می‌شوند، نه نمودار شبکه پیچیده.</p></div></div>
      <section class="card"><div class="branch-grid"><div class="branch-root">هاب تهران<br><small>پایان مسیر مشترک</small></div><div class="branch-lines"><div class="branch-line"><span><b>پارس موتور آریا</b> · A2</span><b>تهران</b></div><div class="branch-line"><span><b>پارس موتور آریا + آرمان تجهیز</b> · A1/B1</span><b>قزوین</b></div><div class="branch-line"><span><b>راهکار پلیمر سپهر</b> · C1</span><b>کرج</b></div></div></div></section>`;
  }

  function plannedRoute() {
    return `<section class="card"><div class="card-head"><div><h2>برنامه مسیر · نسخه ۳</h2><p>آخرین بازبرنامه‌ریزی: ۲۲ شهریور · دلیل: ظرفیت قطار</p></div>${status("نسخه فعال", "current")}</div><div class="route-strip">
      ${routeNode("۱", "شانگهای", "خورگوس", "جاده‌ای", "۶–۸ روز", "complete")}
      ${routeNode("۲", "خورگوس", "آکتائو", "ریلی", "۴–۶ روز", "current")}
      ${routeNode("۳", "آکتائو", "بندر انزلی", "دریایی", "۸–۱۰ روز", "")}
      ${routeNode("۴", "انزلی", "هاب تهران", "جاده‌ای", "۲–۳ روز", "")}
    </div></section>`;
  }

  function actualRoute() {
    return `<section class="card"><div class="card-head"><div><h2>مسیر واقعی تا امروز</h2><p>زمان وقوع و زمان ثبت جدا نگه داشته می‌شوند.</p></div>${status("مرحله ۲ در جریان", "current")}</div><div class="route-strip">
      ${routeNode("۱", "شانگهای", "خورگوس", "رسید ۲۰ شهریور", "۷ روز", "complete")}
      ${routeNode("۲", "خورگوس", "نزدیک آلماتی", "آخرین گزارش ۱۴:۳۰", "در جریان", "current")}
      ${routeNode("۳", "آکتائو", "بندر انزلی", "هنوز شروع نشده", "—", "")}
      ${routeNode("۴", "انزلی", "هاب تهران", "هنوز شروع نشده", "—", "")}
    </div><div class="card tint-amber flat" style="margin-top:12px"><b>تفاوت با برنامه:</b> توقف ۶ ساعته در خورگوس ثبت شد؛ چون اثر مهمی بر ETA فعلی ندارد، Exception ساخته نشده است.</div></section>`;
  }

  function routeNode(num, origin, destination, mode, time, currentClass) {
    return `<article class="route-node ${currentClass === "current" ? "current" : ""}"><small>مرحله ${num}</small><strong>${origin} ← ${destination}</strong><span>${mode}</span><div class="route-time">${time}</div>${currentClass === "complete" ? status("تکمیل", "complete") : currentClass === "current" ? status("جاری", "current") : status("آینده", "internal")}</article>`;
  }

  function expertTransport() {
    return `
      <div class="page-heading"><div><p class="eyebrow">ASSIGN · اجرای مرحله مسیر</p><h1>وسایل، واحدهای حمل و شرکت‌های حمل‌کننده</h1><p>وسیله حمل، واحد/ظرف حمل و Carrier سه مفهوم جدا هستند و به اجرای یک Route Leg تعلق دارند.</p></div><div class="heading-actions">${button("تعریف اجرای مرحله", 'data-dialog="transport"', "primary")}</div></div>
      <section class="card tint-blue" style="margin-bottom:14px"><div class="card-head"><div><h2>مرحله ۲ · خورگوس ← آکتائو</h2><p>۳ اجرای هم‌زمان · ۲ Carrier · حمل ریلی/جاده‌ای انتقالی</p></div>${status("در حال اجرا", "current")}</div></section>
      <div class="grid three">
        ${executionCard("TR-12", "کامیون کشنده", "تریلر T-12", "راه ابریشم نو", "پلاک ۸۷ع۵۴۳ ایران۴۴", "complete")}
        ${executionCard("TR-18", "کامیون کشنده", "تریلر T-18", "راه ابریشم نو", "پلاک ۲۳ب۷۸۱ ایران۱۱", "complete")}
        ${executionCard("TR-24", "کامیون کشنده", "تریلر T-24", "ترابر خزر", "پلاک هنوز دریافت نشده", "incomplete")}
        ${executionCard("RL-07", "قطار باری", "واگن W-07 ← کانتینر C-771", "ریل آسیای مرکزی", "شماره قطار KZ-204", "current")}
        ${executionCard("RL-09", "قطار باری", "واگن W-09 ← کانتینر C-804", "ریل آسیای مرکزی", "شماره قطار KZ-204", "current")}
      </div>
      <section class="card tint-amber" style="margin-top:14px"><div class="card-head"><div><h2>تعریف پایه «واگن یخچالی» فعال نیست</h2><p>برای اقدام وابسته به این نوع، کارشناس باید منتظر فعال‌سازی مدیر سازمان بماند؛ سایر کارهای پرونده قابل ادامه‌اند.</p></div>${button("مشاهده مسیر مدیر", 'data-role="admin" data-admin-section="catalog"', "")}</div></section>`;
  }

  function executionCard(id, means, equipment, carrier, detail, tone) {
    const label = tone === "incomplete" ? "اطلاعات ناقص" : tone === "current" ? "در حرکت" : "آماده";
    return `<article class="execution-card"><div class="execution-top"><div><p class="eyebrow">اجرای ${id}</p><h3 class="no-margin">${means}</h3></div>${status(label, tone)}</div><div class="execution-hierarchy"><span class="hierarchy-node">وسیله: ${means}</span><span aria-hidden="true">←</span><span class="hierarchy-node">واحد: ${equipment}</span><span aria-hidden="true">←</span><span class="hierarchy-node">کالا</span></div><p class="no-margin"><b>Carrier:</b> ${carrier}</p><p class="subtle tiny no-margin">${detail}</p></article>`;
  }

  function expertAllocation() {
    return `
      <div class="page-heading"><div><p class="eyebrow">ASSIGN · تخصیص</p><h1>تخصیص کالا به واحدهای حمل</h1><p>نمای دوطرفه نشان می‌دهد هر Cargo کجا قرار دارد و هر واحد حمل، کالای کدام مشتری‌ها را حمل می‌کند.</p></div><div class="heading-actions">${button("ثبت تخصیص", 'data-dialog="allocation"', "primary")}${button("انتقال کالا", 'data-dialog="transfer"')}</div></div>
      <div class="grid two">
        <section class="card"><div class="card-head"><div><h2>بر اساس کالا</h2><p>مقدار کل، تخصیص‌یافته و باقی‌مانده</p></div></div>
          ${allocationRow("A1 · قطعات موتور", "پارس موتور آریا", 100, 100, "TR-12: ۶۰ · TR-18: ۴۰", "ok")}
          ${allocationRow("B1 · فیلتر صنعتی", "آرمان تجهیز شرق", 90, 80, "TR-12: ۳۰ · TR-24: ۵۰", "warn")}
          ${allocationRow("C1 · رزین پلیمری", "راهکار پلیمر سپهر", 12, 12, "W-09: ۱۲ جامبوبگ", "ok")}
        </section>
        <section class="card"><div class="card-head"><div><h2>بر اساس واحد حمل</h2><p>ترکیب چندمشتری بدون مخلوط‌شدن مالکیت</p></div></div>
          <div class="attention-list"><article class="attention-item"><span class="rail" style="background:var(--blue)"></span><div><h3>TR-12 · تریلر T-12</h3><p>مشتری A: ۶۰ کارتن · مشتری B: ۳۰ کارتن</p></div>${status("مشترک", "shared")}</article><article class="attention-item"><span class="rail" style="background:var(--cyan)"></span><div><h3>TR-18 · تریلر T-18</h3><p>مشتری A: ۴۰ کارتن</p></div>${status("تک‌مشتری", "customer")}</article><article class="attention-item"><span class="rail" style="background:var(--violet)"></span><div><h3>W-09 · واگن / کانتینر C-804</h3><p>مشتری C: ۱۲ جامبوبگ</p></div>${status("تک‌مشتری", "customer")}</article></div>
        </section>
      </div>
      <section class="card tint-amber" style="margin-top:14px"><div class="action-line"><div><p class="eyebrow">تخصیص ناقص مجاز است</p><h2>۱۰ کارتن از B1 هنوز تخصیص نیافته است</h2><p>کار ادامه دارد، اما شروع اجرای واحد سوم تا تخصیص یا تصمیم روشن، نیازمند توجه است.</p></div>${button("تکمیل تخصیص", 'data-dialog="allocation"', "primary")}</div></section>
      <div class="section-title"><div><h2>تاریخچه تغییرات تخصیص</h2><p>تغییر عملیاتی با فرمان «انتقال کالا» ثبت می‌شود؛ مقدار قبلی ویرایش خام نمی‌شود.</p></div></div>
      <div class="table-wrap"><table><thead><tr><th>زمان</th><th>کالا</th><th>تغییر</th><th>نقطه عملیاتی</th><th>ثبت‌کننده</th></tr></thead><tbody><tr><td>دیروز ۱۶:۴۰</td><td>A1</td><td>انتقال ۴۰ کارتن از TR-12 به TR-18</td><td>پایانه خورگوس</td><td>نرگس احمدی</td></tr><tr><td>۲۰ شهریور ۱۰:۱۵</td><td>B1</td><td>تخصیص اولیه ۳۰ کارتن به TR-12</td><td>انبار شانگهای</td><td>نرگس احمدی</td></tr></tbody></table></div>`;
  }

  function allocationRow(title, customer, total, allocated, units, tone) {
    const remaining = total - allocated;
    return `<article style="padding:11px 0;border-bottom:1px solid var(--line)"><div class="card-head" style="margin-bottom:7px"><div><h3>${title}</h3><p>${customer}</p></div>${remaining ? status(`${remaining} باقی‌مانده`, "incomplete") : status("کامل", "complete")}</div><div class="progress-track ${tone}"><span style="width:${Math.round(allocated/total*100)}%"></span></div><div class="quantity-row"><div class="quantity-values"><span>کل <b>${total}</b></span><span>تخصیص <b>${allocated}</b></span><span>باقی‌مانده <b>${remaining}</b></span></div><small class="subtle">${units}</small></div></article>`;
  }

  function expertDocuments() {
    const docs = {
      all: [
        ["CMR حمل مشترک", "Shipment · مرحله خورگوس–آکتائو", "مشترک و قابل نمایش", "shared"],
        ["Commercial Invoice A", "Cargo A1 · پارس موتور آریا", "مخصوص مشتری مربوط", "customer"],
        ["Packing List B", "Cargo B1 · آرمان تجهیز شرق", "مخصوص مشتری مربوط", "customer"],
        ["صورت‌حساب Carrier", "اجرای TR-12 · راه ابریشم نو", "داخلی", "internal"],
        ["رسید تحویل ۱", "Delivery A1 · تهران", "مخصوص مشتری مربوط", "customer"],
        ["رسید تحویل ۲", "Delivery A1 · قزوین", "فایل دریافت نشده", "incomplete"],
      ],
      cargoA: [
        ["Commercial Invoice A", "Cargo A1 · پارس موتور آریا", "مخصوص مشتری مربوط", "customer"],
        ["Packing List A", "Cargo A1 · پارس موتور آریا", "مخصوص مشتری مربوط", "customer"],
        ["CMR حمل مشترک", "Shipment · مرتبط با Cargo A1", "مشترک و قابل نمایش", "shared"],
      ],
      truck12: [
        ["CMR حمل مشترک", "اجرای TR-12", "مشترک و قابل نمایش", "shared"],
        ["مجوز تردد", "وسیله TR-12", "داخلی", "internal"],
        ["صورت‌حساب Carrier", "Carrier راه ابریشم نو", "داخلی", "internal"],
      ],
    };
    const activeDocs = docs[state.documentContext];
    return `
      <div class="page-heading"><div><p class="eyebrow">CONTEXT · اسناد و visibility</p><h1>اسناد</h1><p>زمینه سند و مجوز دیدن آن مستقل‌اند. ارتباط با حمل مشترک، سند را برای همه مشتری‌ها قابل مشاهده نمی‌کند.</p></div><div class="heading-actions">${button("افزودن سند", 'data-dialog="document"', "primary")}</div></div>
      <div class="tabs" role="tablist" aria-label="زمینه اسناد" style="width:fit-content;margin-bottom:14px"><button class="tab-button ${state.documentContext === "all" ? "is-active" : ""}" data-doc-context="all">همه اسناد</button><button class="tab-button ${state.documentContext === "cargoA" ? "is-active" : ""}" data-doc-context="cargoA">در زمینه Cargo A1</button><button class="tab-button ${state.documentContext === "truck12" ? "is-active" : ""}" data-doc-context="truck12">در زمینه TR-12</button></div>
      <section class="card"><div class="card-head"><div><h2>${state.documentContext === "all" ? "مدیریت همه اسناد" : state.documentContext === "cargoA" ? "اسناد مرتبط با Cargo A1" : "اسناد مرتبط با TR-12"}</h2><p>نسخه، وضعیت فایل، زمینه و visibility در هر ردیف مشخص است.</p></div>${status(`${activeDocs.length} مورد`, "internal")}</div><div class="document-list">${activeDocs.map((d, i) => documentRow(...d, i)).join("")}</div></section>`;
  }

  function documentRow(name, context, visibility, tone, index) {
    return `<article class="document-row"><div><h3>${name}</h3><p>${context} · نسخه ${index + 1} · آخرین تغییر ${index + 20} شهریور</p></div><div class="document-tags">${status(visibility, tone)}${visibility.includes("دریافت نشده") ? status("الزام باز", "blocked") : button("مشاهده", 'data-dialog="document-preview"', "small")}</div></article>`;
  }

  function expertTimeline() {
    return `
      <div class="page-heading"><div><p class="eyebrow">CHANGE · روایت اجرا</p><h1>اجرای حمل و Timeline</h1><p>Timeline روایت معنادار عملیات است، نه log خام. اصلاح‌ها و تغییر وسیله بدون پاک‌کردن گذشته دیده می‌شوند.</p></div><div class="heading-actions">${button("ثبت موقعیت", 'data-dialog="location"', "primary")}${button("ثبت رخداد", 'data-dialog="event"')}</div></div>
      <div class="grid two">
        <section class="card location-card"><div class="card-head"><div><p class="eyebrow" style="color:#a9dce0">آخرین موقعیت گزارش‌شده</p><h2>نزدیک آلماتی</h2></div>${status("گزارش عملیاتی", "shared")}</div><p>آخرین به‌روزرسانی: امروز ۱۴:۳۰</p><p>منبع: گزارش شرکت حمل</p><p class="tiny">این موقعیت GPS یا LIVE نیست.</p></section>
        <section class="card"><div class="card-head"><div><h2>ETA جاری</h2><p>بازه زمانی برای جلوگیری از دقت کاذب</p></div>${status("تازه", "complete")}</div><dl class="detail-list"><div class="detail-row"><dt>مقصد نهایی</dt><dd>۲۳ تا ۲۸ روز</dd></div><div class="detail-row"><dt>نقطه مهم بعدی: آکتائو</dt><dd>۲ تا ۳ روز</dd></div><div class="detail-row"><dt>مبنای ساده</dt><dd>مرجع مسیر + پیشرفت ثبت‌شده</dd></div></dl></section>
      </div>
      <section class="card" style="margin-top:14px"><div class="card-head"><div><h2>روایت عملیات</h2><p>رخدادهای کلیدی با گروه‌بندی روزانه</p></div>${button("فیلتر Timeline", 'data-dialog="timeline-filter"', "small")}</div>
        <ol class="timeline">
          ${timelineItem("۱۴:۳۰", "موقعیت گزارش‌شده اصلاح شد", "در مسیر آلماتی؛ آخرین گزارش معتبر", "corrected", '<div class="correction-note"><b>گزارش قبلی:</b> «رسیدن به مرز» در ۱۰:۰۰ بعداً اصلاح شد. گزارش قبلی حذف نشده است.</div>')}
          ${timelineItem("۱۲:۱۰", "پیگیری شرکت حمل ثبت شد", "زمان تحویل سند واگن تا ۱۷:۰۰ تأیید شد.", "")}
          ${timelineItem("۱۰:۰۰", "رسیدن به مرز گزارش شد", "این گزارش بعداً با دلیل «اشتباه در برداشت از پیام Carrier» اصلاح شد.", "corrected")}
          ${timelineItem("دیروز · ۱۶:۴۰", "۴۰ کارتن Cargo A1 منتقل شد", "از TR-12 به TR-18 در پایانه خورگوس؛ سابقه تخصیص حفظ شد.", "")}
          ${timelineItem("۲۰ شهریور · ۱۹:۱۵", "مرحله جاده‌ای تکمیل شد", "ورود سه کامیون به پایانه خورگوس تأیید شد.", "complete")}
          ${timelineItem("۱۹ شهریور · ۰۹:۰۰", "مشکل عملیاتی ثبت شد", "تأخیر سند واگن؛ اثر روی حمل مشترک.", "problem")}
        </ol>
      </section>`;
  }

  function timelineItem(time, title, text, tone = "", extra = "") {
    return `<li class="timeline-item"><span class="timeline-dot ${tone}">${tone === "complete" ? "✓" : tone === "problem" ? "!" : "•"}</span><div class="timeline-content"><h3>${title}</h3><p>${text}</p><p class="timeline-meta">${time} · ثبت‌کننده/منبع مجاز</p>${extra}</div></li>`;
  }

  function expertIssues() {
    return `
      <div class="page-heading"><div><p class="eyebrow">CHANGE · رسیدگی عملیاتی</p><h1>مشکلات، اقدام‌ها و Attention</h1><p>مشکل می‌گوید چه اتفاقی افتاده؛ اقدام می‌گوید چه کاری لازم است؛ Attention فقط اولویت بررسی را نشان می‌دهد.</p></div><div class="heading-actions">${button("ثبت مشکل", 'data-dialog="exception"', "primary")}${button("ثبت پیگیری", 'data-dialog="followup"')}</div></div>
      <section class="card tint-red"><div class="card-head"><div><p class="eyebrow" style="color:var(--red)">EX-204 · مشکل عملیاتی فعال</p><h2>تأخیر در تحویل سند واگن</h2><p>اثر: احتمال توقف یک‌روزه در آکتائو · شدت: مهم</p></div>${status("باز", "problem")}</div>
        <div class="grid two">
          <div class="card flat"><h3>توضیح داخلی</h3><p>اصل Packing List مشتری B هنوز توسط نماینده مبدا تأیید نشده و صدور سند واگن به تعویق افتاده است.</p>${status("فقط داخلی", "internal")}</div>
          <div class="card flat"><h3>پیام امن برای مشتریان متأثر</h3><p>یک مشکل عملیاتی در اسناد حمل ثبت شده و در حال پیگیری است. بازه ETA فعلی بدون تغییر است.</p>${status("قابل نمایش به مشتری", "shared")}</div>
        </div>
      </section>
      <div class="grid two" style="margin-top:14px">
        <section class="card"><div class="card-head"><div><h2>اقدام مرتبط AC-88</h2><p>دریافت تأیید سند از Carrier</p></div>${status("در پیگیری", "attention")}</div><dl class="detail-list"><div class="detail-row"><dt>مسئول</dt><dd>نرگس احمدی</dd></div><div class="detail-row"><dt>موعد</dt><dd>امروز ۱۷:۰۰</dd></div><div class="detail-row"><dt>SLA</dt><dd>${status("۱ ساعت تا هشدار", "attention")}</dd></div><div class="detail-row"><dt>آخرین نتیجه</dt><dd>Carrier زمان ارسال را تأیید کرد</dd></div></dl></section>
        <section class="card"><div class="card-head"><div><h2>اثر بر مشتری‌ها</h2><p>نتیجه‌محور و customer-scoped</p></div></div><ul class="metric-list"><li><span>مشتری A</span><b>پیام امن عمومی</b></li><li><span>مشتری B</span><b>پیام مربوط + درخواست سند</b></li><li><span>مشتری C</span><b>پیام امن عمومی</b></li></ul><p class="tiny subtle">اگر متن اختصاصی کارشناس خالی باشد، پیام امن پیش‌فرض deterministic نمایش داده می‌شود.</p></section>
      </div>`;
  }

  function expertDeliveries() {
    return `
      <div class="page-heading"><div><p class="eyebrow">CHANGE · ثبت تحویل</p><h1>تحویل‌ها</h1><p>هر Delivery مقدار، مقصد، زمان و evidence خود را دارد. تحویل یک مشتری، Shipment مشترک را نمی‌بندد.</p></div><div class="heading-actions">${button("ثبت تحویل", 'data-dialog="delivery"', "primary")}</div></div>
      <div class="grid three">
        <section class="card"><div class="card-head"><div><p class="eyebrow">مشتری A</p><h2>پارس موتور آریا</h2></div>${status("تحویل‌شده", "complete")}</div><p><b>Cargo A1 · ۱۰۰ کارتن</b></p><div class="progress-track ok"><span style="width:100%"></span></div><div class="quantity-values"><span>تحویل <b>۱۰۰</b></span><span>باقی‌مانده <b>۰</b></span></div></section>
        <section class="card"><div class="card-head"><div><p class="eyebrow">مشتری B</p><h2>آرمان تجهیز شرق</h2></div>${status("در حال حمل", "current")}</div><p><b>Cargo B1 · ۸۷ کارتن واقعی</b></p><div class="progress-track"><span style="width:0%"></span></div><div class="quantity-values"><span>تحویل <b>۰</b></span><span>در حمل <b>۸۷</b></span></div></section>
        <section class="card"><div class="card-head"><div><p class="eyebrow">مشتری C</p><h2>راهکار پلیمر سپهر</h2></div>${status("در انتظار گمرک", "attention")}</div><p><b>Cargo C1 · ۱۲ جامبوبگ</b></p><div class="progress-track warn"><span style="width:0%"></span></div><div class="quantity-values"><span>تحویل <b>۰</b></span><span>در گمرک <b>۱۲</b></span></div></section>
      </div>
      <div class="section-title"><div><h2>تحویل‌های Cargo A1</h2><p>تقسیم تحویل به مقصدهای متفاوت</p></div></div>
      <div class="table-wrap"><table><thead><tr><th>تحویل</th><th>مقدار</th><th>مکان</th><th>زمان</th><th>Evidence</th></tr></thead><tbody><tr><td>DL-301</td><td>۶۰ کارتن</td><td>تهران</td><td>۲۲ شهریور · ۱۰:۲۰</td><td>${status("رسید تأییدشده", "complete")}</td></tr><tr><td>DL-305</td><td>۴۰ کارتن</td><td>قزوین</td><td>۲۳ شهریور · ۱۷:۱۰</td><td>${status("فایل رسید مفقود", "blocked")}</td></tr></tbody></table></div>`;
  }

  function expertClosure() {
    return `
      <div class="page-heading"><div><p class="eyebrow">CONTROL · پایان پرونده</p><h1>آمادگی برای بستن پرونده</h1><p>تحویل کامل با بسته‌شدن Shipment یکی نیست. الزام‌های عمومی و modeهای استفاده‌شده از تنظیمات سازمان خوانده می‌شوند.</p></div><div class="heading-actions">${button("درخواست استثنا از مدیر", 'data-role="admin" data-admin-section="closure-exceptions"')}</div></div>
      <section class="card tint-red"><div class="action-line"><div><p class="eyebrow" style="color:var(--red)">نتیجه کنترل</p><h2>پرونده هنوز قابل بستن نیست</h2><p>۲ الزام mandatory تکمیل نشده‌اند. کارشناس امکان bypass ندارد.</p></div>${status("BLOCKED", "blocked")}</div></section>
      <div class="grid two" style="margin-top:14px">
        <section class="card"><div class="card-head"><div><h2>چک‌لیست بستن</h2><p>سیاست سازمان · حمل ترکیبی جاده/ریل/دریا</p></div>${status("۶ از ۸", "attention")}</div><div class="checklist">
          ${checkRow(true, "همه Cargoها تعیین تکلیف شده‌اند", "عمومی")}
          ${checkRow(true, "مقدار واقعی ثبت شده است", "عمومی")}
          ${checkRow(true, "تحویل‌ها ثبت شده‌اند", "عمومی")}
          ${checkRow(false, "رسید Delivery DL-305 موجود نیست", "الزام جاده")}
          ${checkRow(true, "مشکلات ضروری بسته شده‌اند", "عمومی")}
          ${checkRow(false, "پیگیری AC-88 هنوز باز است", "الزام عملیات")}
          ${checkRow(true, "سند واگن نسخه معتبر دارد", "الزام ریل")}
          ${checkRow(true, "گزارش تخلیه بندر ثبت شده", "الزام دریایی")}
        </div></section>
        <section class="card"><div class="card-head"><div><h2>توضیح کنترل</h2><p>چرا بسته‌شدن مسدود است؟</p></div></div><ol><li>فایل رسید تحویل دوم هنوز دریافت نشده است.</li><li>Action مربوط به سند واگن نتیجه نهایی ندارد.</li></ol><div class="card tint-amber flat"><b>راه‌های مجاز:</b><p>مدرک و نتیجه پیگیری را تکمیل کنید؛ یا در وضعیت استثنایی، درخواست دارای دلیل برای مدیر سازمان بفرستید.</p></div>${button("رفتن به اسناد", 'data-expert-section="documents"', "")}${button("رفتن به پیگیری", 'data-expert-section="issues"', "")}</section>
      </div>`;
  }

  function checkRow(pass, text, scope) {
    return `<div class="check-row ${pass ? "pass" : "fail"}"><span class="check-icon">${pass ? "✓" : "×"}</span><span>${text}</span><small class="subtle">${scope}</small></div>`;
  }

  function renderExpert() {
    const screens = {
      overview: expertOverview,
      relations: expertRelations,
      cargo: expertCargo,
      route: expertRoute,
      transport: expertTransport,
      allocation: expertAllocation,
      documents: expertDocuments,
      timeline: expertTimeline,
      issues: expertIssues,
      deliveries: expertDeliveries,
      closure: expertClosure,
    };
    return expertShell(screens[state.expertSection]());
  }

  function customerNav() {
    return `<nav class="customer-nav" aria-label="بخش‌های پرتال مشتری">${customerSections.map(([key, label]) => `<button type="button" class="tab-button ${state.customerSection === key ? "is-active" : ""}" data-customer-section="${key}" ${state.customerSection === key ? 'aria-current="page"' : ""}>${label}</button>`).join("")}</nav>`;
  }

  function customerSummary() {
    return `
      <div class="page-heading"><div><p class="eyebrow">حمل من · پرونده S-100</p><h1>پارس موتور آریا</h1><p>اطلاعات این صفحه فقط به کالا و اسناد شما محدود است.</p></div>${status("در حال حمل", "current")}</div>
      <div class="shared-note" role="note"><span aria-hidden="true">◎</span><div><b>این حمل با بار سایر مشتریان به‌صورت مشترک انجام می‌شود.</b><br><small>اطلاعات هویتی، کالا، اسناد و تحویل سایر مشتریان برای شما نمایش داده نمی‌شود.</small></div></div>
      <div class="customer-hero" style="margin-top:14px">
        <section class="card location-card"><p class="eyebrow" style="color:#a9dce0">آخرین موقعیت گزارش‌شده</p><h2>نزدیک آلماتی</h2><p>امروز ۱۴:۳۰ · گزارش شرکت حمل</p><p class="tiny">گزارش عملیاتی؛ نه GPS زنده</p></section>
        <section class="card"><div class="card-head"><div><h2>زمان تقریبی رسیدن</h2><p>آخرین به‌روزرسانی امروز ۱۴:۳۰</p></div></div><h1>۲۳ تا ۲۸ روز</h1><p class="subtle">نقطه مهم بعدی: آکتائو · ۲ تا ۳ روز</p>${status("بازه تخمینی", "shared")}</section>
      </div>
      <div class="grid three">
        <section class="card"><div class="card-head"><div><h3>کالای شما</h3><p>۲ قلم · ۱۲۴ واحد بسته‌بندی</p></div></div><b>قطعات موتور و بوش فلزی</b><p class="subtle">۱۰۰ کارتن + ۲۴ پالت</p>${button("مشاهده جزئیات", 'data-customer-section="cargo"', "small")}</section>
        <section class="card"><div class="card-head"><div><h3>تحویل شما</h3><p>دو تحویل ثبت‌شده</p></div>${status("تکمیل", "complete")}</div><b>۶۰ کارتن تهران · ۴۰ کارتن قزوین</b><p class="subtle">رسید دوم در حال تکمیل پرونده است.</p></section>
        <section class="card"><div class="card-head"><div><h3>وضعیت عملیاتی</h3><p>اثر امن مشکل جاری</p></div>${status("در پیگیری", "attention")}</div><p>یک مشکل عملیاتی در اسناد حمل ثبت شده و در حال پیگیری است. ETA فعلی بدون تغییر است.</p></section>
      </div>`;
  }

  function customerTimeline() {
    return `<div class="page-heading"><div><p class="eyebrow">مسیر و Timeline امن</p><h1>سفر حمل شما</h1><p>روایت ساده و customer-safe؛ جزئیات داخلی و اطلاعات مشتریان دیگر حذف شده‌اند.</p></div></div>
      <section class="card"><div class="route-strip">${routeNode("۱","شانگهای","خورگوس","جاده‌ای","تکمیل","complete")}${routeNode("۲","خورگوس","آکتائو","ریلی","در حال اجرا","current")}${routeNode("۳","آکتائو","انزلی","دریایی","آینده","")}${routeNode("۴","انزلی","مقصدهای شما","جاده‌ای","آینده","")}</div></section>
      <section class="card" style="margin-top:14px"><ol class="timeline">${timelineItem("امروز · ۱۴:۳۰","موقعیت گزارش‌شده به‌روز شد","در مسیر آلماتی · منبع: گزارش شرکت حمل","corrected",'<div class="correction-note">گزارش ساعت ۱۰:۰۰ بعداً اصلاح شد؛ آخرین گزارش معتبر همین مورد است.</div>')}${timelineItem("امروز · ۱۲:۱۰","پیگیری عملیاتی ادامه دارد","اثر زمانی جدیدی بر ETA ثبت نشده است.","")}${timelineItem("۲۰ شهریور","تغییر اصلی روش حمل","کالای شما از حمل جاده‌ای به حمل ریلی منتقل شد.","complete")}${timelineItem("۱۸ شهریور","حرکت از مبدا","بارگیری و خروج از شانگهای ثبت شد.","complete")}</ol></section>`;
  }

  function customerCargo() {
    return `<div class="page-heading"><div><p class="eyebrow">فقط کالای شما</p><h1>کالاها</h1><p>داده سایر مشتریان در این projection وجود ندارد.</p></div></div><div class="grid two"><section class="card"><div class="card-head"><div><h2>قطعات موتور A1</h2><p>درخواست RQ-8421</p></div>${status("تحویل‌شده", "complete")}</div><dl class="detail-list"><div class="detail-row"><dt>مقدار</dt><dd>۱۰۰ کارتن</dd></div><div class="detail-row"><dt>HS Code</dt><dd>8409.91</dd></div><div class="detail-row"><dt>مقصدها</dt><dd>تهران / قزوین</dd></div></dl></section><section class="card"><div class="card-head"><div><h2>بوش فلزی A2</h2><p>درخواست RQ-8421</p></div>${status("در مسیر", "current")}</div><dl class="detail-list"><div class="detail-row"><dt>مقدار</dt><dd>۲۴ پالت</dd></div><div class="detail-row"><dt>HS Code</dt><dd>8483.30</dd></div><div class="detail-row"><dt>مقصد</dt><dd>تهران</dd></div></dl></section></div><section class="card tint-blue" style="margin-top:14px"><b>حریم خصوصی فعال است</b><p class="no-margin">این Shipment سه مشتری دارد، اما شما فقط ۲ Cargo متعلق به خودتان را می‌بینید.</p></section>`;
  }

  function customerDocuments() {
    return `<div class="page-heading"><div><p class="eyebrow">اسناد مجاز شما</p><h1>اسناد</h1><p>سند مشترک فقط وقتی نمایش داده می‌شود که صریحاً visibility مشتری داشته باشد.</p></div></div><section class="card"><div class="document-list">${documentRow("Commercial Invoice A","Cargo A1 · متعلق به شما","مخصوص مشتری مربوط","customer",1)}${documentRow("Packing List A","Cargo A1 · متعلق به شما","مخصوص مشتری مربوط","customer",2)}${documentRow("CMR حمل مشترک","مرحله خورگوس–آکتائو","مشترک و قابل نمایش","shared",3)}${documentRow("رسید تحویل تهران","Delivery DL-301","مخصوص مشتری مربوط","customer",4)}</div></section><div class="shared-note" style="margin-top:14px"><span>ⓘ</span><span>اسناد داخلی شرکت حمل، اسناد مشتریان دیگر و علت خصوصی مشکلات در این صفحه نمایش داده نمی‌شوند.</span></div>`;
  }

  function customerDelivery() {
    return `<div class="page-heading"><div><p class="eyebrow">تحویل‌های کالای شما</p><h1>تحویل</h1><p>هر تحویل مقدار، مقصد و مدرک مستقل دارد.</p></div>${status("۱۰۰ از ۱۰۰ کارتن", "complete")}</div><section class="card"><div class="grid two"><div class="card flat tint-green"><p class="eyebrow">تحویل ۱ · DL-301</p><h2>۶۰ کارتن · تهران</h2><p>۲۲ شهریور · ۱۰:۲۰</p>${status("رسید قابل مشاهده", "complete")}</div><div class="card flat tint-amber"><p class="eyebrow">تحویل ۲ · DL-305</p><h2>۴۰ کارتن · قزوین</h2><p>۲۳ شهریور · ۱۷:۱۰</p>${status("رسید در حال تکمیل", "incomplete")}</div></div></section><p class="subtle tiny">تکمیل تحویل کالای شما به‌تنهایی پرونده حمل مشترک را نمی‌بندد.</p>`;
  }

  function renderCustomer() {
    const screens = { summary: customerSummary, timeline: customerTimeline, cargo: customerCargo, documents: customerDocuments, delivery: customerDelivery };
    return `<main id="main-content" class="customer-shell">${state.scenario === "stale" ? staleBanner() : ""}${customerNav()}${screens[state.customerSection]()}</main>`;
  }

  function adminCatalog() {
    return `<div class="page-heading"><div><p class="eyebrow">DEFINE · تعاریف پایه سازمان</p><h1>تعاریف مرجع سازمان</h1><p>مدیر سازمان از catalog مرکزی انتخاب می‌کند یا تعریف سازمانی می‌سازد؛ کارشناس free-text bypass ندارد.</p></div><div class="heading-actions">${button("درخواست تعریف سازمانی", 'data-dialog="catalog-request"', "primary")}</div></div>
      <section class="card"><div class="card-head"><div><h2>نوع وسیله و واحد حمل</h2><p>فعال‌سازی برای استفاده کارشناسان همین سازمان</p></div>${status("۴ تعریف", "internal")}</div>
        ${catalogRow("truck","کامیون کشنده","مرجع مرکزی · TRUCK_TRACTOR","فعال")}
        ${catalogRow("rail","قطار باری","مرجع مرکزی · FREIGHT_TRAIN","فعال")}
        ${catalogRow("reeferWagon","واگن یخچالی","تعریف مرکزی · REEFER_WAGON","غیرفعال")}
        ${catalogRow("container40","کانتینر ۴۰ فوت","مرجع مرکزی · ISO_40_GP","فعال")}
      </section>
      <section class="card tint-amber" style="margin-top:14px"><div class="action-line"><div><p class="eyebrow">نیاز کارشناس در Shipment S-100</p><h2>واگن یخچالی در تعاریف سازمان فعال نیست</h2><p>فقط اقدام وابسته متوقف می‌شود؛ مدیر می‌تواند پس از بررسی تعریف را فعال کند.</p></div>${button("فعال‌سازی و ثبت history", 'data-toggle-catalog="reeferWagon"', "primary")}</div></section>`;
  }

  function catalogRow(key, title, source, fallback) {
    const active = state.catalogActive[key];
    return `<div class="catalog-row"><div><b>${title}</b><p class="tiny subtle no-margin">${source}</p></div><span>${active ? status("قابل استفاده برای Expert", "complete") : status("غیرفعال", "incomplete")}</span><button type="button" class="toggle" role="switch" aria-label="${active ? "غیرفعال‌کردن" : "فعال‌کردن"} ${title}" aria-checked="${active}" data-toggle-catalog="${key}"></button></div>`;
  }

  function adminRouteTimes() {
    return `<div class="page-heading"><div><p class="eyebrow">REFERENCE · نسخه‌دار و سازمانی</p><h1>زمان مرجع مسیر</h1><p>زمان حرکت از توقف/عملیات جداست. عملکرد واقعی فقط پیشنهاد بازبینی می‌دهد و مرجع را خودکار تغییر نمی‌دهد.</p></div><div class="heading-actions">${button("افزودن نسخه جدید", 'data-dialog="route-reference"', "primary")}</div></div>
      <section class="card"><div class="card-head"><div><h2>خورگوس ← آکتائو</h2><p>سازمان آفتاب ترابر · نسخه‌های موثر</p></div>${status("نسخه ۴ فعال", "complete")}</div><div class="table-wrap"><table><thead><tr><th>Mode</th><th>زمان حرکت</th><th>توقف/عملیات</th><th>بازه اثر</th><th>وضعیت</th></tr></thead><tbody><tr><td>جاده‌ای</td><td>۶ تا ۸ روز</td><td>۰ تا ۱ روز</td><td>از ۱ شهریور</td><td>${status("فعال", "complete")}</td></tr><tr><td>ریلی</td><td>۴ تا ۶ روز</td><td>۱ تا ۲ روز</td><td>از ۱ شهریور</td><td>${status("فعال", "complete")}</td></tr><tr><td>ریلی</td><td>۳ تا ۵ روز</td><td>۰ تا ۱ روز</td><td>تا ۳۱ مرداد</td><td>${status("تاریخی", "internal")}</td></tr></tbody></table></div></section>
      <div class="grid two" style="margin-top:14px"><section class="card"><div class="card-head"><div><h2>مرجع فعلی</h2><p>ریل · حرکت</p></div></div><h1>۴ تا ۶ روز</h1>${status("مصوب مدیر سازمان", "complete")}</section><section class="card tint-amber"><div class="card-head"><div><h2>عملکرد واقعی اخیر</h2><p>نمای هدف تحلیلی؛ بدون اجرای analytics</p></div>${status("پیشنهاد بازبینی", "attention")}</div><h1>۷ تا ۹ روز</h1><p>سیستم مرجع رسمی را خودکار تغییر نمی‌دهد.</p></section></div>`;
  }

  function adminClosureRules() {
    return `<div class="page-heading"><div><p class="eyebrow">CONTROL · الزام‌های سازمان</p><h1>الزامات بستن پرونده</h1><p>الزام‌های عمومی با modeهای استفاده‌شده ترکیب می‌شوند. هیچ موردی از نمونه به universal mandatory تبدیل نشده است.</p></div><div class="heading-actions">${button("افزودن الزام", 'data-dialog="closure-rule"', "primary")}</div></div><div class="grid two"><section class="card"><div class="card-head"><div><h2>الزام‌های عمومی</h2><p>نسخه ۶ · موثر از ۱ شهریور</p></div>${status("منتشرشده", "complete")}</div><div class="checklist">${checkRow(true,"تعیین تکلیف همه Cargoها","mandatory")}${checkRow(true,"ثبت مقدار واقعی","mandatory")}${checkRow(true,"بستن مشکلات ضروری","mandatory")}${checkRow(true,"ثبت Deliveryهای لازم","mandatory")}</div></section><section class="card"><div class="card-head"><div><h2>الزام‌های وابسته به Mode</h2><p>برای حمل ترکیبی با هم اعمال می‌شوند</p></div></div><div class="checklist">${checkRow(true,"رسید تحویل مقصد","جاده")}${checkRow(true,"نسخه معتبر سند واگن","ریل")}${checkRow(true,"گزارش تخلیه بندر","دریا")}</div></section></div>`;
  }

  function adminClosureExceptions() {
    return `<div class="page-heading"><div><p class="eyebrow">EXCEPTION · اختیار ویژه مدیر</p><h1>بررسی استثنای بستن</h1><p>مسیر استثنا آشکار، دلیل‌دار و audit‌شده است؛ کارشناس اجازه bypass ندارد.</p></div></div><section class="card tint-red"><div class="card-head"><div><p class="eyebrow" style="color:var(--red)">درخواست CE-19 · Shipment S-100</p><h2>بستن پرونده با یک مدرک مفقود</h2><p>درخواست‌کننده: نرگس احمدی · امروز ۱۵:۱۰</p></div>${status("در انتظار تصمیم", "blocked")}</div><div class="grid two"><div class="card flat"><h3>الزام تکمیل‌نشده</h3><p>فایل رسید Delivery DL-305 موجود نیست.</p><b>واقعیت موجود:</b><p>تحویل ۴۰ کارتن در قزوین ثبت شده؛ شماره رسید و تأیید گیرنده موجود است، اما فایل اسکن هنوز نرسیده.</p></div><div class="card flat"><h3>اثر تصمیم</h3><p>در صورت تأیید، پرونده با وضعیت صریح «بستن با استثنا» بسته می‌شود و Requirement حذف یا پاس‌شده نمایش داده نمی‌شود.</p>${status("نیازمند دلیل مدیر", "attention")}</div></div><div class="dialog-actions">${button("رد درخواست", 'data-dialog="reject-exception"', "danger")}${button("بررسی و تصویب استثنا", 'data-dialog="closure-exception"', "primary")}</div></section><section class="card" style="margin-top:14px"><div class="card-head"><div><h2>سابقه تصمیم‌ها</h2><p>الزام، دلیل، تصویب‌کننده و زمان حفظ می‌شوند</p></div></div><div class="table-wrap"><table><thead><tr><th>پرونده</th><th>الزام</th><th>تصمیم</th><th>تصویب‌کننده</th><th>زمان</th></tr></thead><tbody><tr><td>S-091</td><td>اصل رسید بندر</td><td>${status("تأیید با استثنا", "attention")}</td><td>سارا یوسفی</td><td>۱۲ شهریور</td></tr><tr><td>S-087</td><td>پیگیری باز</td><td>${status("رد", "blocked")}</td><td>سارا یوسفی</td><td>۸ شهریور</td></tr></tbody></table></div></section>`;
  }

  function renderAdmin() {
    const screens = { catalog: adminCatalog, "route-times": adminRouteTimes, "closure-rules": adminClosureRules, "closure-exceptions": adminClosureExceptions };
    return `<main id="main-content"><div class="admin-layout"><aside><nav class="admin-nav" aria-label="تنظیمات سازمان">${adminSections.map(([key,label])=>`<button type="button" data-admin-section="${key}" class="${state.adminSection===key?"is-active":""}" ${state.adminSection===key?'aria-current="page"':""}>${label}</button>`).join("")}</nav></aside><div>${state.scenario === "stale" ? staleBanner() : ""}${screens[state.adminSection]()}</div></div></main>`;
  }

  function statePage(kind) {
    const states = {
      loading: ["…", "در حال آماده‌سازی اطلاعات", "آخرین داده معتبر پرونده در حال دریافت است.", `<div class="skeleton"></div><div class="skeleton" style="width:76%"></div><div class="skeleton" style="width:55%"></div>`],
      empty: ["○", "هنوز داده‌ای در این بخش نیست", "این حالت به معنی سلامت یا تکمیل پرونده نیست. از اقدام‌های مرتبط برای شروع استفاده کنید.", button("بازگشت به حالت عادی", 'data-action="reset-scenario"', "primary")],
      denied: ["⊘", "دسترسی به این بخش مجاز نیست", "دامنه نقش یا سازمان جاری اجازه مشاهده این اطلاعات را نمی‌دهد. شناسه مستقیم اختیار تازه ایجاد نمی‌کند.", button("بازگشت امن", 'data-action="reset-scenario"')],
      error: ["!", "دریافت اطلاعات ممکن نشد", "موفقیت ساختگی نمایش داده نمی‌شود. دوباره تلاش کنید یا بعداً بازگردید.", `${button("تلاش دوباره", 'data-action="reset-scenario"', "primary")}`],
    };
    const [symbol, title, text, extra] = states[kind];
    return `<main id="main-content" class="state-page"><section class="state-box" role="${kind === "error" ? "alert" : "status"}"><span class="state-symbol">${symbol}</span><h1>${title}</h1><p>${text}</p>${extra}</section></main>`;
  }

  function render() {
    document.querySelectorAll("[data-role]").forEach((el) => {
      if (!el.classList.contains("role-button")) return;
      const active = el.dataset.role === state.role;
      el.classList.toggle("is-active", active);
      el.setAttribute("aria-pressed", String(active));
    });
    if (["loading", "empty", "denied", "error"].includes(state.scenario)) {
      app.innerHTML = statePage(state.scenario);
      return;
    }
    app.innerHTML = state.role === "expert" ? renderExpert() : state.role === "customer" ? renderCustomer() : renderAdmin();
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function openDialog(type) {
    const node = dialogTemplate.content.cloneNode(true);
    dialogLayer.replaceChildren(node);
    dialogLayer.hidden = false;
    document.body.style.overflow = "hidden";
    const eyebrow = dialogLayer.querySelector("#dialog-eyebrow");
    const title = dialogLayer.querySelector("#dialog-title");
    const body = dialogLayer.querySelector(".dialog-body");
    const dialogs = dialogDefinitions();
    const selected = dialogs[type] || dialogs.info;
    eyebrow.textContent = selected.eyebrow;
    title.textContent = selected.title;
    body.innerHTML = selected.body;
    requestAnimationFrame(() => dialogLayer.querySelector("button, input, select")?.focus());
  }

  function closeDialog() {
    dialogLayer.hidden = true;
    dialogLayer.replaceChildren();
    document.body.style.overflow = "";
  }

  function dialogDefinitions() {
    return {
      scenarios: { eyebrow: "نمایش وضعیت‌های UX", title: "حالت رابط را انتخاب کنید", body: `<div class="scenario-grid">${scenarioOption("normal","عادی","داده واقعی نمونه و مسیر کامل")}${scenarioOption("loading","در حال بارگذاری","بدون نمایش داده قدیمی به‌عنوان تازه")}${scenarioOption("empty","خالی","نبود داده، نه موفقیت یا سلامت")}${scenarioOption("error","خطا","پیام قابل اقدام و تلاش مجدد")}${scenarioOption("denied","عدم دسترسی","بدون نشت داده یا تایید وجود")}${scenarioOption("stale","قدیمی / degraded","هشدار مشترک و عدم برداشت سلامت")}</div>` },
      allocation: { eyebrow: "ASSIGN · تخصیص Cargo B1", title: "تکمیل تخصیص فیلتر صنعتی", body: `<form data-form="allocation"><div class="form-grid"><div class="field full"><label for="allocation-unit">واحد حمل</label><select id="allocation-unit" name="unit"><option>TR-24 · تریلر T-24</option><option>W-07 · واگن W-07</option></select></div><div class="field"><label for="allocation-quantity">مقدار (کارتن)</label><input id="allocation-quantity" name="quantity" type="number" value="10" min="1" max="10" data-allocation-quantity><p class="field-help">باقی‌مانده قابل تخصیص: ۱۰ کارتن</p><p class="field-error" data-allocation-error hidden>بیش از ۱۰ کارتن قابل تخصیص نیست؛ over-allocation مسدود است.</p></div><div class="field"><label for="allocation-stage">مرحله مسیر</label><select id="allocation-stage" name="stage"><option>خورگوس ← آکتائو</option></select></div></div><div class="dialog-actions">${button("انصراف", 'data-action="close-dialog"')}${button("ثبت تخصیص", 'type="submit"', "primary")}</div></form>` },
      transfer: { eyebrow: "CHANGE · انتقال کالا", title: "ثبت انتقال عملیاتی کالا", body: `<form data-form="transfer"><div class="form-grid"><div class="field full"><label>کالا</label><select name="cargo"><option>A1 · قطعات موتور · پارس موتور آریا</option></select></div><div class="field"><label>از</label><select><option>TR-12 · تریلر T-12</option></select></div><div class="field"><label>به</label><select><option>TR-18 · تریلر T-18</option></select></div><div class="field"><label>مقدار</label><input type="number" value="40" min="1" max="60"></div><div class="field"><label>زمان وقوع</label><input type="datetime-local" value="2026-09-23T16:40"></div><div class="field full"><label>نقطه عملیاتی</label><select><option>پایانه خورگوس</option></select></div><div class="field full"><label>دلیل (اختیاری)</label><textarea>تعادل ظرفیت دو تریلر</textarea></div></div><p class="field-help">تخصیص قبلی حذف نمی‌شود؛ نتیجه جاری و history هر دو به‌روز می‌شوند.</p><div class="dialog-actions">${button("ثبت انتقال", 'type="submit"', "primary")}</div></form>` },
      location: { eyebrow: "CHANGE · گزارش عملیاتی", title: "ثبت موقعیت گزارش‌شده", body: `<form data-form="location"><div class="form-grid"><div class="field full"><label>موقعیت گزارش‌شده</label><input value="نزدیک آکتائو" required></div><div class="field"><label>زمان وقوع</label><input type="datetime-local" value="2026-09-24T16:10" required></div><div class="field"><label>منبع</label><select><option>گزارش شرکت حمل</option><option>تماس راننده</option><option>ایمیل عملیات</option></select></div><div class="field full"><label>یادداشت داخلی (اختیاری)</label><textarea></textarea></div></div><div class="card tint-blue flat"><b>شفافیت:</b> این ثبت به‌عنوان «گزارش عملیاتی» نمایش داده می‌شود و GPS یا LIVE نامیده نمی‌شود.</div><div class="dialog-actions">${button("ثبت گزارش", 'type="submit"', "primary")}</div></form>` },
      delivery: { eyebrow: "CHANGE · Delivery", title: "ثبت تحویل جدید", body: `<form data-form="delivery"><div class="form-grid"><div class="field full"><label>کالا</label><select><option>B1 · فیلتر صنعتی · آرمان تجهیز شرق</option></select></div><div class="field"><label>مقدار</label><input type="number" value="30"></div><div class="field"><label>مکان</label><input value="قزوین"></div><div class="field"><label>زمان تحویل</label><input type="datetime-local" value="2026-09-24T15:30"></div><div class="field"><label>Evidence</label><select><option>در انتظار فایل</option><option>رسید دریافت‌شده</option></select></div></div><p class="field-help">ثبت Delivery مقدار باقی‌مانده همین Cargo را تغییر می‌دهد؛ Shipment فقط با کنترل closure بسته می‌شود.</p><div class="dialog-actions">${button("ثبت تحویل", 'type="submit"', "primary")}</div></form>` },
      exception: { eyebrow: "CHANGE · مشکل عملیاتی", title: "ثبت مشکل", body: `<form data-form="generic"><div class="form-grid"><div class="field full"><label>عنوان مشکل</label><input value="تأخیر در سند حمل"></div><div class="field"><label>اثر</label><select><option>اثر زمانی</option><option>اثر بر کالا</option><option>اثر بر اسناد</option></select></div><div class="field"><label>شدت</label><select><option>مهم</option><option>بحرانی</option></select></div><div class="field full"><label>توضیح داخلی</label><textarea></textarea></div><div class="field full"><label>توضیح امن برای مشتری</label><textarea></textarea><p class="field-help">اگر خالی بماند و Customer متأثر باشد، پیام امن پیش‌فرض نمایش داده می‌شود.</p></div></div><div class="dialog-actions">${button("ثبت مشکل", 'type="submit"', "primary")}</div></form>` },
      closureException: { eyebrow: "اختیار ویژه مدیر سازمان", title: "تصویب بستن با استثنا", body: `<form data-form="closure-exception"><div class="card tint-red flat"><b>الزام مفقود:</b><p>فایل رسید Delivery DL-305 موجود نیست. این Requirement PASS نمی‌شود و به‌عنوان استثنا باقی می‌ماند.</p></div><div class="field"><label>دلیل تصمیم مدیر (الزامی)</label><textarea required>تأیید گیرنده و شماره رسید موجود است؛ فایل اصل پس از بستن نیز باید پیگیری شود.</textarea></div><div class="field"><label>تصویب‌کننده</label><input value="سارا یوسفی · مدیر سازمان" readonly></div><div class="dialog-actions">${button("انصراف", 'data-action="close-dialog"')}${button("تصویب استثنا", 'type="submit"', "danger")}</div></form>` },
      routeReference: { eyebrow: "نسخه جدید مرجع", title: "ویرایش زمان مرجع خورگوس ← آکتائو", body: `<form data-form="generic"><div class="form-grid"><div class="field"><label>Mode</label><select><option>ریلی</option></select></div><div class="field"><label>تاریخ اثر</label><input type="date" value="2026-10-01"></div><div class="field"><label>حرکت از (روز)</label><input type="number" value="6"></div><div class="field"><label>حرکت تا (روز)</label><input type="number" value="8"></div><div class="field"><label>توقف از (روز)</label><input type="number" value="1"></div><div class="field"><label>توقف تا (روز)</label><input type="number" value="2"></div><div class="field full"><label>دلیل نسخه جدید</label><textarea required>بازبینی بر اساس عملکرد اخیر؛ نیازمند تصویب مدیر</textarea></div></div><p class="field-help">نسخه جاری و Shipmentهای تاریخی بازنویسی نمی‌شوند.</p><div class="dialog-actions">${button("انتشار نسخه", 'type="submit"', "primary")}</div></form>` },
      documentPreview: { eyebrow: "پیش‌نمایش سند ساختگی", title: "CMR حمل مشترک", body: `<div class="card flat" style="min-height:260px;display:grid;place-items:center;background:var(--surface-soft)"><div style="text-align:center"><div style="font-size:44px">▧</div><b>سند نمایشی</b><p class="subtle">هیچ فایل واقعی یا داده مشتری استفاده نشده است.</p></div></div>` },
      info: { eyebrow: "نمونه تعاملی", title: "این اقدام در محدوده Prototype است", body: `<p>این کنترل برای نمایش جریان و ساختار تجربه طراحی شده است و هیچ داده‌ای را در محصول یا پایگاه داده تغییر نمی‌دهد.</p><div class="dialog-actions">${button("متوجه شدم", 'data-action="close-dialog"', "primary")}</div>` },
    };
  }

  function scenarioOption(key, title, text) {
    return `<button type="button" class="scenario-option" data-scenario="${key}"><strong>${title}</strong><span>${text}</span></button>`;
  }

  function showToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    toastRegion.append(toast);
    setTimeout(() => toast.remove(), 3200);
  }

  document.addEventListener("click", (event) => {
    const target = event.target.closest("button, [data-action]");
    if (!target) return;
    if (target.dataset.role) {
      state.role = target.dataset.role;
      if (target.dataset.adminSection) state.adminSection = target.dataset.adminSection;
      state.scenario = "normal";
      render();
      return;
    }
    if (target.dataset.expertSection) { state.role = "expert"; state.expertSection = target.dataset.expertSection; render(); return; }
    if (target.dataset.customerSection) { state.customerSection = target.dataset.customerSection; render(); return; }
    if (target.dataset.adminSection) { state.adminSection = target.dataset.adminSection; render(); return; }
    if (target.dataset.routeView) { state.routeView = target.dataset.routeView; render(); return; }
    if (target.dataset.docContext) { state.documentContext = target.dataset.docContext; render(); return; }
    if (target.dataset.dialog) { openDialog(target.dataset.dialog); return; }
    if (target.dataset.scenario) { state.scenario = target.dataset.scenario; closeDialog(); render(); return; }
    if (target.dataset.toggleCatalog) {
      const key = target.dataset.toggleCatalog;
      state.catalogActive[key] = !state.catalogActive[key];
      showToast(state.catalogActive[key] ? "تعریف برای سازمان فعال شد و رویداد history ثبت شد." : "تعریف برای استفاده جدید غیرفعال شد؛ سابقه حفظ می‌شود.");
      render();
      return;
    }
    if (target.dataset.action === "open-scenarios") { openDialog("scenarios"); return; }
    if (target.dataset.action === "close-dialog") { closeDialog(); return; }
    if (target.dataset.action === "reset-scenario") { state.scenario = "normal"; render(); }
  });

  document.addEventListener("input", (event) => {
    if (!event.target.matches("[data-allocation-quantity]")) return;
    const error = event.target.closest("form").querySelector("[data-allocation-error]");
    error.hidden = Number(event.target.value) <= 10;
  });

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("form[data-form]");
    if (!form) return;
    event.preventDefault();
    if (form.dataset.form === "allocation") {
      const quantity = Number(new FormData(form).get("quantity"));
      const error = form.querySelector("[data-allocation-error]");
      if (quantity > 10) { error.hidden = false; form.querySelector("[name=quantity]").focus(); return; }
      showToast(`${quantity} کارتن تخصیص یافت. این تغییر فقط در state محلی Prototype است.`);
    } else if (form.dataset.form === "closure-exception") {
      showToast("تصمیم استثنا به‌صورت نمایشی ثبت شد؛ الزام همچنان با برچسب استثنا باقی می‌ماند.");
    } else {
      showToast("اقدام در state محلی Prototype ثبت شد و به هیچ سامانه‌ای ارسال نشد.");
    }
    closeDialog();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !dialogLayer.hidden) closeDialog();
  });

  render();
})();
