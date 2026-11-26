import os
import sys
import io
import re
import json
import pickle
import tempfile
import gc
import atexit
import glob
import time
import shutil
import contextlib
import datetime as dt
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response, RedirectResponse
import requests as http_requests
import numpy as np
import pandas as pd
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database import (
    OWNER_EMAIL,
    MASTER_SCHEMAS,
    init_db,
    is_admin,
    list_users,
    set_user_role,
    get_user,
    record_user_login,
    get_user_google_token,
    save_user_google_token,
    create_user_session,
    get_session_user,
    delete_user_session,
    sync_two_sheet_supplier_excel,
    generate_temp_supplier_xlsx,
    generate_temp_daftar_barang_xlsx,
    harvest_from_sales_df,
    inspect_and_map_columns,
    learn_column_aliases,
    sync_master_dataframe,
    get_master_rows,
    upsert_master_row,
    delete_master_row,
    clear_master_table,
)

from scripts.excel_utils import pastikan_xlsx
import scripts.rangkuman_penjualan as rk
from scripts.doi_cabang import run_doi_pipeline, jenis_file as deteksi_jenis_doi
from navigation.dashboard_data import penjualan_data as pdata
from navigation.dashboard_data import doi_data as ddata
from navigation.dashboard_visual import penjualan as pvis
from navigation.dashboard_visual import doi as dvis
from navigation.dashboard_data.format_rp import fmt_rp, fmt_num

app = FastAPI(title="Nexus · Company Automation Hub API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = os.path.abspath(os.path.join(ROOT_DIR, "output"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

APP_STATE = {
    "rk_state": None,
    "doi_last_excel": None,
    "sales_dash_df": None,
    "sales_dash_auto_df": None,
    "doi_dash_cleared": False,
    "doi_dash_list": [],
}


@app.on_event("startup")
def on_startup():
    init_db()


# ---- UI React (frontend-react/dist). Bila belum di-build, UI lama (frontend/index.html) tetap dipakai ----
REACT_DIST = os.path.abspath(os.path.join(ROOT_DIR, "frontend-react", "dist"))
NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
if os.path.isdir(os.path.join(REACT_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(REACT_DIST, "assets")), name="react-assets")


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    react_index = os.path.join(REACT_DIST, "index.html")
    if os.path.exists(react_index):
        return FileResponse(react_index, headers=NO_CACHE)
    frontend_path = os.path.abspath(os.path.join(ROOT_DIR, "frontend", "index.html"))
    if os.path.exists(frontend_path):
        return FileResponse(
            frontend_path,
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
        )
    return HTMLResponse("<h3>File frontend/index.html belum ditemukan.</h3>")


OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SESSION_COOKIE_NAME = "bbi_session"
OAUTH_STATE_STORE = {}


def _find_client_secret_file() -> Optional[str]:
    candidates = [
        os.path.join(ROOT_DIR, "client_secret.json"),
        os.path.join(BASE_DIR, "client_secret.json"),
        os.path.join(os.getcwd(), "client_secret.json"),
        os.path.join(ROOT_DIR, "credentials.json"),
        os.path.join(BASE_DIR, "credentials.json"),
        os.path.join(os.getcwd(), "credentials.json"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    for root, dirs, files in os.walk(ROOT_DIR):
        if "client_secret.json" in files:
            return os.path.join(root, "client_secret.json")
        if "credentials.json" in files:
            return os.path.join(root, "credentials.json")
    return None


def _fetch_google_userinfo(creds) -> dict:
    r = http_requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError("Gagal mengambil profil akun Google.")
    return r.json()


def _load_google_creds(user_email: Optional[str] = None):
    from google.auth.transport.requests import Request as GoogleAuthRequest

    if user_email:
        raw = get_user_google_token(user_email)
        if raw:
            try:
                creds = pickle.loads(raw)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(GoogleAuthRequest())
                    save_user_google_token(user_email, pickle.dumps(creds))
                if creds and creds.valid:
                    return creds
            except Exception:
                pass

    token_path = os.path.join(ROOT_DIR, "token.pickle")
    if os.path.exists(token_path):
        try:
            with open(token_path, "rb") as f:
                creds = pickle.load(f)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(GoogleAuthRequest())
                with open(token_path, "wb") as f:
                    pickle.dump(creds, f)
            return creds
        except Exception:
            return None
    return None


def require_current_user(request: Request) -> dict:
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_session_user(sid)
    if not user:
        raise HTTPException(status_code=401, detail="Sesi login berakhir atau belum masuk. Silakan Sign in dengan Google.")
    return user


@app.get("/api/auth/me")
def api_auth_me(request: Request):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_session_user(sid)
    if not user:
        return {"authenticated": False}
    has_token = get_user_google_token(user["email"]) is not None or os.path.exists(os.path.join(ROOT_DIR, "token.pickle"))
    return {
        "authenticated": True,
        "user": {
            "email": user["email"],
            "name": user["name"] or user["email"],
            "role": user["role"],
            "is_admin": is_admin(user["email"]),
            "is_owner": user["email"].strip().lower() == OWNER_EMAIL.lower(),
            "picture": user.get("picture") or "",
            "gsheets_ready": has_token,
        },
    }


@app.get("/api/auth/google/login")
def api_google_login(request: Request):
    secret_file = _find_client_secret_file()
    if not secret_file:
        raise HTTPException(
            status_code=400,
            detail="File client_secret.json belum ditemukan di folder utama project. Letakkan client_secret.json sejajar dengan folder backend & frontend.",
        )

    with open(secret_file, "r", encoding="utf-8") as f:
        client_cfg = json.load(f)

    if "web" in client_cfg:
        from google_auth_oauthlib.flow import Flow
        redirect_uri = str(request.url_for("api_google_callback"))
        flow = Flow.from_client_secrets_file(secret_file, scopes=OAUTH_SCOPES, redirect_uri=redirect_uri)
        auth_url, state = flow.authorization_url(
            access_type="offline",
            prompt="select_account consent",
            include_granted_scopes="true",
        )
        # PKCE: google-auth-oauthlib versi baru membuat code_verifier saat authorization_url(); harus dibawa ke callback
        OAUTH_STATE_STORE[state] = {"redirect_uri": redirect_uri, "code_verifier": getattr(flow, "code_verifier", None)}
        return {"mode": "redirect", "auth_url": auth_url}

    from google_auth_oauthlib.flow import InstalledAppFlow
    try:
        flow = InstalledAppFlow.from_client_secrets_file(secret_file, OAUTH_SCOPES)
        creds = flow.run_local_server(port=0, prompt="select_account")
        info = _fetch_google_userinfo(creds)
        email = (info.get("email") or "").strip().lower()
        name = info.get("name") or email
        picture = info.get("picture") or ""
        token_bytes = pickle.dumps(creds)
        user = record_user_login(email, name, picture, token_bytes=token_bytes)
        with open(os.path.join(ROOT_DIR, "token.pickle"), "wb") as tf:
            tf.write(token_bytes)
        sid = create_user_session(user["email"])
        resp = Response(
            content=json.dumps({"mode": "completed", "user": user}),
            media_type="application/json",
        )
        resp.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=sid,
            httponly=True,
            max_age=14 * 86400,
            samesite="lax",
        )
        return resp
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal otorisasi Google: {e}")


@app.get("/auth/callback")
def api_google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error:
        return RedirectResponse(url=f"/?auth_error={error}")
    secret_file = _find_client_secret_file()
    if not secret_file or not code:
        return RedirectResponse(url="/?auth_error=missing_code")
    try:
        from google_auth_oauthlib.flow import Flow
        saved = OAUTH_STATE_STORE.pop(state, None) or {}
        redirect_uri = saved.get("redirect_uri") or str(request.url_for("api_google_callback"))
        flow = Flow.from_client_secrets_file(secret_file, scopes=OAUTH_SCOPES, state=state, redirect_uri=redirect_uri)
        if saved.get("code_verifier"):
            flow.code_verifier = saved["code_verifier"]  # sama dengan yang dipakai saat login dimulai
        flow.fetch_token(code=code)
        creds = flow.credentials
        info = _fetch_google_userinfo(creds)
        email = (info.get("email") or "").strip().lower()
        name = info.get("name") or email
        picture = info.get("picture") or ""
        token_bytes = pickle.dumps(creds)
        user = record_user_login(email, name, picture, token_bytes=token_bytes)
        with open(os.path.join(ROOT_DIR, "token.pickle"), "wb") as tf:
            tf.write(token_bytes)
        sid = create_user_session(user["email"])
        resp = RedirectResponse(url="/")
        resp.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=sid,
            httponly=True,
            max_age=14 * 86400,
            samesite="lax",
        )
        return resp
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse(url=f"/?auth_error={quote('Gagal login Google: ' + str(e))}")


@app.post("/api/auth/logout")
def api_logout(request: Request, response: Response):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    delete_user_session(sid)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"status": "SUCCESS", "message": "Berhasil keluar."}


