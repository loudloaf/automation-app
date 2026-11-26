# backend/database.py
"""FastAPI Database Layer: SQLite WAL Mode, Multi-Sheet Supplier, Auto-Harvesting, & Zero-Touch Script Adapters."""
import os
import datetime as dt
import secrets
import sqlite3
import pandas as pd
from openpyxl import Workbook

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data"))
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "automation_hub.db")
OWNER_EMAIL = "stanleytan990@gmail.com"  # Owner: selalu admin penuh, tidak bisa diturunkan atau dibuang oleh admin lain

NICKNAME = {
    "MBI": "Bintang", "IBN": "Mayora", "FFI": "Susu Bendera", "BWI": "Pronas", "ABC": "Nu Green Tea",
    "SATP": "Sovia", "BDY": "Bandulan", "OWI": "Oasis", "UCI": "Unicharm", "MTI": "Motasa",
    "SLM": "Garam", "EPM": "Sun Kara", "SWT": "Pristine", "KMI": "Zoda", "KDM": "Camel",
    "CCOD": "Coca-Cola", "FRI": "Fokus Ritel", "AKD": "Kin", "KINO": "Kino", "MALEE": "Malee",
    "LBP": "Wangs", "CBN": "Umma", "SLN": "AMDK",
}

MASTER_SCHEMAS = {
    "supplier_rekap": {
        "title": "Supplier · Sheet Rekap",
        "table": "master_supplier_rekap",
        "pk": "row_key",
        "key_fields": ["kode_supp", "kode_grup"],
        "fields": {
            "kode_supp": {"label": "Kode Supplier (Kode)", "required": True, "default_aliases": ["kode", "kodesupp", "kode supplier", "supp id", "suppid"]},
            "supp": {"label": "Singkatan (Supp)", "required": True, "default_aliases": ["supp", "supplier", "principal", "singkatan"]},
            "kode_grup": {"label": "Kode Grup Barang", "required": True, "default_aliases": ["kode grup barang", "kodegrup", "kode group", "kode grup", "group id"]},
            "nama_grup": {"label": "Nama Grup Barang", "required": True, "default_aliases": ["nama grup barang", "namagrup", "nama group", "nama grup", "grup barang"]},
            "label_principal": {"label": "Label Principal (Laporan)", "required": False, "default_aliases": ["label", "label principal", "nama principal"]},
        },
    },
    "supplier_cabang": {
        "title": "Supplier · Sheet Per Cabang (Zeta)",
        "table": "master_supplier_cabang",
        "pk": "row_key",
        "key_fields": ["cabang", "kode_grup", "kode_supp"],
        "fields": {
            "cabang": {"label": "Cabang", "required": True, "default_aliases": ["cabang", "branch", "depo", "wilayah"]},
            "kode_grup": {"label": "Kode Grup Barang", "required": True, "default_aliases": ["kode grup barang", "kodegrup", "kode group", "kode grup"]},
            "nama_grup": {"label": "Nama Grup Barang", "required": True, "default_aliases": ["nama grup barang", "namagrup", "nama group", "nama grup"]},
            "kode_supp": {"label": "Kode Supplier (Kode)", "required": True, "default_aliases": ["kode", "kodesupp", "kode supplier", "supp id"]},
            "supp": {"label": "Singkatan (Supp)", "required": True, "default_aliases": ["supp", "supplier", "principal", "singkatan"]},
        },
    },
    "customer": {
        "title": "Master Customer / Outlet",
        "table": "master_customers",
        "pk": "customer_code",
        "key_fields": ["customer_code"],
        "fields": {
            "customer_code": {"label": "Kode Customer", "required": True, "default_aliases": ["kodecust", "kode customer", "kode pelanggan", "cust id", "no cust", "outlet id"]},
            "customer_name": {"label": "Nama Customer / Outlet", "required": True, "default_aliases": ["customer", "nama customer", "nama pelanggan", "outlet", "nama toko", "custname"]},
            "cabang": {"label": "Cabang", "required": False, "default_aliases": ["cabang", "branch", "depo", "area", "entityid_"]},
            "alamat": {"label": "Alamat", "required": False, "default_aliases": ["alamat", "address", "address 1", "lokasi"]},
        },
    },
    "product": {
        "title": "Master Produk / Daftar Barang (SKU)",
        "table": "master_products",
        "pk": "sku_code",
        "key_fields": ["sku_code"],
        "fields": {
            "sku_code": {"label": "Kode Barang (Kode)", "required": True, "default_aliases": ["kode", "kode barang", "sku", "itemid", "item code", "kd_brg"]},
            "sku_name": {"label": "Nama Barang (Nama)", "required": True, "default_aliases": ["nama", "nama barang", "itemdesc", "deskripsi", "item name", "produk"]},
            "satuan": {"label": "Satuan Besar (Sat)", "required": False, "default_aliases": ["sat", "satuan", "satuan besar", "unitid", "uom"]},
            "konversi": {"label": "Konversi", "required": False, "default_aliases": ["konversi", "isi", "conv"]},
            "grup": {"label": "Group", "required": False, "default_aliases": ["group", "grup", "namagrup", "itemgroupdesc", "nama grup barang"]},
            "divisi": {"label": "Divisi", "required": False, "default_aliases": ["divisi", "div", "division", "principal"]},
        },
    },
    "warehouse": {
        "title": "Master Gudang (DOI)",
        "table": "master_warehouses",
        "pk": "warehouse_code",
        "key_fields": ["warehouse_code"],
        "fields": {
            "warehouse_code": {"label": "Kode Gudang", "required": True, "default_aliases": ["gudang", "kode gudang", "wh", "warehouse", "lokasi", "gud"]},
            "keterangan": {"label": "Nama / Keterangan Gudang", "required": False, "default_aliases": ["keterangan", "nama gudang", "deskripsi gudang", "locationdesc"]},
            "cabang": {"label": "Cabang", "required": False, "default_aliases": ["cabang", "branch", "depo"]},
            "dihitung_doi": {"label": "Dihitung di DOI (Ya/Tidak)", "required": False, "default_aliases": ["dihitung", "hitung doi", "aktif", "status"]},
        },
    },
    "branch": {
        "title": "Master Cabang",
        "table": "master_branches",
        "pk": "branch_code",
        "key_fields": ["branch_code"],
        "fields": {
            "branch_code": {"label": "Kode / Nama Cabang", "required": True, "default_aliases": ["cabang", "kode cabang", "branch", "depo"]},
            "branch_name": {"label": "Nama Lengkap Cabang", "required": True, "default_aliases": ["nama cabang", "branch name", "wilayah", "cabang"]},
            "region": {"label": "Sistem / Region", "required": False, "default_aliases": ["region", "area", "zona", "sistem", "sumber"]},
        },
    },
}


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _norm(text: str) -> str:
    return "".join(ch for ch in str(text).lower().strip() if ch.isalnum() or ch == " ").strip()


