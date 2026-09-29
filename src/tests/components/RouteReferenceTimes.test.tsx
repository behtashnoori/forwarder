import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import RouteReferenceTimes from "@/components/RouteReferenceTimes";
import OrganizationRouteTimesTab from "@/components/OrganizationRouteTimesTab";
import { timeRange, type LegTime, type TimeVersion } from "@/lib/routeTimeApi";
const api=vi.hoisted(()=>({
  get:vi.fn(),select:vi.fn(),list:vi.fn(),revise:vi.fn(),create:vi.fn(),
  countries:vi.fn(),provinces:vi.fn(),iran:vi.fn(),international:vi.fn(),points:vi.fn(),
}));
vi.mock("@/i18n",()=>({useI18n:()=>({transportLabel:(value:string)=>value,businessLabel:(value:string)=>value})}));
vi.mock("@/lib/routeTimeApi",async()=>({...await vi.importActual<typeof import("@/lib/routeTimeApi")>("@/lib/routeTimeApi"),getPlanTimes:api.get,selectPlanTime:api.select,listRouteTimes:api.list,reviseRouteTime:api.revise,createRouteTime:api.create}));
vi.mock("@/lib/api",async()=>({...await vi.importActual<typeof import("@/lib/api")>("@/lib/api"),fetchAdminCountries:api.countries,fetchAdminProvinces:api.provinces,searchIranDestinations:api.iran,fetchInternationalCityPage:api.international,listLogisticsPoints:api.points}));
const version:TimeVersion={public_id:"version-1",version:1,movement_min_minutes:1200,movement_max_minutes:1440,stop_min_minutes:240,stop_max_minutes:480,planned_distance_km:"1250.000",effective_from:"2026-09-01T00:00:00Z",effective_until:null,recorded_at:"2026-09-01T00:00:00Z",actor_user_id:2,recorded_by:"مدیر سازمان"};
const leg:LegTime={leg_id:3,leg_version:1,sequence_number:1,origin_label:"خورگوس",destination_label:"آکتائو",transport_mode:"rail",reference_at:"2027-10-01T00:00:00Z",time_basis:"PLANNED_DEPARTURE",applicable:version,selected:null,selection_matches_leg:false,history:[],can_select:true};
const plans=[{id:1,revision_number:1,status:"draft"}];
const response=(item:LegTime)=>({data:{plan_id:1,plan_revision:1,plan_status:"draft",items:[item]}});
describe("explicit route reference basis",()=>{
  beforeEach(()=>{
    vi.clearAllMocks();
    api.get.mockResolvedValue(response(leg));
    api.select.mockResolvedValue({data:{public_id:"selection",created:true}});
    api.list.mockResolvedValue({data:{items:[],page:1,total:0,has_next:false}});
    api.create.mockResolvedValue({data:{public_id:"version-new",created:true}});
    api.countries.mockResolvedValue({items:[
      {id:1,name_fa:"ایران",name_en:"Iran",code:"IR",is_active:true},
      {id:2,name_fa:"آندورا",name_en:"Andorra",code:"AD",is_active:true},
      {id:3,name_fa:"قدیمی",name_en:"Inactive",code:"ZZ",is_active:false},
    ]});
    api.provinces.mockResolvedValue({items:[
      {id:10,name_fa:"اصفهان",code:"ISF",country_id:null,is_active:true},
      {id:11,name_fa:"هرمزگان",code:"HRZ",country_id:null,is_active:true},
    ]});
    api.iran.mockImplementation(async(query:string,_limit:number,type:string)=>({data:type==="international_city"&&(!query||query.includes("بندرعباس"))?[{identity:{type:"international_city",id:59},label:"بندر — بندرعباس · ایران",display_name:"بندرعباس",type_label:"بندر",province:null,secondary_label:"بندر · ایران"}]:[],meta:{count:type==="international_city"?1:0,limit:50}}));
    api.international.mockResolvedValue({items:[],offset:0,limit:50,has_more:false});
    api.points.mockResolvedValue({items:[],page:1,pages:0,total:0});
  });
  it("shows undefined without invented zero and keeps movement separate from stop",async()=>{
    api.get.mockResolvedValue(response({...leg,applicable:null}));render(<RouteReferenceTimes shipmentId="shipment" plans={plans}/>);
    expect(await screen.findByText("مرجع قابل استفاده")).toBeInTheDocument();
    expect(screen.getAllByText("تعریف نشده")).toHaveLength(6);
    expect(screen.getByRole("button",{name:"ثبت این نسخه برای برنامه"})).toBeDisabled();
    expect(timeRange(1200,1440)).toBe("۲۰ ساعت تا ۲۴ ساعت");
    expect(timeRange(0,0)).toBe("۰ ساعت");
    expect(timeRange(null,null)).toBe("تعریف نشده");
  });
  it("keeps version one visible after admin supplies version two, until explicit selection",async()=>{
    const selected={public_id:"selection-1",selection_revision:1,reference_at:leg.reference_at,recorded_at:version.recorded_at,actor_user_id:1,reference:version};
    api.get.mockResolvedValue(response({...leg,selected,selection_matches_leg:true,history:[selected],applicable:{...version,public_id:"version-2",version:2,movement_min_minutes:1500}}));
    render(<RouteReferenceTimes shipmentId="shipment" plans={plans}/>);
    expect(await screen.findByText("مبنای ثبت‌شده برنامه · نسخه مرجع 1")).toBeInTheDocument();
    expect(screen.getByText("مرجع قابل استفاده · نسخه 2")).toBeInTheDocument();
    expect(api.select).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"ثبت این نسخه برای برنامه"}));
    await waitFor(()=>expect(api.select).toHaveBeenCalledWith("shipment",1,expect.objectContaining({selected:expect.objectContaining({selection_revision:1}),applicable:expect.objectContaining({public_id:"version-2"})}),expect.any(String)));
  });
  it("does not expose configuration or selection action for a read-only plan",async()=>{
    api.get.mockResolvedValue(response({...leg,can_select:false}));render(<RouteReferenceTimes shipmentId="shipment" plans={plans}/>);
    expect(await screen.findByText("مبنای این برنامه فقط خواندنی است.")).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"ثبت این نسخه برای برنامه"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"ثبت نسخه تازه"})).not.toBeInTheDocument();
  });
  it("discards a delayed result after switching plans",async()=>{
    let finish!:(value:ReturnType<typeof response>)=>void;
    api.get.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;})).mockResolvedValue(response({...leg,origin_label:"برنامه دوم"}));
    render(<RouteReferenceTimes shipmentId="shipment" plans={[...plans,{id:2,revision_number:2,status:"draft"}]}/>);
    fireEvent.change(screen.getByLabelText("برنامه مبنای زمان"),{target:{value:"2"}});
    expect(await screen.findByText(/برنامه دوم/)).toBeInTheDocument();
    finish(response({...leg,origin_label:"پاسخ قدیمی"}));
    await waitFor(()=>expect(screen.queryByText(/پاسخ قدیمی/)).not.toBeInTheDocument());
  });
  it("Admin shows no configured default and preserves version history on update",async()=>{
    const reference={public_id:"reference",origin_label:"خورگوس",destination_label:"آکتائو",transport_mode:"rail",latest_version:1,current:version,versions:[version]};
    api.list.mockResolvedValue({data:{items:[reference],page:1,total:1,has_next:false}});
    api.revise.mockResolvedValue({data:{public_id:"version-2",created:true}});
    render(<OrganizationRouteTimesTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"ثبت نسخه تازه"}));
    fireEvent.change(screen.getByLabelText("حداقل حرکت (ساعت)"),{target:{value:"25"}});
    fireEvent.change(screen.getByLabelText("حداکثر حرکت (ساعت)"),{target:{value:"30"}});
    fireEvent.change(screen.getByLabelText("شروع اعتبار"),{target:{value:"2030-01-01T09:00"}});
    fireEvent.click(screen.getByRole("button",{name:"ثبت زمان مرجع"}));
    await waitFor(()=>expect(api.revise).toHaveBeenCalledWith("reference",expect.objectContaining({expected_version:1,movement_min_minutes:1500,movement_max_minutes:1800,stop_min_minutes:240,stop_max_minutes:480}),expect.any(String)));
    expect(reference.versions[0].movement_min_minutes).toBe(1200);
  });
  it("uses the complete canonical Country source and persists country-bound canonical locations without raw enums",async()=>{
    render(<OrganizationRouteTimesTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"تعریف زمان مرجع تازه"}));
    const originCountry=await screen.findByLabelText("مبدأ مرجع کشور");
    const destinationCountry=screen.getByLabelText("مقصد مرجع کشور");
    expect(screen.getAllByRole("option",{name:"آندورا · AD"})).toHaveLength(2);
    expect(screen.queryByRole("option",{name:/قدیمی/})).not.toBeInTheDocument();
    fireEvent.change(originCountry,{target:{value:"1"}});
    fireEvent.change(destinationCountry,{target:{value:"1"}});
    const originLocation=await screen.findByLabelText("مبدأ مرجع مکان");
    const destinationLocation=screen.getByLabelText("مقصد مرجع مکان");
    await waitFor(()=>expect(originLocation).toHaveTextContent("استان — اصفهان"));
    expect(destinationLocation).toHaveTextContent("بندر — بندرعباس");
    expect(document.body).not.toHaveTextContent("international_city");
    expect(api.iran).toHaveBeenCalledWith("",50,"international_city");
    fireEvent.change(originLocation,{target:{value:"province:10"}});
    fireEvent.change(destinationLocation,{target:{value:"international_city:59"}});
    fireEvent.change(screen.getByLabelText("روش حمل مرجع"),{target:{value:"road"}});
    fireEvent.change(screen.getByLabelText("حداقل حرکت (ساعت)"),{target:{value:"6"}});
    fireEvent.change(screen.getByLabelText("حداکثر حرکت (ساعت)"),{target:{value:"8"}});
    fireEvent.change(screen.getByLabelText("شروع اعتبار"),{target:{value:"2026-10-01T09:00"}});
    fireEvent.click(screen.getByRole("button",{name:"ثبت زمان مرجع"}));
    await waitFor(()=>expect(api.create).toHaveBeenCalledWith(expect.objectContaining({
      origin:{country_id:1,source_type:"province",source_id:10},
      destination:{country_id:1,source_type:"international_city",source_id:59},
      transport_mode:"road",
    }),expect.any(String)));
    expect(api.countries).toHaveBeenCalledTimes(1);
  });
  it("shows explicit loading, empty, and backend error states",async()=>{
    api.iran.mockResolvedValue({data:[],meta:{count:0,limit:50}});
    let finishPoints!:(value:{items:never[];page:number;pages:number;total:number})=>void;
    api.points.mockImplementationOnce(()=>new Promise(resolve=>{finishPoints=resolve;}));
    render(<OrganizationRouteTimesTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"تعریف زمان مرجع تازه"}));
    fireEvent.change(await screen.findByLabelText("مبدأ مرجع کشور"),{target:{value:"1"}});
    expect(await screen.findByRole("status",{name:""})).toHaveTextContent("در حال جست‌وجوی مکان‌های معتبر");
    finishPoints({items:[],page:1,pages:0,total:0});
    await waitFor(()=>expect(screen.queryByText("در حال جست‌وجوی مکان‌های معتبر…")).not.toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("مبدأ مرجع جست‌وجوی مکان"),{target:{value:"ناشناخته"}});
    fireEvent.click(screen.getAllByRole("button",{name:"جست‌وجو"})[0]);
    expect(await screen.findByText("مکان معتبر منطبق با این جست‌وجو یافت نشد.")).toBeInTheDocument();
    api.points.mockRejectedValueOnce(new Error("network"));
    fireEvent.click(screen.getAllByRole("button",{name:"جست‌وجو"})[0]);
    expect(await screen.findByRole("alert")).toHaveTextContent("دوباره جست‌وجو کنید");
  });
  it("does not turn Persian free text into endpoint identity",async()=>{
    api.iran.mockResolvedValue({data:[],meta:{count:0,limit:50}});
    api.points.mockResolvedValue({items:[],page:1,pages:0,total:0});
    api.provinces.mockResolvedValue({items:[]});
    render(<OrganizationRouteTimesTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"تعریف زمان مرجع تازه"}));
    fireEvent.change(await screen.findByLabelText("مبدأ مرجع کشور"),{target:{value:"1"}});
    fireEvent.change(screen.getByLabelText("مبدأ مرجع جست‌وجوی مکان"),{target:{value:"اصفهان"}});
    fireEvent.click(screen.getAllByRole("button",{name:"جست‌وجو"})[0]);
    await screen.findByText("مکان معتبر منطبق با این جست‌وجو یافت نشد.");
    fireEvent.change(screen.getByLabelText("روش حمل مرجع"),{target:{value:"road"}});
    fireEvent.change(screen.getByLabelText("حداقل حرکت (ساعت)"),{target:{value:"6"}});
    fireEvent.change(screen.getByLabelText("حداکثر حرکت (ساعت)"),{target:{value:"8"}});
    fireEvent.change(screen.getByLabelText("شروع اعتبار"),{target:{value:"2026-10-01T09:00"}});
    fireEvent.click(screen.getByRole("button",{name:"ثبت زمان مرجع"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("مبدأ، مقصد و روش حمل را انتخاب کنید");
    expect(api.create).not.toHaveBeenCalled();
  });
  it("requests only canonically bound international locations for new Route References",async()=>{
    render(<OrganizationRouteTimesTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"تعریف زمان مرجع تازه"}));
    fireEvent.change(await screen.findByLabelText("مبدأ مرجع کشور"),{target:{value:"2"}});
    await waitFor(()=>expect(api.international).toHaveBeenCalledWith(2,"",0,undefined,true));
  });
});