def _auto_clean_header_df(df: pd.DataFrame) -> pd.DataFrame:
    unnamed_ratio = sum(1 for c in df.columns if str(c).startswith("Unnamed:")) / max(len(df.columns), 1)
    if unnamed_ratio >= 0.5:
        for r_idx in range(min(6, len(df))):
            row_vals = df.iloc[r_idx].values
            non_empty = [str(v).strip() for v in row_vals if pd.notna(v) and str(v).strip() and not str(v).startswith("Unnamed:")]
            if len(non_empty) >= 2:
                df = df.iloc[r_idx + 1:].reset_index(drop=True)
                df.columns = [str(v).strip() if pd.notna(v) and str(v).strip() else f"Unnamed: {i}" for i, v in enumerate(row_vals)]
                break
    keep_cols = [c for c in df.columns if not (str(c).startswith("Unnamed:") and df[c].isna().all())]
    return df[keep_cols]


@app.get("/api/overview")
def api_overview():
    out_files = []
    if os.path.exists(OUTPUT_DIR):
        for fn in sorted(os.listdir(OUTPUT_DIR), reverse=True):
            fp = os.path.join(OUTPUT_DIR, fn)
            if os.path.isfile(fp) and not fn.startswith("~$"):
                out_files.append({
                    "name": fn,
                    "size_kb": round(os.path.getsize(fp) / 1024, 1),
                    "mtime": dt.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%d %b %Y %H:%M"),
                })
    counts = {k: len(get_master_rows(k)) for k in MASTER_SCHEMAS}
    return {
        "output_count": len(out_files),
        "output_files": out_files[:20],
        "master_counts": counts,
        "rk_ready": APP_STATE["rk_state"] is not None,
        "doi_ready": APP_STATE["doi_last_excel"] is not None,
        "sales_dash_ready": (APP_STATE["sales_dash_df"] is not None) or (APP_STATE["rk_state"] is not None),
        "doi_dash_ready": bool(APP_STATE["doi_dash_list"]) or (APP_STATE["doi_last_excel"] is not None),
    }


@app.get("/api/users")
def api_get_users(current_user: dict = Depends(require_current_user)):
    return {
        "current_user": current_user["email"],
        "is_admin": is_admin(current_user["email"]),
        "users": list_users(),
    }


