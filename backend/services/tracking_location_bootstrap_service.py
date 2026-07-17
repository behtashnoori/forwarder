"""Idempotent curated China-to-Iran tracking checkpoint bootstrap."""
from backend.extensions import db
from backend.models import TrackingLocationReference

ROWS=[
 ("cn-shanghai","شانگهای","Shanghai","CN","seaport",[]),("cn-ningbo-zhoushan","نینگبو-ژوشان","Ningbo-Zhoushan","CN","seaport",[]),("cn-shenzhen-yantian","شنژن / یانتیان","Shenzhen / Yantian","CN","seaport",[]),("cn-guangzhou-nansha","گوانگژو / نانشا","Guangzhou / Nansha","CN","seaport",[]),("cn-qingdao","چینگدائو","Qingdao","CN","seaport",[]),("cn-tianjin-xingang","تیانجین / شینگانگ","Tianjin / Xingang","CN","seaport",[]),("cn-lianyungang","لیانیونگانگ","Lianyungang","CN","rail_terminal",[]),("cn-yiwu","ایوو","Yiwu","CN","commercial_hub",["Yiwu","ایوو","یی‌وو","یی وو"]),("cn-xian","شی‌آن","Xi'an","CN","rail_terminal",["Xi'an","Xian","شی‌آن","شیان"]),("cn-zhengzhou","ژنگژو","Zhengzhou","CN","rail_terminal",[]),("cn-chengdu","چنگدو","Chengdu","CN","rail_terminal",[]),("cn-chongqing","چونگ‌چینگ","Chongqing","CN","rail_terminal",[]),("cn-wuhan","ووهان","Wuhan","CN","rail_terminal",[]),("cn-lanzhou","لانژو","Lanzhou","CN","rail_terminal",[]),("cn-urumqi","اورومچی","Urumqi","CN","transit_city",[]),("cn-kashgar","کاشغر","Kashgar","CN","transit_city",[]),("cn-alashankou","آلاشانکو","Alashankou","CN","border_point",[]),("cn-khorgos","خورگوس","Khorgos","CN","border_point",[]),
 ("kz-dostyk","دوستیک","Dostyk","KZ","border_point",[]),("kz-altynkol","آلتین‌کول","Altynkol","KZ","border_point",[]),("kz-almaty","آلماتی","Almaty","KZ","transit_city",[]),("kz-shymkent","شیمکنت","Shymkent","KZ","transit_city",[]),("KG-OSH","اوش","Osh","KG","commercial_hub",["Osh","Ош","اوش"]),("uz-tashkent","تاشکند","Tashkent","UZ","transit_city",[]),("uz-samarkand","سمرقند","Samarkand","UZ","transit_city",[]),("uz-navoi","نوایی","Navoi","UZ","transit_city",[]),("uz-bukhara","بخارا","Bukhara","UZ","transit_city",[]),("tm-alat","آلات","Alat","TM","border_point",[]),("tm-farap","فاراپ","Farap","TM","border_point",[]),("tm-turkmenabat","ترکمن‌آباد","Turkmenabat","TM","transit_city",[]),("tm-mary","مرو","Mary","TM","transit_city",[]),("tm-tejen","تجن","Tejen","TM","transit_city",[]),("tm-serakhs","سرخس ترکمنستان","Serakhs","TM","border_point",[]),("tm-etrek","اترک","Etrek","TM","border_point",[]),("kz-aktau","آکتائو","Aktau","KZ","seaport",[]),("tm-turkmenbashi","ترکمن‌باشی","Turkmenbashi","TM","seaport",[]),
 ("pk-sost","سوست","Sost","PK","border_point",[]),("pk-islamabad","اسلام‌آباد","Islamabad","PK","transit_city",[]),("pk-quetta","کویته","Quetta","PK","transit_city",[]),("pk-taftan","تفتان","Taftan","PK","border_point",[]),("pk-karachi","کراچی","Karachi","PK","seaport",[]),("pk-port-qasim","بندر قاسم","Port Qasim","PK","seaport",[]),("pk-gwadar","گوادر","Gwadar","PK","seaport",[]),("pk-gabd","گبد","Gabd","PK","border_point",[]),("af-herat","هرات","Herat","AF","transit_city",[]),("af-islam-qala","اسلام‌قلعه","Islam Qala","AF","border_point",[]),("af-zaranj","زرنج","Zaranj","AF","border_point",[]),
 ("ir-sarakhs","سرخس","Sarakhs","IR","iran_gateway",[]),("ir-incheh-borun","اینچه‌برون","Incheh Borun","IR","iran_gateway",[]),("ir-mirjaveh","میرجاوه","Mirjaveh","IR","iran_gateway",[]),("ir-dogharoun","دوغارون","Dogharoun","IR","iran_gateway",[]),("ir-rimdan","ریمدان","Rimdan","IR","iran_gateway",[]),("ir-mashhad","مشهد","Mashhad","IR","destination_city",[]),("ir-zahedan","زاهدان","Zahedan","IR","destination_city",[]),("ir-tehran","تهران","Tehran","IR","destination_city",[]),("ir-qom","قم","Qom","IR","destination_city",[]),("ir-isfahan","اصفهان","Isfahan","IR","destination_city",[]),("ir-yazd","یزد","Yazd","IR","destination_city",[]),("ir-kerman","کرمان","Kerman","IR","destination_city",[]),("ir-shahid-rajaee","بندر شهید رجایی","Shahid Rajaee Port","IR","iran_gateway",[]),("ir-chabahar","بندر چابهار","Chabahar Port","IR","iran_gateway",[]),("ir-imam-khomeini","بندر امام خمینی","Imam Khomeini Port","IR","iran_gateway",[]),("ir-amirabad","بندر امیرآباد","Amirabad Port","IR","iran_gateway",[]),("ir-anzali-caspian","بندر انزلی / کاسپین","Anzali / Caspian Port","IR","iran_gateway",[]),
]

NOTES = {
    "KG-OSH": (
        "هاب ترانزیتی جاده‌ای و ریلی در جنوب قرقیزستان؛ قابل استفاده در "
        "گزارش‌های دستی ردیابی محموله‌های مسیر چین به ایران."
    ),
}

def bootstrap(*,apply=False):
    counts={"inserted":0,"updated":0,"unchanged":0,"total":len(ROWS),"applied":apply}
    for order,(key,fa,en,country,kind,aliases) in enumerate(ROWS):
        row=TrackingLocationReference.query.filter_by(internal_key=key).one_or_none()
        if row is None: counts["inserted"]+=1
        else:
            desired=(fa,en,country,kind,aliases,"internal_reference",order,True,NOTES.get(key))
            current=(row.name_fa,row.name_en,row.country_code,row.location_type,row.aliases or [],row.reference_status,row.sort_order,row.is_active,row.notes)
            counts["updated" if current!=desired else "unchanged"]+=1
        if apply:
            if row is None:
                row=TrackingLocationReference(
                    internal_key=key,country_code=country,location_type=kind,
                    is_active=True,reference_status="internal_reference",
                );db.session.add(row)
            row.name_fa=fa;row.name_en=en;row.country_code=country;row.location_type=kind
            row.aliases=aliases;row.reference_status="internal_reference";row.sort_order=order
            row.is_active=True;row.notes=NOTES.get(key)
    if apply: db.session.commit()
    else: db.session.rollback()
    return counts