def _clean_cell(val) -> str:
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def make_principal_label(supp: str, fallback_group: str = "") -> str:
    s = str(supp).strip()
    if not s:
        return ""
    nick = NICKNAME.get(s.upper(), str(fallback_group or s).title())
    return f"{s} ({nick})"


def init_db():
    now = dt.datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.executescript("""
        -- Drop legacy single-sheet supplier table if it exists
        DROP TABLE IF EXISTS master_suppliers;

        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT,
            role TEXT DEFAULT 'staff',
            last_login TEXT,
            picture TEXT DEFAULT '',
            google_token BLOB
        );

        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schema_aliases (
            entity_type TEXT NOT NULL,
            standard_field TEXT NOT NULL,
            alias_name TEXT NOT NULL,
            PRIMARY KEY (entity_type, standard_field, alias_name)
        );

        CREATE TABLE IF NOT EXISTS master_supplier_rekap (
            row_key TEXT PRIMARY KEY,
            kode_supp TEXT NOT NULL,
            supp TEXT NOT NULL,
            kode_grup TEXT NOT NULL,
            nama_grup TEXT NOT NULL,
            label_principal TEXT DEFAULT '',
            updated_at TEXT,
            updated_by TEXT
        );

        CREATE TABLE IF NOT EXISTS master_supplier_cabang (
            row_key TEXT PRIMARY KEY,
            cabang TEXT NOT NULL,
            kode_grup TEXT NOT NULL,
            nama_grup TEXT NOT NULL,
            kode_supp TEXT NOT NULL,
            supp TEXT NOT NULL,
            updated_at TEXT,
            updated_by TEXT
        );

        CREATE TABLE IF NOT EXISTS master_customers (
            customer_code TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            cabang TEXT DEFAULT '',
            alamat TEXT DEFAULT '',
            updated_at TEXT,
            updated_by TEXT
        );

        CREATE TABLE IF NOT EXISTS master_products (
            sku_code TEXT PRIMARY KEY,
            sku_name TEXT NOT NULL,
            satuan TEXT DEFAULT 'CTN',
            konversi REAL DEFAULT 1.0,
            grup TEXT DEFAULT '',
            divisi TEXT DEFAULT '',
            updated_at TEXT,
            updated_by TEXT
        );

        CREATE TABLE IF NOT EXISTS master_warehouses (
            warehouse_code TEXT PRIMARY KEY,
            keterangan TEXT DEFAULT '',
            cabang TEXT DEFAULT '',
            dihitung_doi TEXT DEFAULT 'Ya',
            updated_at TEXT,
            updated_by TEXT
        );

        CREATE TABLE IF NOT EXISTS master_branches (
            branch_code TEXT PRIMARY KEY,
            branch_name TEXT NOT NULL,
            region TEXT DEFAULT '',
            updated_at TEXT,
            updated_by TEXT
        );
        """)

        # Migrate master_products columns safely if table already existed from earlier test
        existing_prod_cols = {r["name"] for r in conn.execute("PRAGMA table_info(master_products)").fetchall()}
        if "grup" not in existing_prod_cols:
            conn.execute("ALTER TABLE master_products ADD COLUMN grup TEXT DEFAULT ''")
        if "divisi" not in existing_prod_cols:
            conn.execute("ALTER TABLE master_products ADD COLUMN divisi TEXT DEFAULT ''")

        existing_user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "picture" not in existing_user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN picture TEXT DEFAULT ''")
        if "google_token" not in existing_user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN google_token BLOB")

        conn.execute(
            "INSERT OR IGNORE INTO users (email, name, role, last_login) VALUES (?, ?, 'admin', ?)",
            ("admin@company.com", "Super Admin", now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO users (email, name, role, last_login) VALUES (?, ?, 'admin', ?)",
            (OWNER_EMAIL, "Owner", now),
        )
        conn.execute("UPDATE users SET role='admin' WHERE LOWER(email)=LOWER(?)", (OWNER_EMAIL,))

        for ent, cfg in MASTER_SCHEMAS.items():
            for std_col, fmeta in cfg["fields"].items():
                conn.execute(
                    "INSERT OR IGNORE INTO schema_aliases VALUES (?, ?, ?)",
                    (ent, std_col, _norm(std_col)),
                )
                for al in fmeta["default_aliases"]:
                    conn.execute(
                        "INSERT OR IGNORE INTO schema_aliases VALUES (?, ?, ?)",
                        (ent, std_col, _norm(al)),
                    )


# --- PERMISSION CHECK ---
def is_admin(email: str) -> bool:
    if email.strip().lower() == OWNER_EMAIL:
        return True
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT role FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)).fetchone()
        return bool(row and row["role"] == "admin")


