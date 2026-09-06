import type { DashboardDefinition } from "./types";
export const operationsControlTower: DashboardDefinition = {
  dashboard_id: "system.operations-control-tower.v1", name: "برج کنترل عملیات", description: "نمای عملیاتی مبتنی بر داده‌های معنایی تاییدشده.", dashboard_type: "SYSTEM", semantic_version: "analytics-semantic-v1", refresh_policy: { mode: "PERIODIC", interval_ms: 120000 },
  global_filters: [
    { dimension_key: "TIME", label: "بازه زمانی", applicable_widget_ids: ["active", "lifecycle", "route-status", "route-mode", "exceptions", "work-items", "delay-cases", "documents"] },
    { dimension_key: "CUSTOMER", label: "مشتری", applicable_widget_ids: ["active", "lifecycle", "route-status", "route-mode", "exceptions", "work-items", "delay-cases"] },
    { dimension_key: "PROJECT", label: "پروژه", applicable_widget_ids: ["active", "lifecycle", "route-status", "route-mode", "exceptions", "work-items", "delay-cases"] },
  ],
  sections: [{ section_id: "overview", title: "نمای عملیاتی", order: 1, widget_ids: ["active", "exceptions", "work-items", "documents", "lifecycle", "route-status", "route-mode", "delay-cases"] }],
  widgets: [
    { widget_id:"active", widget_type:"KPI_CARD", title:"محموله‌های فعال", query:{metric_keys:["ACTIVE_SHIPMENT_COUNT"],dimension_keys:[]}, coverage_policy:"SHOW_ALWAYS",warnings_policy:"SHOW_WHEN_PRESENT",drilldown:{enabled:true},layout:{col_span:1,order:1},required_permissions:["operational_shipment.read"] },
    { widget_id:"exceptions", widget_type:"KPI_CARD", title:"موارد استثنای باز", query:{metric_keys:["OPEN_EXCEPTION_COUNT"],dimension_keys:[]}, coverage_policy:"SHOW_ALWAYS",warnings_policy:"SHOW_WHEN_PRESENT",drilldown:{enabled:true},layout:{col_span:1,order:2},required_permissions:["operational_shipment.read"] },
    { widget_id:"work-items", widget_type:"KPI_CARD", title:"کارهای باز", query:{metric_keys:["OPEN_WORK_ITEM_COUNT"],dimension_keys:[]}, coverage_policy:"SHOW_ALWAYS",warnings_policy:"SHOW_WHEN_PRESENT",drilldown:{enabled:false},layout:{col_span:1,order:3},required_permissions:["operational_shipment.read"] },
    { widget_id:"documents", widget_type:"KPI_CARD", title:"پوشش آمادگی اسناد", query:{metric_keys:["DOCUMENT_READINESS_COVERAGE"],dimension_keys:[]}, coverage_policy:"SHOW_ALWAYS",warnings_policy:"SHOW_ALWAYS",drilldown:{enabled:true},layout:{col_span:1,order:4},required_permissions:["operational_shipment.read"] },
    { widget_id:"lifecycle", widget_type:"STATUS_DISTRIBUTION", title:"چرخه عمر محموله", query:{metric_keys:["SHIPMENT_COUNT"],dimension_keys:["SHIPMENT_STATUS"],limit:20}, coverage_policy:"SHOW_WHEN_PARTIAL",warnings_policy:"SHOW_WHEN_PRESENT",drilldown:{enabled:true,allow_segment:true},layout:{col_span:2,order:5},required_permissions:["operational_shipment.read"] },
    { widget_id:"route-status", widget_type:"STACKED_BAR", title:"وضعیت بخش‌های مسیر", query:{metric_keys:["ROUTE_LEG_COUNT"],dimension_keys:["LEG_STATUS"],limit:20}, coverage_policy:"SHOW_ALWAYS",warnings_policy:"SHOW_WHEN_PRESENT",drilldown:{enabled:true,allow_segment:true},layout:{col_span:2,order:6},required_permissions:["operational_shipment.read"] },
    { widget_id:"route-mode", widget_type:"BAR", title:"فعالیت مسیر بر اساس روش حمل", query:{metric_keys:["ROUTE_LEG_COUNT"],dimension_keys:["TRANSPORT_MODE"],limit:20}, coverage_policy:"SHOW_ALWAYS",warnings_policy:"SHOW_WHEN_PRESENT",drilldown:{enabled:true,allow_segment:true},layout:{col_span:2,order:7},required_permissions:["operational_shipment.read"] },
    { widget_id:"delay-cases", widget_type:"TREND", title:"موارد تأخیر گزارش‌شده", description:"تعداد موارد گزارش‌شده است، نه تعداد محموله‌های هم‌اکنون با تأخیر.", query:{metric_keys:["DELAY_CASE_COUNT"],dimension_keys:["TIME"],time_dimension:"created",time_grain:"day",limit:90}, coverage_policy:"SHOW_WHEN_PARTIAL",warnings_policy:"SHOW_WHEN_PRESENT",drilldown:{enabled:false},layout:{col_span:2,order:8},required_permissions:["operational_shipment.read"] },
  ]
};