@app.post("/api/users")
def api_manage_user(
    email: str = Form(...),
    name: str = Form(""),
    role: str = Form("staff"),
    current_user: dict = Depends(require_current_user),
):
    if not is_admin(current_user["email"]):
        raise HTTPException(status_code=403, detail="Hanya Admin yang dapat mengatur izin akses.")
    try:
        set_user_role(email, name, role)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"message": f"Hak akses {email} diperbarui menjadi {role}."}


@app.get("/api/master/{entity_type}")
def api_get_master(entity_type: str):
    if entity_type not in MASTER_SCHEMAS:
        raise HTTPException(status_code=404, detail="Kategori Master tidak ditemukan.")
    cfg = MASTER_SCHEMAS[entity_type]
    counts = {k: len(get_master_rows(k)) for k in MASTER_SCHEMAS}
    return {
        "entity_type": entity_type,
        "title": cfg["title"],
        "pk": cfg["pk"],
        "fields": [{"field": k, "label": v["label"], "required": v["required"]} for k, v in cfg["fields"].items()],
        "rows": get_master_rows(entity_type),
        "counts": counts,
    }


@app.post("/api/master/{entity_type}/upload")
async def api_upload_master(
    entity_type: str,
    file: UploadFile = File(...),
    custom_mapping_json: Optional[str] = Form(None),
    current_user: dict = Depends(require_current_user),
):
    x_user_email = current_user["email"]
    if entity_type not in MASTER_SCHEMAS:
        raise HTTPException(status_code=404, detail="Kategori Master tidak dikenal.")

    contents = await file.read()
    fname = file.filename or "uploaded.xlsx"

    try:
        if fname.lower().endswith(".csv"):
            df = _auto_clean_header_df(pd.read_csv(io.BytesIO(contents)))
        else:
            xl = pd.ExcelFile(io.BytesIO(contents))
            if "Rekap" in xl.sheet_names and "Per Cabang" in xl.sheet_names and not custom_mapping_json:
                res = sync_two_sheet_supplier_excel(xl, user_email=x_user_email)
                return {
                    "status": "SUCCESS",
                    "message": (
                        f"File 2-Sheet Supplier.xlsx terdeteksi otomatis! "
                        f"Sheet Rekap: +{res['rekap_added']} baru (Total {res['rekap_total']}) · "
                        f"Sheet Per Cabang (Zeta): +{res['cabang_added']} baru (Total {res['cabang_total']})."
                    ),
                    "stats": res,
                }

            target_sheet = 0
            if entity_type == "supplier_rekap" and "Rekap" in xl.sheet_names:
                target_sheet = "Rekap"
            elif entity_type == "supplier_cabang" and "Per Cabang" in xl.sheet_names:
                target_sheet = "Per Cabang"
            df = _auto_clean_header_df(pd.read_excel(xl, sheet_name=target_sheet))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca file: {e}")

    if custom_mapping_json:
        user_map = json.loads(custom_mapping_json)
        learn_column_aliases(entity_type, user_map)

    check = inspect_and_map_columns(df, entity_type)
    if not check["valid"]:
        return {
            "status": "NEEDS_MAPPING",
            "message": f"Struktur kolom pada file '{fname}' berbeda dari standar.",
            "missing_required": check["missing_required"],
            "matched": check["matched"],
            "available_columns": check["available_columns"],
            "all_fields": check["all_fields"],
        }

    stats = sync_master_dataframe(df, entity_type, check["matched"], user_email=x_user_email)
    return {
        "status": "SUCCESS",
        "message": f"Berhasil menyinkronkan master data: +{stats['added']} data baru ditambahkan (Total: {stats['total']}).",
        "stats": stats,
    }


@app.post("/api/master/{entity_type}/row")
def api_save_row(
    entity_type: str,
    payload: dict,
    mode: str = "add",
    current_user: dict = Depends(require_current_user),
):
    x_user_email = current_user["email"]
    if entity_type not in MASTER_SCHEMAS:
        raise HTTPException(status_code=404, detail="Kategori Master tidak dikenal.")
    admin_flag = is_admin(x_user_email)
    if mode == "edit" and not admin_flag:
        raise HTTPException(status_code=403, detail="Hanya Admin yang diizinkan mengedit.")
    try:
        upsert_master_row(entity_type, payload, x_user_email, allow_overwrite=(mode == "edit" and admin_flag))
        return {"status": "SUCCESS", "message": "Data master berhasil disimpan."}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/master/{entity_type}/row/{pk_val:path}")
def api_delete_row(
    entity_type: str,
    pk_val: str,
    current_user: dict = Depends(require_current_user),
):
    if not is_admin(current_user["email"]):
        raise HTTPException(status_code=403, detail="Hanya Admin yang diizinkan menghapus.")
    delete_master_row(entity_type, pk_val)
    return {"status": "SUCCESS", "message": f"Data '{pk_val}' berhasil dihapus."}


@app.delete("/api/master/{entity_type}/clear")
def api_clear_table(
    entity_type: str,
    current_user: dict = Depends(require_current_user),
):
    if not is_admin(current_user["email"]):
        raise HTTPException(status_code=403, detail="Hanya Admin yang diizinkan mengosongkan tabel.")
    clear_master_table(entity_type)
    return {"status": "SUCCESS", "message": "Tabel berhasil dikosongkan."}


_LEFTOVER_TMP = []


def _sweep_tmp():
    for p in list(_LEFTOVER_TMP):
        shutil.rmtree(p, ignore_errors=True)
        if not os.path.exists(p):
            _LEFTOVER_TMP.remove(p)