def list_users():
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT email, name, role, last_login, COALESCE(picture, '') AS picture, (google_token IS NOT NULL) AS has_google_token FROM users ORDER BY role, email"
        ).fetchall()
        return [dict(r) for r in rows]


def get_user(email: str):
    if not email:
        return None
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT email, name, role, last_login, COALESCE(picture, '') AS picture FROM users WHERE LOWER(email) = LOWER(?)",
            (email.strip(),),
        ).fetchone()
        return dict(row) if row else None


def record_user_login(email: str, name: str = "", picture: str = "", token_bytes: bytes = None):
    """Catat login akun Google pribadi. Otomatis mendaftarkan pengguna baru sebagai 'staff' (atau 'admin' untuk Owner)."""
    clean_email = email.strip().lower()
    if not clean_email:
        raise ValueError("Email akun Google kosong.")
    init_db()
    existing = get_user(clean_email)
    role = "admin" if clean_email == OWNER_EMAIL.lower() else (existing["role"] if existing else "staff")
    display_name = name.strip() or (existing["name"] if existing and existing.get("name") else clean_email.split("@")[0])
    pic = picture or (existing.get("picture", "") if existing else "")
    now = dt.datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        if existing:
            if token_bytes is not None:
                conn.execute(
                    "UPDATE users SET name=?, role=?, last_login=?, picture=?, google_token=? WHERE LOWER(email)=LOWER(?)",
                    (display_name, role, now, pic, token_bytes, clean_email),
                )
            else:
                conn.execute(
                    "UPDATE users SET name=?, role=?, last_login=?, picture=? WHERE LOWER(email)=LOWER(?)",
                    (display_name, role, now, pic, clean_email),
                )
        else:
            conn.execute(
                "INSERT INTO users (email, name, role, last_login, picture, google_token) VALUES (?, ?, ?, ?, ?, ?)",
                (clean_email, display_name, role, now, pic, token_bytes),
            )
    return get_user(clean_email)


