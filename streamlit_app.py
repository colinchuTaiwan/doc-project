"""
admin_app.py — 公文專案管理系統（Streamlit Cloud + Firebase）

requirements.txt：
    streamlit
    firebase-admin
    requests

"""

import streamlit as st
import json
import os
import time
import zipfile
import io
import requests
from datetime import datetime, date, timedelta

# =========================
# Firebase 初始化
# =========================

import firebase_admin
from firebase_admin import credentials, db as firebase_db

@st.cache_resource
def init_firebase():
    if firebase_admin._apps:
        return firebase_admin.get_app()
    s = st.secrets["firebase"]
    cert = {
        "type":                        s["type"],
        "project_id":                  s["project_id"],
        "private_key_id":              s["private_key_id"],
        "private_key":                 s["private_key"].replace("\\n", "\n"),
        "client_email":                s["client_email"],
        "client_id":                   s["client_id"],
        "auth_uri":                    s["auth_uri"],
        "token_uri":                   s["token_uri"],
        "client_x509_cert_url":        s.get("client_x509_cert_url", ""),
        "auth_provider_x509_cert_url": s.get("auth_provider_x509_cert_url", ""),
    }
    cred = credentials.Certificate(cert)
    return firebase_admin.initialize_app(cred, {"databaseURL": s["database_url"]})

# =========================
# Firebase CRUD
# =========================

def save_project(data: dict) -> str:
    init_firebase()
    ref = firebase_db.reference("projects")
    new_ref = ref.push(data)
    load_projects_cached.clear()
    return new_ref.key

def update_project(fb_key: str, data: dict):
    init_firebase()
    firebase_db.reference(f"projects/{fb_key}").update(data)
    load_projects_cached.clear()

def delete_project(fb_key: str):
    init_firebase()
    firebase_db.reference(f"projects/{fb_key}").delete()
    load_projects_cached.clear()

@st.cache_data(ttl=30)
def load_projects_cached() -> list:
    init_firebase()
    data = firebase_db.reference("projects").get()
    if not data:
        return []
    result = []
    for k, v in data.items():
        v["_fb_key"] = k
        result.append(v)
    return sorted(result, key=lambda x: x.get("recvdate", ""), reverse=True)

# =========================
# ZIP 產生
# =========================

def folder_name(d: dict) -> str:
    date_str = (d.get("recvdate") or "00000000").replace("-", "")
    subject  = (d.get("subject") or "無主旨")[:20]
    for ch in r'/\:*?"<>|':
        subject = subject.replace(ch, "")
    return f"{date_str}_{subject}"

def build_project_record(d: dict) -> str:
    dl = d.get("deadline", "未設定")
    return f"""╔═══════════════════════════════════════════╗
║           📋 專 案 紀 錄 文 件             ║
╚═══════════════════════════════════════════╝

【基本資訊】
建立日期：{d.get('createdAt','')}
公文字號：{d.get('docnum','')}
來文機關：{d.get('origin','')}
公文主旨：{d.get('subject','')}
案件類型：{d.get('type','')}
收文日期：{d.get('recvdate','')}
辦理期限：{dl}

【承辦資訊】
承辦人：{d.get('owner','')}（{d.get('dept','')}）
協辦人員：{d.get('coowner','無')}
聯絡信箱：{d.get('email','未填')}

【辦理說明】
{d.get('notes','（未填寫）')}

預算金額：{'NT$ ' + d['budget'] if d.get('budget') else '無經費需求'}
預計成果：{d.get('outcome','（未填寫）')}

═══════════════════════════════════════════"""

def build_todo(d: dict) -> str:
    return f"""╔═══════════════════════════════════════════╗
║              ✅ 待 辦 追 蹤 表              ║
╚═══════════════════════════════════════════╝

專案：{d.get('subject','')}
承辦人：{d.get('owner','')}　期限：{d.get('deadline','未設定')}

─────────────────────────────────────
【行政前置作業】
□ 詳閱公文及附件
□ 確認辦理期限與需求
□ 向主管報告 / 取得授權
□ 確認協辦人員名單
□ 建立本資料夾並歸檔公文

【計畫與準備】
□ 草擬計畫書 / 活動規劃
□ 計畫書提交主管審核
□ 確認場地 / 時間安排
□ 確認講師 / 資源需求
□ 完成採購或委託程序（如需）

【執行作業】
□ 發送邀請 / 公告通知
□ 收集報名 / 回覆資料
□ 完成現場佈置與執行
□ 拍攝活動照片
□ 收集簽到表 / 問卷

【後續追蹤】
□ 整理活動照片並附說明
□ 彙整問卷 / 統計回饋
□ 完成核銷 / 決算
□ 撰寫成果報告
□ 歸檔所有文件
□ 提交 / 回覆上級機關

═══════════════════════════════════════════"""