atexit.register(_sweep_tmp)
for _old in glob.glob(os.path.join(tempfile.gettempdir(), "bbi_*")):
    shutil.rmtree(_old, ignore_errors=True)


@contextlib.contextmanager
def _safe_tmp():
    _sweep_tmp()
    tmp = tempfile.mkdtemp(prefix="bbi_")
    try:
        yield tmp
    finally:
        gc.collect()
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.exists(tmp):
            _LEFTOVER_TMP.append(tmp)


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _stage_files(kind: str, files: dict):
    pend = APP_STATE.setdefault("pending_files", {})
    for k in [k for k, v in pend.items() if v["kind"] == kind]:
        del pend[k]
    for name, data in files.items():
        pend[name] = {"kind": kind, "data": data}


def _save_upload_list(upload_list: Optional[List[UploadFile]], tmp_dir: str, prefix: str = "") -> List[str]:
    saved = []
    for u in upload_list or []:
        if not u or not u.filename or u.filename.startswith("~$"):
            continue
        p = os.path.join(tmp_dir, prefix + u.filename)
        with open(p, "wb") as o:
            o.write(u.file.read())
        pastikan_xlsx(p)
        saved.append(p)
    return saved


@app.post("/api/automate/rangkuman-penjualan")
def api_run_rangkuman_penjualan(
    files: List[UploadFile] = File(...),
    files_bulan_lalu: Optional[List[UploadFile]] = File(None),
    files_tahun_lalu: Optional[List[UploadFile]] = File(None),
    use_master_supplier: bool = Form(False),
    current_user: dict = Depends(require_current_user),
):
    x_user_email = current_user["email"]
    try:
        with _safe_tmp() as tmp:
            paths = _save_upload_list(files, tmp)
            bl_paths = _save_upload_list(files_bulan_lalu, tmp, "bl_")
            tl_paths = _save_upload_list(files_tahun_lalu, tmp, "tl_")

            jenis = {p: rk.deteksi_file(p) for p in paths}
            sups_uploaded = [p for p, j in jenis.items() if j == "SUPPLIER"]
            data_files = [p for p, j in jenis.items() if j in ("ORLAN", "ZETA")]

            if sups_uploaded:
                sup_path = sups_uploaded[0]
                try:
                    with pd.ExcelFile(io.BytesIO(_read_bytes(sup_path))) as xl_sup:
                        if "Rekap" in xl_sup.sheet_names and "Per Cabang" in xl_sup.sheet_names:
                            sync_two_sheet_supplier_excel(xl_sup, user_email=x_user_email)
                except Exception:
                    pass
                supplier_source_msg = f"File Upload ({os.path.basename(sup_path)}) + Auto-Update Master DB"
            elif use_master_supplier:
                sup_path = generate_temp_supplier_xlsx(tmp)
                supplier_source_msg = "Database Master Supplier (Rekap & Per Cabang)"
            else:
                raise HTTPException(
                    status_code=400,
                    detail="File `Supplier.xlsx` belum ikut di-upload. Silakan upload `Supplier.xlsx` bersama file penjualan, atau aktifkan opsi 'Gunakan Supplier dari Master Data'.",
                )

            if not data_files:
                raise HTTPException(status_code=400, detail="Tidak ada file penjualan Orlan atau Zeta yang dikenali.")

            r78 = rk.run_sel7_and_sel8(
                supplier_path=sup_path,
                data_files=sorted(data_files),
                files_bulan_lalu=bl_paths,
                files_tahun_lalu=tl_paths,
            )
            r9 = rk.run_sel9_zip_reports(
                MASTER=r78["MASTER"],
                HASIL=r78["HASIL"],
                PEMB=r78["PEMB"],
                output_dir=os.path.join(tmp, "out"),
            )
            _stage_files("rk", {os.path.basename(z): _read_bytes(z) for z in r9["zip_files"]})

            APP_STATE["rk_state"] = {
                "MASTER": r78["MASTER"],
                "HASIL": r78["HASIL"],
                "PEMB": r78["PEMB"],
            }
            frames = []
            cols = ["Sumber", "Cabang", "Tanggal", "NoFaktur", "KodeCust", "Customer", "Salesman", "Principal", "Jenis", "Net"]
            for h in r78["HASIL"].values():
                harvest_from_sales_df(h["df"], user_email=x_user_email)
                d_clean = h["df"][h["df"]["DipakaiLaporan"]].copy()
                frames.append(d_clean[cols].astype({"Sumber": "category", "Cabang": "category"}))
            if frames:
                df_auto = pd.concat(frames, ignore_index=True)
                df_auto["Tanggal"] = df_auto["Tanggal"].dt.normalize()
                APP_STATE["sales_dash_auto_df"] = df_auto
                APP_STATE["sales_dash_df"] = df_auto

            reports_out = []
            for rep in r78["per_file_reports"]:
                reports_out.append({
                    "file": rep["file"],
                    "sumber": rep["sumber"],
                    "periode": rep["periode"],
                    "ringkas": json.loads(rep["ringkas_df"].to_json(orient="records")),
                    "log": json.loads(rep["log_df"].to_json(orient="records")),
                })

            zip_names = [os.path.basename(z) for z in r9["zip_files"]]
            return {
                "status": "SUCCESS",
                "message": f"Selesai memproses {len(data_files)} file penjualan ({supplier_source_msg}). Paket ZIP siap diunduh!",
                "supplier_source": supplier_source_msg,
                "zip_files": zip_names,
                "per_file_reports": reports_out,
                "logs": r78["logs"] + "\n" + r9["logs"],
            }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/api/automate/rangkuman-gsheets")