def get_user_google_token(email: str) -> bytes:
    if not email:
        return None
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT google_token FROM users WHERE LOWER(email) = LOWER(?)",
            (email.strip(),),
        ).fetchone()
        return row["google_token"] if row and row["google_token"] else None


def save_user_google_token(email: str, token_bytes: bytes):
    init_db()
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET google_token = ? WHERE LOWER(email) = LOWER(?)",
            (token_bytes, email.strip()),
        )


def create_user_session(email: str, days: int = 30) -> str:
    init_db()
    sid = secrets.token_urlsafe(32)
    now = dt.datetime.now()
    exp = now + dt.timedelta(days=days)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_sessions (session_id, email, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (sid, email.strip().lower(), now.isoformat(timespec="seconds"), exp.isoformat(timespec="seconds")),
        )
    return sid


def get_session_user(session_id: str):
    if not session_id:
        return None
    init_db()
    now_iso = dt.datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT email, expires_at FROM user_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        if row["expires_at"] < now_iso:
            conn.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
            return None
        return get_user(row["email"])


def delete_user_session(session_id: str):
    if not session_id:
        return
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))


def set_user_role(target_email: str, name: str, role: str):
    if target_email.strip().lower() == OWNER_EMAIL.lower() and role != "admin":
        raise PermissionError("Akun Owner tidak dapat diturunkan dari Admin.")
    init_db()
    now = dt.datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users (email, name, role, last_login) VALUES (?, ?, ?, ?)
               ON CONFLICT(email) DO UPDATE SET name= CASE WHEN excluded.name != '' THEN excluded.name ELSE users.name END, role=excluded.role""",
            (target_email.strip().lower(), name.strip(), role, now),
        )


# --- 2-SHEET SUPPLIER.XLSX SYNC & RECONSTRUCTION FOR SCRIPTS ---
def sync_two_sheet_supplier_excel(xl: pd.ExcelFile, user_email: str = "system"):
    init_db()
    now = dt.datetime.now().isoformat(timespec="seconds")

    rekap_raw = pd.read_excel(xl, sheet_name="Rekap", header=2, dtype=str)
    if rekap_raw.shape[1] >= 5 and str(rekap_raw.columns[0]).startswith("Unnamed"):
        rekap = rekap_raw.iloc[:, 1:5].copy()
    else:
        rekap = rekap_raw.iloc[:, :4].copy()
    rekap.columns = ["KodeSupp", "Supp", "KodeGrup", "NamaGrup"]
    for c in rekap.columns:
        rekap[c] = rekap[c].map(_clean_cell)
    rekap = rekap[rekap["KodeSupp"].str.fullmatch(r"\d+")].copy()

    first_grup = rekap.drop_duplicates("KodeSupp").set_index("KodeSupp")["NamaGrup"].to_dict()

    percab_raw = pd.read_excel(xl, sheet_name="Per Cabang", header=1, dtype=str)
    percab = percab_raw.iloc[:, :5].copy()
    percab.columns = ["Cabang", "KodeGrup", "NamaGrup", "KodeSupp", "Supp"]
    for c in percab.columns:
        percab[c] = percab[c].map(_clean_cell)
    percab = percab[percab["KodeSupp"].str.fullmatch(r"\d+")].copy()

    with get_conn() as conn:
        before_rekap = conn.execute("SELECT COUNT(*) AS n FROM master_supplier_rekap").fetchone()["n"]
        before_cab = conn.execute("SELECT COUNT(*) AS n FROM master_supplier_cabang").fetchone()["n"]

        for _, r in rekap.iterrows():
            rkey = f"{r['KodeSupp']}|{r['KodeGrup']}"
            lbl = make_principal_label(r["Supp"], first_grup.get(r["KodeSupp"], r["Supp"]))
            conn.execute(
                """INSERT OR IGNORE INTO master_supplier_rekap
                   (row_key, kode_supp, supp, kode_grup, nama_grup, label_principal, updated_at, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (rkey, r["KodeSupp"], r["Supp"], r["KodeGrup"], r["NamaGrup"], lbl, now, user_email),
            )

        for _, r in percab.iterrows():
            ckey = f"{r['Cabang'].upper()}|{r['KodeGrup']}|{r['KodeSupp']}"
            conn.execute(
                """INSERT OR IGNORE INTO master_supplier_cabang
                   (row_key, cabang, kode_grup, nama_grup, kode_supp, supp, updated_at, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (ckey, r["Cabang"], r["KodeGrup"], r["NamaGrup"], r["KodeSupp"], r["Supp"], now, user_email),
            )
            if r["Cabang"]:
                conn.execute(
                    """INSERT OR IGNORE INTO master_branches (branch_code, branch_name, region, updated_at, updated_by)
                       VALUES (?, ?, 'ZETA / Per Cabang', ?, ?)""",
                    (r["Cabang"].upper(), r["Cabang"], now, user_email),
                )

        after_rekap = conn.execute("SELECT COUNT(*) AS n FROM master_supplier_rekap").fetchone()["n"]
        after_cab = conn.execute("SELECT COUNT(*) AS n FROM master_supplier_cabang").fetchone()["n"]

    return {
        "rekap_before": before_rekap,
        "rekap_added": after_rekap - before_rekap,
        "rekap_total": after_rekap,
        "cabang_before": before_cab,
        "cabang_added": after_cab - before_cab,
        "cabang_total": after_cab,
    }


def generate_temp_supplier_xlsx(target_dir: str) -> str:
    """
    Buat file Supplier.xlsx sementara di target_dir dari SQLite Master Data
    dengan posisi baris & kolom yang 100% identik dengan yang diminta scripts/rangkuman_penjualan.py:
    - Sheet 'Rekap': header di baris ke-3 (index 2), kolom B..E ('Kode', 'Supp', 'Kode Grup Barang', 'Nama Grup Barang')
    - Sheet 'Per Cabang': header di baris ke-2 (index 1), kolom A..E ('Cabang', 'Kode Grup Barang', 'Nama Grup Barang', 'Kode', 'Supp')
    """
    init_db()
    rekap_rows = get_master_rows("supplier_rekap")
    cab_rows = get_master_rows("supplier_cabang")
    if not rekap_rows:
        raise ValueError("Master Data Supplier (Sheet Rekap) masih kosong di database. Silakan upload file Supplier.xlsx terlebih dahulu.")

    wb = Workbook()
    # 1. Sheet Rekap
    ws_r = wb.active
    ws_r.title = "Rekap"
    ws_r.cell(3, 2, "Kode")
    ws_r.cell(3, 3, "Supp")
    ws_r.cell(3, 4, "Kode Grup Barang")
    ws_r.cell(3, 5, "Nama Grup Barang")
    for idx, r in enumerate(rekap_rows, start=4):
        ws_r.cell(idx, 2, str(r["kode_supp"]))
        ws_r.cell(idx, 3, str(r["supp"]))
        ws_r.cell(idx, 4, str(r["kode_grup"]))
        ws_r.cell(idx, 5, str(r["nama_grup"]))

    # 2. Sheet Per Cabang
    ws_c = wb.create_sheet("Per Cabang")
    ws_c.cell(2, 1, "Cabang")
    ws_c.cell(2, 2, "Kode Grup Barang")
    ws_c.cell(2, 3, "Nama Grup Barang")
    ws_c.cell(2, 4, "Kode")
    ws_c.cell(2, 5, "Supp")
    for idx, r in enumerate(cab_rows, start=3):
        ws_c.cell(idx, 1, str(r["cabang"]))
        ws_c.cell(idx, 2, str(r["kode_grup"]))
        ws_c.cell(idx, 3, str(r["nama_grup"]))
        ws_c.cell(idx, 4, str(r["kode_supp"]))
        ws_c.cell(idx, 5, str(r["supp"]))

    out_path = os.path.join(target_dir, "Supplier_MasterDB.xlsx")
    wb.save(out_path)
    return out_path


def generate_temp_daftar_barang_xlsx(target_dir: str) -> str:
    """
    Buat file Daftar_Barang.xlsx sementara di target_dir dari tabel master_products
    dengan header baris pertama: Kode, Nama, Divisi, Group, Sat, Konversi (sesuai scripts/doi_cabang.py).
    """
    init_db()
    prod_rows = get_master_rows("product")
    if not prod_rows:
        raise ValueError("Master Produk / Daftar Barang masih kosong di database. Silakan upload file Daftar Barang terlebih dahulu.")

    df = pd.DataFrame([
        {
            "Kode": r["sku_code"],
            "Nama": r["sku_name"],
            "Divisi": r.get("divisi", ""),
            "Group": r.get("grup", ""),
            "Sat": r.get("satuan", "CTN"),
            "Konversi": float(r.get("konversi") or 1.0),
        }
        for r in prod_rows
    ])
    out_path = os.path.join(target_dir, "Daftar_Barang_MasterDB.xlsx")
    df.to_excel(out_path, index=False)
    return out_path


# --- AUTO-HARVESTING DARI FILE TRANSAKSI SAAT SCRIPT BERJALAN ---
def harvest_from_sales_df(df: pd.DataFrame, user_email: str = "auto_script"):
    """Ekstrak otomatis Customer, Produk, Gudang, dan Cabang baru dari DataFrame bersih Orlan/Zeta."""
    if df is None or df.empty:
        return
    init_db()
    now = dt.datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        # 1. Cabang
        if "Cabang" in df.columns and "Sumber" in df.columns:
            cabs = df[["Cabang", "Sumber"]].drop_duplicates()
            for _, r in cabs.iterrows():
                cb = _clean_cell(r["Cabang"])
                if cb:
                    conn.execute(
                        "INSERT OR IGNORE INTO master_branches VALUES (?, ?, ?, ?, ?)",
                        (cb.upper(), cb.title(), _clean_cell(r["Sumber"]), now, user_email),
                    )
        # 2. Customers
        if {"KodeCust", "Customer", "Cabang"}.issubset(df.columns):
            customer_cols = ["KodeCust", "Customer", "Cabang"]
            if "Alamat" in df.columns:
                customer_cols.append("Alamat")
            custs = df[customer_cols].drop_duplicates("KodeCust")
            cust_tuples = [
                (_clean_cell(r["KodeCust"]), _clean_cell(r["Customer"]), _clean_cell(r["Cabang"]).title(), _clean_cell(r.get("Alamat", "")), now, user_email)
                for _, r in custs.iterrows() if _clean_cell(r["KodeCust"])
            ]
            conn.executemany("INSERT OR IGNORE INTO master_customers VALUES (?, ?, ?, ?, ?, ?)", cust_tuples)

        # 3. Products (SKU)
        if {"KodeBarang", "NamaBarang"}.issubset(df.columns):
            prods = df.drop_duplicates("KodeBarang")
            prod_tuples = [
                (
                    _clean_cell(r["KodeBarang"]),
                    _clean_cell(r["NamaBarang"]),
                    _clean_cell(r.get("Unit", r.get("Unit_Asli", "CTN"))),
                    1.0,
                    _clean_cell(r.get("NamaGrup", "")),
                    _clean_cell(r.get("Principal", "")),
                    now,
                    user_email,
                )
                for _, r in prods.iterrows() if _clean_cell(r["KodeBarang"])
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO master_products (sku_code, sku_name, satuan, konversi, grup, divisi, updated_at, updated_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                prod_tuples,
            )


# --- DYNAMIC SCHEMA DETECTION & SELF-LEARNING ---
def inspect_and_map_columns(df: pd.DataFrame, entity_type: str):
    init_db()
    schema = MASTER_SCHEMAS[entity_type]
    file_cols = [str(c).strip() for c in df.columns if not str(c).startswith("Unnamed:")]
    norm_to_orig = {_norm(c): c for c in file_cols}

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT standard_field, alias_name FROM schema_aliases WHERE entity_type = ?",
            (entity_type,),
        ).fetchall()

    alias_map = {}
    for r in rows:
        alias_map.setdefault(r["standard_field"], set()).add(r["alias_name"])

    matched = {}
    missing_required = []

    for std_field, fmeta in schema["fields"].items():
        known_aliases = alias_map.get(std_field, set())
        found_orig = None
        for norm_col, orig_col in norm_to_orig.items():
            if norm_col in known_aliases:
                found_orig = orig_col
                break
        if found_orig:
            matched[std_field] = found_orig
        elif fmeta["required"]:
            missing_required.append({"field": std_field, "label": fmeta["label"]})

    return {
        "valid": len(missing_required) == 0,
        "matched": matched,
        "missing_required": missing_required,
        "available_columns": [str(c).strip() for c in df.columns],
        "all_fields": [
            {"field": k, "label": v["label"], "required": v["required"]}
            for k, v in schema["fields"].items()
        ],
    }


def learn_column_aliases(entity_type: str, user_mapping: dict):
    init_db()
    with get_conn() as conn:
        for std_field, excel_col in user_mapping.items():
            if excel_col and str(excel_col).strip():
                conn.execute(
                    "INSERT OR IGNORE INTO schema_aliases (entity_type, standard_field, alias_name) VALUES (?, ?, ?)",
                    (entity_type, std_field, _norm(excel_col)),
                )


def _build_pk_value(entity_type: str, rec: dict) -> str:
    schema = MASTER_SCHEMAS[entity_type]
    pk = schema["pk"]
    if pk == "row_key":
        parts = [str(rec.get(k, "")).strip() for k in schema["key_fields"]]
        if any(not p for p in parts):
            return ""
        if entity_type == "supplier_cabang":
            parts[0] = parts[0].upper()
        return "|".join(parts)
    return str(rec.get(pk, "")).strip()


def sync_master_dataframe(df: pd.DataFrame, entity_type: str, column_map: dict, user_email: str = "system"):
    init_db()
    schema = MASTER_SCHEMAS[entity_type]
    table = schema["table"]
    pk = schema["pk"]
    fields = list(schema["fields"].keys())
    now = dt.datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        before_count = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]

    records_to_insert = []
    for _, row in df.iterrows():
        rec = {}
        for f in fields:
            src_col = column_map.get(f)
            val = row[src_col] if (src_col and src_col in df.columns) else ""
            rec[f] = _clean_cell(val)

        if entity_type == "supplier_rekap" and not rec.get("label_principal"):
            rec["label_principal"] = make_principal_label(rec.get("supp", ""), rec.get("nama_grup", ""))

        pk_val = _build_pk_value(entity_type, rec)
        if not pk_val:
            continue
        rec[pk] = pk_val
        records_to_insert.append(rec)

    if not records_to_insert:
        return {"before": before_count, "added": 0, "total": before_count}

    all_cols = ([pk] if pk == "row_key" else []) + fields + ["updated_at", "updated_by"]
    cols_sql = ", ".join(all_cols)
    placeholders = ", ".join(["?"] * len(all_cols))

    with get_conn() as conn:
        for rec in records_to_insert:
            vals = ([rec[pk]] if pk == "row_key" else []) + [rec[f] for f in fields] + [now, user_email]
            conn.execute(
                f"INSERT OR IGNORE INTO {table} ({cols_sql}) VALUES ({placeholders})",
                vals,
            )
        after_count = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]

    return {
        "before": before_count,
        "added": after_count - before_count,
        "total": after_count,
    }


# --- MASTER DATA CRUD (GET, ADD, EDIT, DELETE) ---
def get_master_rows(entity_type: str):
    init_db()
    schema = MASTER_SCHEMAS[entity_type]
    order_col = ", ".join(schema["key_fields"])
    with get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM {schema['table']} ORDER BY {order_col}").fetchall()
        return [dict(r) for r in rows]


def upsert_master_row(entity_type: str, payload: dict, user_email: str, allow_overwrite: bool = False):
    init_db()
    schema = MASTER_SCHEMAS[entity_type]
    table = schema["table"]
    pk = schema["pk"]
    fields = list(schema["fields"].keys())
    now = dt.datetime.now().isoformat(timespec="seconds")

    clean_payload = {f: _clean_cell(payload.get(f, "")) for f in fields}
    if entity_type == "supplier_rekap" and not clean_payload.get("label_principal"):
        clean_payload["label_principal"] = make_principal_label(clean_payload.get("supp", ""), clean_payload.get("nama_grup", ""))

    pk_val = _clean_cell(payload.get(pk, "")) or _build_pk_value(entity_type, clean_payload)
    if not pk_val:
        raise ValueError("Kolom kunci wajib diisi.")

    with get_conn() as conn:
        exists = conn.execute(f"SELECT 1 FROM {table} WHERE {pk} = ?", (pk_val,)).fetchone()
        if exists and not allow_overwrite:
            raise PermissionError("Data sudah ada. Hanya Admin yang memiliki izin untuk mengubah (Edit) data Master.")

        all_cols = ([pk] if pk == "row_key" else []) + fields + ["updated_at", "updated_by"]
        cols_sql = ", ".join(all_cols)
        placeholders = ", ".join(["?"] * len(all_cols))
        vals = ([pk_val] if pk == "row_key" else []) + [clean_payload.get(f, "") for f in fields] + [now, user_email]
        conn.execute(
            f"INSERT OR REPLACE INTO {table} ({cols_sql}) VALUES ({placeholders})",
            vals,
        )


def delete_master_row(entity_type: str, pk_val: str):
    init_db()
    schema = MASTER_SCHEMAS[entity_type]
    with get_conn() as conn:
        conn.execute(f"DELETE FROM {schema['table']} WHERE {schema['pk']} = ?", (pk_val,))


def clear_master_table(entity_type: str):
    init_db()
    schema = MASTER_SCHEMAS[entity_type]
    with get_conn() as conn:
        conn.execute(f"DELETE FROM {schema['table']}")