def build_checklist(d: dict) -> str:
    return f"""╔═══════════════════════════════════════════╗
║              📊 成 果 檢 核 表              ║
╚═══════════════════════════════════════════╝

專案：{d.get('subject','')}
預計成果：{d.get('outcome','（未填寫）')}
辦理期限：{d.get('deadline','未設定')}

─────────────────────────────────────
【文件完整性】
□ 原始公文已歸檔
□ 計畫書（核定版）已存檔
□ 工作分工表已建立
□ 會議紀錄（全部場次）已存檔
□ 出席簽到表已彙整
□ 表單與回覆資料已整理

【活動執行】
□ 活動如期辦理
□ 參與人數達預期目標
□ 照片拍攝完整並附說明
□ 問卷 / 滿意度調查已完成

【經費核銷】
□ 經費使用符合計畫
□ 憑證 / 收據齊全
□ 核銷申請已提交
□ 決算報告完成

【成果報告】
□ 成果報告書完成
□ 統計數據正確
□ 報告已提交上級
□ 回覆公文已發出（如需）

─────────────────────────────────────
下次辦理建議：（完成後填寫）

═══════════════════════════════════════════"""

def build_deadline_reminder(d: dict) -> str:
    dl_str = d.get("deadline", "")
    if dl_str:
        dl = datetime.strptime(dl_str, "%Y-%m-%d")
        days_left = (dl - datetime.now()).days
        urgency = "⚠️ 緊急" if days_left <= 7 else "⏰ 注意" if days_left <= 14 else "✅ 充裕"
        p14 = (dl - timedelta(days=14)).strftime("%Y-%m-%d")
        p7  = (dl - timedelta(days=7)).strftime("%Y-%m-%d")
        p3  = (dl - timedelta(days=3)).strftime("%Y-%m-%d")
        timeline = f"""• 期限前 14 天 → {p14} — 完成計畫書與準備工作
• 期限前 7 天  → {p7} — 完成主要執行事項
• 期限前 3 天  → {p3} — 完成文件整理與報告
• 期限日       → {dl_str} — 提交成果 / 回覆公文"""
    else:
        days_left = None
        urgency = ""
        timeline = "請設定辦理期限後重新建立"

    return f"""╔═══════════════════════════════════════════╗
║              ⏰ 期 限 提 醒 表              ║
╚═══════════════════════════════════════════╝

專案：{d.get('subject','')}
承辦人：{d.get('owner','')}

【關鍵日期】
收文日期：{d.get('recvdate','未設定')}
辦理期限：{dl_str or '未設定'}
剩餘天數：{str(days_left) + ' 天 ' + urgency if days_left is not None else '未設定'}

【建議時程規劃】
{timeline}

═══════════════════════════════════════════"""

def generate_zip_bytes(d: dict) -> bytes:
    root = folder_name(d)
    buf  = io.BytesIO()
    folders = [
        ("01_原始公文與附件",   "存放原始來文公文、附件、相關法規"),
        ("02_計畫書與核定資料", "存放計畫書草稿與核定文件"),
        ("03_工作分工與會議紀錄","存放工作分配表與歷次會議紀錄"),
        ("04_表單與回覆資料",   "存放對外表單與收集回覆"),
        ("05_經費與採購核銷",   "存放所有經費相關文件"),
        ("06_活動照片與說明",   "存放活動照片與文字說明"),
        ("07_成果資料與報告",   "存放成果相關資料"),
    ]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{root}/00_專案紀錄.txt",   build_project_record(d))
        zf.writestr(f"{root}/待辦追蹤表.txt",     build_todo(d))
        zf.writestr(f"{root}/成果檢核表.txt",     build_checklist(d))
        zf.writestr(f"{root}/期限提醒.txt",       build_deadline_reminder(d))
        for name, desc in folders:
            zf.writestr(
                f"{root}/{name}/README.txt",
                f"本資料夾用途：{desc}\n\n專案：{d.get('subject','')}\n承辦人：{d.get('owner','')}"
            )
    return buf.getvalue()