def api_run_rangkuman_gsheets(
    paksa_summary_bulan_lama: bool = Form(False),
    current_user: dict = Depends(require_current_user),
):
    state = APP_STATE.get("rk_state")
    if not state:
        raise HTTPException(status_code=400, detail="Jalankan pembersihan Rangkuman Penjualan (Sel 5-9) terlebih dahulu.")
    try:
        creds = _load_google_creds(current_user["email"])
        with _safe_tmp() as tmp:
            res = rk.run_sel10_to_11c_gsheets_and_summary(
                MASTER=state["MASTER"],
                HASIL=state["HASIL"],
                output_dir=tmp,
                user_creds=creds,
                paksa_summary_bulan_lama=paksa_summary_bulan_lama,
            )
            sp = res.get("summary_excel_path")
            if sp and os.path.exists(sp):
                _stage_files("gs", {os.path.basename(sp): _read_bytes(sp)})
        return {
            "status": "SUCCESS",
            "message": f"Sinkronisasi ke Google Sheets Master & pembuatan Summary Target selesai (Akun: {current_user['email']})!",
            "summary_excel_name": res.get("summary_excel_name"),
            "logs": res.get("logs", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyinkronkan ke Google Sheets: {e}")


@app.post("/api/automate/doi-cabang")
def api_run_doi_cabang(
    files: List[UploadFile] = File(...),
    use_master_daftar_barang: bool = Form(False),
    cabang: str = Form(""),
    hari_kerja: int = Form(26),
    standar_doi_default: int = Form(30),
    ambang_ams_min: float = Form(0.0),
    bulan_stok_masuk_ams: str = Form("auto"),
    maks_bulan_ams: int = Form(0),
    current_user: dict = Depends(require_current_user),
):
    x_user_email = current_user["email"]
    try:
        with _safe_tmp() as tmp:
            paths = _save_upload_list(files, tmp)
            jenis_map = {p: deteksi_jenis_doi(p) for p in paths}
            f_daftar = [p for p, j in jenis_map.items() if j == "daftar"]
            f_mut = [p for p, j in jenis_map.items() if j == "mutasi"]
            f_jual = [p for p, j in jenis_map.items() if j == "penjualan"]

            if f_daftar:
                try:
                    df_d = pd.read_excel(f_daftar[0])
                    sync_master_dataframe(
                        df_d,
                        "product",
                        {"sku_code": "Kode", "sku_name": "Nama", "satuan": "Sat", "konversi": "Konversi", "grup": "Group", "divisi": "Divisi"},
                        user_email=x_user_email,
                    )
                except Exception:
                    pass
            elif use_master_daftar_barang:
                gen_daftar = generate_temp_daftar_barang_xlsx(tmp)
                paths.append(gen_daftar)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="File `Daftar Barang` belum ditemukan di upload. Silakan upload file Daftar Barang atau aktifkan opsi 'Gunakan Daftar Barang dari Master Data'.",
                )

            if len(f_mut) != 1:
                raise HTTPException(status_code=400, detail=f"Harus ada tepat 1 file Laporan Mutasi Stok (terdeteksi: {len(f_mut)}).")
            if len(f_jual) < 1:
                raise HTTPException(status_code=400, detail="Minimal harus ada 1 file Laporan Penjualan.")

            res = run_doi_pipeline(
                file_paths=paths,
                output_dir=os.path.join(tmp, "out"),
                CABANG=cabang.strip(),
                HARI_KERJA=int(hari_kerja),
                MAKS_BULAN_AMS=(int(maks_bulan_ams) if int(maks_bulan_ams) > 0 else None),
                AMBANG_AMS_MIN=float(ambang_ams_min),
                STANDAR_DOI_DEFAULT=int(standar_doi_default),
                BULAN_STOK_MASUK_AMS=bulan_stok_masuk_ams,
            )

            with open(res["out_path"], "rb") as fp:
                excel_bytes = fp.read()
            APP_STATE["doi_last_excel"] = (res["out_name"], excel_bytes)
            _stage_files("doi", {res["out_name"]: excel_bytes})
            try:
                parsed = ddata.baca_laporan_doi(io.BytesIO(excel_bytes), res["out_name"])
                APP_STATE["doi_dash_list"] = [parsed]
                APP_STATE["doi_dash_cleared"] = False
            except Exception:
                pass

            rk_df = res["summary_df"].reset_index().rename(columns={"index": "Principal", "prin": "Principal"})
            rk_records = json.loads(rk_df.to_json(orient="records"))

            return {
                "status": "SUCCESS",
                "message": f"Laporan DOI Cabang {res['cabang']} selesai dibuat!",
                "out_name": res["out_name"],
                "cabang": res["cabang"],
                "ams_months": res["ams_months"],
                "sku_count": res["sku_count"],
                "oms_mode": res["oms_mode"],
                "peringatan": res["peringatan"],
                "summary_rows": rk_records,
                "logs": res["logs"],
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboard/penjualan/upload")
def api_upload_sales_dashboard(
    files: List[UploadFile] = File(...),
    use_master_supplier: bool = Form(True),
    current_user: dict = Depends(require_current_user),
):
    x_user_email = current_user["email"]
    try:
        with _safe_tmp() as tmp:
            paths = _save_upload_list(files, tmp)
            jenis = {p: rk.deteksi_file(p) for p in paths}
            has_sup = any(j == "SUPPLIER" for j in jenis.values())
            if not has_sup and use_master_supplier:
                try:
                    sup_tmp = generate_temp_supplier_xlsx(tmp)
                    paths.append(sup_tmp)
                except Exception:
                    pass
            df = pdata.muat_data(paths)
            APP_STATE["sales_dash_df"] = df
            APP_STATE["sales_dash_cleared"] = False
            harvest_warning = None
            try:
                harvest_from_sales_df(df, user_email=x_user_email)
            except Exception as e:
                harvest_warning = str(e)
        dashboard = api_get_sales_dashboard()
        if harvest_warning:
            dashboard["master_sync_warning"] = harvest_warning
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal memuat data Dashboard Penjualan: {e}")


@app.get("/api/dashboard/penjualan/data")
def api_get_sales_dashboard(cabang: Optional[str] = None, sumber: Optional[str] = None):
    df = APP_STATE.get("sales_dash_df")
    if df is None or df.empty:
        return {"ready": False}

    all_cab = sorted(df["Cabang"].astype(str).unique())
    all_src = sorted(df["Sumber"].astype(str).unique())
    sel_cab = [c for c in (cabang.split(",") if cabang else all_cab) if c in all_cab] or all_cab
    sel_src = [s for s in (sumber.split(",") if sumber else all_src) if s in all_src] or all_src

    d = df[df["Cabang"].astype(str).isin(sel_cab) & df["Sumber"].astype(str).isin(sel_src)]
    if d.empty:
        return {"ready": True, "empty_filter": True, "all_cabang": all_cab, "all_sumber": all_src}

    k = pdata.ringkas(d)
    fx = pdata.prakiraan(d)
    F = pvis.figur(d, k, fx)
    ins = pdata.insight(d, k, fx)

    charts_json = {key: json.loads(fig.to_json()) for key, fig in F.items()}
    return {
        "ready": True,
        "all_cabang": all_cab,
        "all_sumber": all_src,
        "selected_cabang": sel_cab,
        "selected_sumber": sel_src,
        "kpi": {
            "omset": fmt_rp(k["omset"]),
            "faktur": f"{k['faktur']:,}",
            "periode": f"{k['awal']:%d %b} – {k['akhir']:%d %b %Y}",
            "outlet": f"{k['outlet']:,}",
            "rata": fmt_rp(k["rata"]),
            "hari": k["hari"],
            "retur_pct": f"{k['retur_pct']:.2f}%",
            "delta": f"{k['delta']:+.1f}%" if k["delta"] is not None else None,
            "delta_pos": bool(k["delta"] is not None and k["delta"] >= 0),
            "d7_vs_p7": f"{fmt_rp(k['d7'])} vs {fmt_rp(k['p7'])}" if k["delta"] is not None else "Data pembanding belum lengkap",
            "forecast_30d": fmt_rp(fx["fc"]["yhat"].sum()) if fx else "-",
            "forecast_range": f"{fmt_rp(fx['fc']['lo'].sum())} – {fmt_rp(fx['fc']['hi'].sum())}" if fx else "",
        },
        "warnings": [
            f"Data tidak lengkap: {n} hari kerja ({a:%d %b} – {b:%d %b}) omsetnya sangat kecil."
            for a, b, n in k["kosong"]
        ],
        "insights": ins,
        "charts": charts_json,
    }


@app.delete("/api/dashboard/penjualan/data")
def api_clear_sales_dashboard():
    APP_STATE["sales_dash_df"] = None
    APP_STATE["sales_dash_cleared"] = True
    return {"ready": False, "can_restore": APP_STATE.get("sales_dash_auto_df") is not None}


@app.post("/api/dashboard/penjualan/restore")
def api_restore_sales_dashboard():
    APP_STATE["sales_dash_df"] = APP_STATE.get("sales_dash_auto_df")
    APP_STATE["sales_dash_cleared"] = False
    return api_get_sales_dashboard()


@app.get("/api/dashboard/penjualan/export", response_class=HTMLResponse)
def api_export_sales_dashboard(cabang: Optional[str] = None, sumber: Optional[str] = None):
    df = APP_STATE.get("sales_dash_df")
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Data Dashboard Penjualan belum tersedia.")
    all_cab = sorted(df["Cabang"].astype(str).unique())
    all_src = sorted(df["Sumber"].astype(str).unique())
    sel_cab = [c for c in (cabang.split(",") if cabang else all_cab) if c in all_cab] or all_cab
    sel_src = [s for s in (sumber.split(",") if sumber else all_src) if s in all_src] or all_src
    filtered = df[df["Cabang"].astype(str).isin(sel_cab) & df["Sumber"].astype(str).isin(sel_src)]
    if filtered.empty:
        raise HTTPException(status_code=400, detail="Filter tidak menghasilkan data.")
    k = pdata.ringkas(filtered)
    fx = pdata.prakiraan(filtered)
    figures = pvis.figur(filtered, k, fx)
    insights = pdata.insight(filtered, k, fx)
    return HTMLResponse(pvis.html_dashboard(filtered, k, fx, figures, insights))


@app.post("/api/dashboard/doi/upload")
async def api_upload_doi_dashboard(files: List[UploadFile] = File(...)):
    hasil = []
    for f in files:
        content = await f.read()
        try:
            hasil.append(ddata.baca_laporan_doi(io.BytesIO(content), f.filename))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal membaca {f.filename}: {e}")
    if not hasil:
        raise HTTPException(status_code=400, detail="Tidak ada file Laporan_DOI_*.xlsx yang valid.")
    APP_STATE["doi_dash_list"] = hasil
    APP_STATE["doi_dash_cleared"] = False
    return api_get_doi_dashboard()


@app.delete("/api/dashboard/doi/data")
def api_clear_doi_dashboard():
    APP_STATE["doi_dash_list"] = []
    APP_STATE["doi_dash_cleared"] = True
    return {"ready": False, "can_restore": APP_STATE.get("doi_last_excel") is not None}


@app.post("/api/dashboard/doi/restore")
def api_restore_doi_dashboard():
    APP_STATE["doi_dash_list"] = []
    APP_STATE["doi_dash_cleared"] = False
    return api_get_doi_dashboard()


@app.get("/api/dashboard/doi/data")
def api_get_doi_dashboard(
    cabang: Optional[str] = None,
    principal: Optional[str] = None,
    status: Optional[str] = None,
    cari: Optional[str] = None,
    per_cabang: bool = False,
    sort_by: str = "lebih_kurang",
    sort_desc: bool = True,
):
    hasil = APP_STATE.get("doi_dash_list") or []
    if not hasil and not APP_STATE.get("doi_dash_cleared") and APP_STATE.get("doi_last_excel"):
        nm, bts = APP_STATE["doi_last_excel"]
        hasil = [ddata.baca_laporan_doi(io.BytesIO(bts), nm)]
        APP_STATE["doi_dash_list"] = hasil

    if not hasil:
        return {"ready": False}

    data = ddata.gabung([dict(h, param=dict(h["param"])) for h in hasil])
    sku_all, bln_all, gud_all, params = data["sku"], data["bulanan"], data["gudang"], data["param"]
    hk = float(np.mean([p["hari_kerja"] for p in params]))

    all_cab = sorted(sku_all["cabang"].unique())
    all_principal = sorted(sku_all["principal"].dropna().astype(str).unique())
    all_status = [s for s in dvis.STATUS_URUT if s in set(sku_all["status"])]
    sel_cab = [c for c in (cabang.split(",") if cabang else all_cab) if c in all_cab] or all_cab
    sel_principal = [p for p in (principal.split(",") if principal else all_principal) if p in all_principal] or all_principal
    sel_status = [s for s in (status.split(",") if status else all_status) if s in all_status] or all_status

    f = sku_all[
        sku_all["cabang"].isin(sel_cab)
        & sku_all["principal"].astype(str).isin(sel_principal)
    ].copy()
    if f.empty:
        return {
            "ready": True,
            "empty_filter": True,
            "all_cabang": all_cab,
            "all_principal": all_principal,
            "all_status": all_status,
        }

    f["label"] = (f["cabang"] + " · " + f["principal"]) if (per_cabang and len(all_cab) > 1) else f["principal"]
    fs = f[f["status"].isin(sel_status)].copy()
    if cari and cari.strip():
        q = cari.strip().lower()
        fs = fs[
            fs["nama"].astype(str).str.lower().str.contains(q, regex=False, na=False)
            | fs["kode"].astype(str).str.lower().str.contains(q, regex=False, na=False)
        ]
    fs["label"] = (fs["cabang"] + " · " + fs["principal"]) if (per_cabang and len(all_cab) > 1) else fs["principal"]
    bln = bln_all[bln_all["cabang"].isin(sel_cab)]
    bln = bln[bln["principal"].astype(str).isin(sel_principal)]
    gud = gud_all[gud_all["cabang"].isin(sel_cab)]

    by = ["cabang", "principal"] if (per_cabang and len(all_cab) > 1) else ["principal"]
    rk_df = ddata.ringkas(f, hk, by=by)
    rk_df["label"] = (rk_df["cabang"] + " · " + rk_df["principal"]) if (per_cabang and len(all_cab) > 1) else rk_df["principal"]
    K = ddata.kpi(f, hk)
    ins = ddata.insight(f, rk_df, bln, gud, hk)

    F = {
        "doi_std": dvis.fig_doi_std(rk_df),
        "lebih_kurang": dvis.fig_lebih_kurang(rk_df),
        "porsi": dvis.fig_porsi(rk_df),
        "bucket": dvis.fig_bucket(f, "label"),
        "top_lebih": dvis.fig_top_lebih(fs),
        "top_kritis": dvis.fig_top_kritis(fs),
        "tren": dvis.fig_tren(bln),
        "gudang": dvis.fig_gudang(gud),
    }
    F["scatter"], _ = (None, 0) if fs.empty else dvis.fig_scatter(fs, hk)
    charts_json = {k: (json.loads(v.to_json()) if v is not None else None) for k, v in F.items()}

    sort_col = sort_by if sort_by in {"saldo", "ams", "doi", "lebih_kurang", "nama"} else "lebih_kurang"
    t = fs.sort_values(sort_col, ascending=not sort_desc, na_position="last").head(1000)
    sku_rows = [
        {
            "cabang": str(r["cabang"]),
            "principal": str(r["principal"]),
            "kode": str(r["kode"]),
            "nama": str(r["nama"]),
            "stok": f"{r['stok']:,.1f}",
            "sat": str(r["sat"]),
            "saldo": fmt_rp(r["saldo"]),
            "ams": fmt_rp(r["ams"]),
            "doi": f"{r['doi']:,.1f}" if pd.notna(r["doi"]) else "-",
            "std": f"{r['std']:,.0f}",
            "lebih_kurang": fmt_rp(r["lebih_kurang"]),
            "status": str(r["status"]),
        }
        for _, r in t.iterrows()
    ]
    stock_dates = sorted({p["tanggal"] for p in params if pd.notna(p["tanggal"])})
    month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    latest_stock_date = stock_dates[-1] if len(stock_dates) == 1 else None
    stock_date = f"{latest_stock_date.day:02d} {month_names[latest_stock_date.month - 1]} {latest_stock_date.year}" if latest_stock_date is not None else "tanggal tiap laporan"
    ams_months = {p["n_bulan"] for p in params}
    ams_period = f"Rata-rata {next(iter(ams_months))} bulan" if len(ams_months) == 1 else "Rata-rata omset bulanan"
    weighted_standard = float((f["std"] * f["ams"]).sum() / f["ams"].sum()) if f["ams"].sum() > 0 else np.nan

    return {
        "ready": True,
        "all_cabang": all_cab,
        "all_principal": all_principal,
        "all_status": all_status,
        "selected_cabang": sel_cab,
        "selected_principal": sel_principal,
        "selected_status": sel_status,
        "selected_per_cabang": per_cabang,
        "selected_cari": cari or "",
        "selected_sort_by": sort_col,
        "selected_sort_desc": sort_desc,
        "kpi": {
            "saldo": fmt_rp(K["saldo"]),
            "ams": fmt_rp(K["ams"]),
            "ams_period": ams_period,
            "doi": f"{K['doi']:,.1f} hari" if pd.notna(K["doi"]) else "-",
            "std_doi": f"Standar tertimbang {weighted_standard:,.1f} hari" if pd.notna(weighted_standard) else "",
            "stock_date": stock_date,
            "n_sku": fmt_num(K["n_sku"]),
            "kelebihan": fmt_rp(K["kelebihan"]),
            "kekurangan": fmt_rp(abs(K["kekurangan"])),
            "kritis_kosong": fmt_num(K["n_kritis"] + K["n_kosong"]),
            "ams_terancam": fmt_rp(K["ams_kosong"]),
            "n_mati": fmt_num(K["n_mati"]),
            "n_tanpa_harga": fmt_num(K["n_tanpa_harga"]),
        },
        "insights": [re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", x) for x in ins],
        "charts": charts_json,
        "sku_table": sku_rows,
        "sku_total": int(len(fs)),
    }


@app.get("/api/dashboard/doi/export.csv")
def api_export_doi_csv(
    cabang: Optional[str] = None,
    principal: Optional[str] = None,
    status: Optional[str] = None,
    cari: Optional[str] = None,
    sort_by: str = "lebih_kurang",
    sort_desc: bool = True,
):
    hasil = APP_STATE.get("doi_dash_list") or []
    if not hasil and not APP_STATE.get("doi_dash_cleared") and APP_STATE.get("doi_last_excel"):
        nm, bts = APP_STATE["doi_last_excel"]
        hasil = [ddata.baca_laporan_doi(io.BytesIO(bts), nm)]
    if not hasil:
        raise HTTPException(status_code=404, detail="Data Dashboard DOI belum tersedia.")

    sku = ddata.gabung([dict(h, param=dict(h["param"])) for h in hasil])["sku"]
    all_cab = sorted(sku["cabang"].unique())
    all_principal = sorted(sku["principal"].dropna().astype(str).unique())
    all_status = [s for s in dvis.STATUS_URUT if s in set(sku["status"])]
    sel_cab = [c for c in (cabang.split(",") if cabang else all_cab) if c in all_cab] or all_cab
    sel_principal = [p for p in (principal.split(",") if principal else all_principal) if p in all_principal] or all_principal
    sel_status = [s for s in (status.split(",") if status else all_status) if s in all_status] or all_status
    filtered = sku[
        sku["cabang"].isin(sel_cab)
        & sku["principal"].astype(str).isin(sel_principal)
        & sku["status"].isin(sel_status)
    ].copy()
    if cari and cari.strip():
        q = cari.strip().lower()
        filtered = filtered[
            filtered["nama"].astype(str).str.lower().str.contains(q, regex=False, na=False)
            | filtered["kode"].astype(str).str.lower().str.contains(q, regex=False, na=False)
        ]
    if filtered.empty:
        raise HTTPException(status_code=400, detail="Filter tidak menghasilkan baris SKU.")

    sort_col = sort_by if sort_by in {"saldo", "ams", "doi", "lebih_kurang", "nama"} else "lebih_kurang"
    filtered = filtered.sort_values(sort_col, ascending=not sort_desc, na_position="last")
    columns = ["cabang", "principal", "kode", "nama", "stok", "sat", "harga", "saldo", "ams", "doi", "std", "lebih_kurang", "status", "tanpa_harga"]
    csv_data = filtered[columns].to_csv(index=False).encode("utf-8-sig")
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sku_doi.csv"'},
    )


@app.get("/api/download/output/{filename}")
def api_download_output(filename: str):
    filename = os.path.basename(filename)
    fpath = os.path.join(OUTPUT_DIR, filename)
    pend = APP_STATE.get("pending_files", {})
    if filename in pend:
        part = fpath + ".part"
        with open(part, "wb") as fh:
            fh.write(pend[filename]["data"])
        os.replace(part, fpath)
        del pend[filename]
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="File output tidak ditemukan.")
    return FileResponse(fpath, filename=filename)


@app.get("/legacy", response_class=HTMLResponse, include_in_schema=False)
def serve_legacy_frontend():
    """UI lama (frontend/index.html) tetap bisa dibuka di /legacy selama halaman React belum selesai dipindahkan."""
    legacy = os.path.abspath(os.path.join(ROOT_DIR, "frontend", "index.html"))
    if os.path.exists(legacy):
        return FileResponse(legacy, headers=NO_CACHE)
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """Alamat halaman React (mis. /automation/doi) selalu membuka index.html; file statis (logo, dll) dilayani langsung."""
    if full_path.startswith(("api/", "auth/")):
        raise HTTPException(status_code=404, detail="Not found")
    react_index = os.path.join(REACT_DIST, "index.html")
    if not os.path.exists(react_index):
        raise HTTPException(status_code=404, detail="Not found")
    cand = os.path.abspath(os.path.join(REACT_DIST, full_path))
    if cand.startswith(REACT_DIST + os.sep) and os.path.isfile(cand):
        return FileResponse(cand)
    return FileResponse(react_index, headers=NO_CACHE)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)