# =========================
# Gemini API
# =========================

def call_gemini(api_key: str, prompt: str) -> str:
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    last_err = None
    for model in models:
        for attempt in range(1, 3):
            try:
                url  = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                body = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "systemInstruction": {"parts": [{"text": "你是台灣學校行政人員，擅長公文寫作。請使用繁體中文，語氣正式，格式清楚，內容可直接複製使用。"}]},
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
                }
                resp = requests.post(url, json=body, timeout=30)
                if not resp.ok:
                    err = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
                    raise Exception(err)
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            except Exception as e:
                last_err = e
                if attempt < 2:
                    time.sleep(2)
    raise last_err or Exception("Gemini 呼叫失敗")

# =========================
# 頁面設定
# =========================

st.set_page_config(page_title="公文專案管理系統", page_icon="📋", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }
.project-meta { font-size:12px; color:#666; }
</style>
""", unsafe_allow_html=True)

# =========================
# Session 初始化
# =========================

if "page" not in st.session_state:
    st.session_state.page = "home"
if "selected_project" not in st.session_state:
    st.session_state.selected_project = None
if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = ""

# =========================
# Header
# =========================

col_logo, col_nav = st.columns([3, 5])
with col_logo:
    st.markdown("## 📋 公文專案管理系統")
    st.caption("收文即啟動・自動建資料夾・AI 輔助產稿")
with col_nav:
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🏠 首頁",       use_container_width=True,
                 type="primary" if st.session_state.page=="home"     else "secondary"):
        st.session_state.page = "home"; st.rerun()
    if c2.button("📁 專案列表",    use_container_width=True,
                 type="primary" if st.session_state.page=="projects" else "secondary"):
        st.session_state.page = "projects"; st.rerun()
    if c3.button("＋ 啟動新專案",  use_container_width=True,
                 type="primary" if st.session_state.page=="form"     else "secondary"):
        st.session_state.page = "form"; st.rerun()
    if c4.button("🤖 AI 草稿助理", use_container_width=True,
                 type="primary" if st.session_state.page=="ai"       else "secondary"):
        st.session_state.page = "ai"; st.rerun()

st.divider()

# =========================
# 首頁
# =========================

if st.session_state.page == "home":
    st.markdown("### 使用流程")
    cols = st.columns(5)
    for i, (icon, label) in enumerate([
        ("📥","填表啟動"), ("📦","下載 ZIP"),
        ("✅","追蹤進度"), ("🤖","AI 產稿"), ("📊","成果報告")
    ]):
        cols[i].markdown(f"""
        <div style='text-align:center;padding:16px;background:#eff6ff;border-radius:8px;border:1px solid #bfdbfe'>
        <div style='font-size:28px'>{icon}</div>
        <div style='font-weight:700;margin-top:6px;font-size:13px'>{i+1}. {label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.info("📌 收到公文後，點擊「＋ 啟動新專案」填表，系統自動建立完整資料夾結構並產生追蹤文件，下載 ZIP 即可使用。")

    st.markdown("### 資料夾結構")
    st.code("""📁 [收文日期_公文主旨]/
├── 📄 00_專案紀錄.txt
├── 📄 待辦追蹤表.txt
├── 📄 成果檢核表.txt
├── 📄 期限提醒.txt
├── 📁 01_原始公文與附件/
├── 📁 02_計畫書與核定資料/
├── 📁 03_工作分工與會議紀錄/
├── 📁 04_表單與回覆資料/
├── 📁 05_經費與採購核銷/
├── 📁 06_活動照片與說明/
└── 📁 07_成果資料與報告/""", language="")

# =========================
# 啟動新專案
# =========================

elif st.session_state.page == "form":
    st.markdown("### 📝 公文專案啟動表")
    st.warning("標有 ＊ 的欄位為必填")

    with st.form("project_form"):
        st.markdown("**▌ 公文基本資訊**")
        c1, c2 = st.columns(2)
        docnum   = c1.text_input("來文字號 ＊", placeholder="例：教部技字第1130012345號")
        origin   = c2.text_input("來文機關 ＊", placeholder="例：教育部")
        subject  = st.text_input("公文主旨 ＊", placeholder="例：辦理112學年度數位教學增能研習")
        c3, c4, c5 = st.columns(3)
        recvdate = c3.date_input("收文日期 ＊", value=date.today())
        deadline = c4.date_input("辦理期限 ＊", value=date.today() + timedelta(days=30))
        ptype    = c5.selectbox("案件類型", ["研習/研討會","計畫申請","活動辦理","調查填報","採購案","公告事項","其他"])

        st.markdown("**▌ 承辦資訊**")
        c6, c7 = st.columns(2)
        owner   = c6.text_input("承辦人 ＊", placeholder="姓名")
        email   = c7.text_input("承辦人 Email", placeholder="xxx@school.edu.tw")
        c8, c9 = st.columns(2)
        dept    = c8.text_input("單位名稱", placeholder="例：教務處")
        coowner = c9.text_input("協辦人員", placeholder="可填多位，以逗號分隔")

        st.markdown("**▌ 專案說明**")
        notes   = st.text_area("辦理要點", placeholder="簡述本次公文需要辦理的事項、注意事項...")
        c10, c11 = st.columns(2)
        budget  = c10.text_input("預算金額（元）", placeholder="例：50000（無則留白）")
        outcome = c11.text_input("預計成果", placeholder="例：辦理研習 1 場、參與人數 30 人")

        submitted = st.form_submit_button("📦 建立專案並下載 ZIP", type="primary", use_container_width=True)

    if submitted:
        if not all([docnum, origin, subject, owner]):
            st.error("請填寫所有必填欄位（來文字號、來文機關、公文主旨、承辦人）")
        else:
            project = {
                "docnum":    docnum,
                "origin":    origin,
                "subject":   subject,
                "recvdate":  recvdate.strftime("%Y-%m-%d"),
                "deadline":  deadline.strftime("%Y-%m-%d"),
                "type":      ptype,
                "owner":     owner,
                "email":     email,
                "dept":      dept,
                "coowner":   coowner,
                "notes":     notes,
                "budget":    budget,
                "outcome":   outcome,
                "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status":    "進行中",
            }
            with st.spinner("儲存專案並產生 ZIP..."):
                fb_key = save_project(project)
                project["_fb_key"] = fb_key
                zip_bytes = generate_zip_bytes(project)

            fname = folder_name(project) + ".zip"
            st.success(f"✅ 專案「{subject}」已建立！")
            st.download_button(
                label="⬇️ 下載專案 ZIP",
                data=zip_bytes,
                file_name=fname,
                mime="application/zip",
                use_container_width=True,
                type="primary",
            )
            if email:
                dl_fmt = deadline.strftime("%Y-%m-%d")
                mailto = (
                    f"mailto:{email}"
                    f"?subject=%E3%80%90%E5%85%AC%E6%96%87%E5%B0%88%E6%A1%88%E5%95%9F%E5%8B%95%E3%80%91{subject[:20]}"
                    f"&body=%E6%82%A8%E5%A5%BD%EF%BC%8C%0A%0A%E4%BB%A5%E4%B8%8B%E5%B0%88%E6%A1%88%E5%B7%B2%E5%BB%BA%E7%AB%8B%EF%BC%9A%0A%E4%B8%BB%E6%97%A8%EF%BC%9A{subject}%0A%E6%9C%9F%E9%99%90%EF%BC%9A{dl_fmt}"
                )
                st.markdown(f"[📧 點此發送 Email 通知給 {email}]({mailto})")

# =========================
# 專案列表
# =========================

elif st.session_state.page == "projects":

    if st.session_state.selected_project:
        p = st.session_state.selected_project
        if st.button("← 返回列表"):
            st.session_state.selected_project = None
            st.rerun()

        st.markdown(f"### 📋 {p.get('subject','')}")
        st.caption(f"{p.get('origin','')} ／ {p.get('owner','')} ／ {p.get('type','')} ／ 建立：{p.get('createdAt','')}")

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("#### ✅ 待辦事項")
            todos = [
                "詳閱公文及附件","確認辦理期限","向主管報告取得授權",
                "草擬計畫書","確認場地時間","發送通知公告",
                "收集報名回覆","完成現場執行","整理照片成果",
                "撰寫成果報告","完成核銷決算","歸檔所有文件",
            ]
            for t in todos:
                st.checkbox(t, key=f"todo_{t}_{p.get('_fb_key','')}")

        with col_right:
            st.markdown("#### 📅 重要時程")
            dl_str = p.get("deadline", "")
            if dl_str:
                dl = datetime.strptime(dl_str, "%Y-%m-%d")
                items = [
                    (p.get("recvdate","—"), "收文・專案建立"),
                    ((dl - timedelta(days=14)).strftime("%Y-%m-%d"), "建議完成計畫書"),
                    ((dl - timedelta(days=7)).strftime("%Y-%m-%d"),  "建議完成主要執行事項"),
                    ((dl - timedelta(days=3)).strftime("%Y-%m-%d"),  "建議完成文件整理"),
                    (dl_str, "⚠️ 辦理期限"),
                ]
                for d_item, label in items:
                    st.markdown(f"- `{d_item}` {label}")
            else:
                st.info("未設定辦理期限")

        st.markdown("#### 📊 成果檢核表")
        checks = ["文件完整歸檔","活動如期辦理","照片及說明完整","問卷資料彙整","核銷文件齊全","成果報告完成","已回覆上級機關"]
        for c in checks:
            st.checkbox(c, key=f"chk_{c}_{p.get('_fb_key','')}")

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            zip_bytes = generate_zip_bytes(p)
            st.download_button("📦 重新下載 ZIP", data=zip_bytes,
                               file_name=folder_name(p)+".zip",
                               mime="application/zip", use_container_width=True)
        with c2:
            if st.button("🤖 AI 草稿", use_container_width=True):
                st.session_state.ai_context = f"""公文主旨：{p.get('subject','')}
來文機關：{p.get('origin','')}
公文字號：{p.get('docnum','')}
案件類型：{p.get('type','')}
辦理期限：{p.get('deadline','')}
承辦人：{p.get('owner','')}（{p.get('dept','')}）
辦理要點：{p.get('notes','')}
預計成果：{p.get('outcome','')}"""
                st.session_state.page = "ai"
                st.rerun()
        with c3:
            if st.button("🗑️ 刪除專案", use_container_width=True, type="secondary"):
                delete_project(p["_fb_key"])
                st.session_state.selected_project = None
                st.success("專案已刪除")
                st.rerun()

    else:
        st.markdown("### 📁 專案列表")
        col_h, col_btn = st.columns([6, 2])
        col_h.caption("點擊專案查看詳情")
        if col_btn.button("＋ 新增專案", type="primary"):
            st.session_state.page = "form"; st.rerun()

        with st.spinner("載入專案..."):
            projects = load_projects_cached()

        if not projects:
            st.info("尚無專案記錄，點擊「＋ 啟動新專案」開始。")
        else:
            today = datetime.now()
            for p in projects:
                dl_str = p.get("deadline", "")
                if dl_str:
                    dl = datetime.strptime(dl_str, "%Y-%m-%d")
                    days_left = (dl - today).days
                    if days_left < 0:
                        badge = "🔴 已逾期"
                    elif days_left <= 7:
                        badge = f"🔴 剩 {days_left} 天"
                    elif days_left <= 14:
                        badge = f"🟡 剩 {days_left} 天"
                    else:
                        badge = f"🟢 剩 {days_left} 天"
                else:
                    badge = "⚪ 無期限"

                with st.container(border=True):
                    c1, c2 = st.columns([7, 2])
                    with c1:
                        st.markdown(f"**{p.get('subject','')}**")
                        st.caption(f"{p.get('origin','')} ／ {p.get('owner','')}（{p.get('dept','')}）／ {p.get('type','')} ／ {p.get('createdAt','')}")
                    with c2:
                        st.markdown(badge)
                        if st.button("查看", key=f"open_{p.get('_fb_key','')}"):
                            st.session_state.selected_project = p
                            st.rerun()

# =========================
# AI 草稿助理
# =========================

elif st.session_state.page == "ai":
    st.markdown("### 🤖 AI 草稿助理")

    with st.expander("⚙️ Gemini API Key 設定", expanded=not st.session_state.gemini_key):
        key_input = st.text_input("Google Gemini API Key", type="password",
                                  placeholder="AIzaSy...",
                                  value=st.session_state.gemini_key)
        if st.button("儲存 Key"):
            st.session_state.gemini_key = key_input
            st.success("✅ 已儲存")

    with st.spinner("載入專案..."):
        projects = load_projects_cached()

    project_options = {"── 手動輸入 ──": None}
    for p in projects:
        project_options[p.get("subject", p.get("_fb_key",""))] = p

    selected = st.selectbox("選擇專案（自動帶入內容）", list(project_options.keys()))
    p = project_options[selected]

    default_ctx = ""
    if p:
        default_ctx = f"""公文主旨：{p.get('subject','')}
來文機關：{p.get('origin','')}
公文字號：{p.get('docnum','')}
案件類型：{p.get('type','')}
辦理期限：{p.get('deadline','')}
承辦人：{p.get('owner','')}（{p.get('dept','')}）
辦理要點：{p.get('notes','')}
預計成果：{p.get('outcome','')}"""

    # 若是從專案詳情跳過來
    if hasattr(st.session_state, "ai_context") and st.session_state.ai_context:
        default_ctx = st.session_state.ai_context
        st.session_state.ai_context = ""

    context = st.text_area("公文 / 專案內容摘要", value=default_ctx, height=150,
                           placeholder="貼上公文主旨、辦理要點等...")

    draft_types = {
        "📌 公文重點摘要": "請將以下公文資訊整理成「公文重點摘要」，包含：主旨、辦理事項、注意事項、重要期限，適合在行政會議上報告。",
        "📢 校內公告":    "請根據以下資訊撰寫「校內公告」草稿，語氣正式友善，包含活動名稱、時間、參加對象、報名方式、注意事項。",
        "✅ 待辦清單":    "請根據以下資訊列出完整的「待辦清單」，分階段列出每個需要執行的任務，使用核取方塊格式（□）。",
        "📋 表單題目":    "請根據以下活動/計畫內容，設計一份「報名/調查表單」的題目清單，包含必要欄位、選填欄位，並說明每題的用途。",
        "📊 會議追蹤表":  "請根據以下資訊設計「會議追蹤表」範本，包含會議基本資訊、討論議題、決議事項、後續追蹤欄位。",
        "📄 成果報告初稿": "請根據以下資訊撰寫「成果報告書」初稿架構與部分內容，包含前言、辦理情形、成效分析、檢討建議，格式正式。",
        "🎯 簡報大綱":    "請根據以下資訊設計「成果簡報大綱」，包含每張投影片的標題與重點內容（3-5 個要點），適合在會議上報告。",
        "💡 下次辦理建議": "請根據以下辦理情形提出「下次辦理建議」，包含可改進之處、時程調整建議、資源準備建議、注意事項。",
    }

    draft_type = st.radio("選擇草稿類型", list(draft_types.keys()), horizontal=True)

    if st.button("✨ 產生草稿", type="primary", use_container_width=True):
        if not context.strip():
            st.warning("請先填寫公文 / 專案內容摘要")
        elif not st.session_state.gemini_key:
            st.warning("請先設定 Gemini API Key")
        else:
            prompt = f"""{draft_types[draft_type]}

請遵守：
1. 使用繁體中文
2. 台灣學校行政公文語氣
3. 條列清楚，可直接複製使用
4. 資料不足處標示「待補」

---
公文 / 專案內容：
{context}"""
            with st.spinner("Gemini 產生草稿中..."):
                try:
                    result = call_gemini(st.session_state.gemini_key, prompt)
                    st.session_state.draft_result = result
                except Exception as e:
                    st.error(f"❌ 錯誤：{e}")
                    st.session_state.draft_result = ""

    if st.session_state.get("draft_result"):
        st.markdown("---")
        st.markdown("#### 草稿輸出")
        st.text_area("", value=st.session_state.draft_result, height=400, key="draft_display")
        st.download_button("⬇️ 下載草稿", data=st.session_state.draft_result,
                           file_name="草稿.txt", mime="text/plain")
