from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import urllib.parse

app = FastAPI()

active_gc = None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, error: str = None):
    err_html = f"<div style='color:red; background:#ffe6e6; padding:10px; border-radius:5px; margin-bottom:15px;'>{error}</div>" if error else ""
    
    if not active_gc:
        return f"""
        <html>
        <head><title>Saina Tailor Hub - Login</title></head>
        <body style="font-family:sans-serif; background:#f4f7f6; padding:40px; display:flex; justify-content:center;">
            <div style="background:white; padding:30px; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1); width:400px;">
                <h2 style="color:#333; margin-top:0;">🪡 Saina Tailor Hub</h2>
                {err_html}
                <p style="color:#666; font-size:14px;">Upload your Google Cloud <b>credentials.json</b> file once to connect securely:</p>
                <form action="/connect" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".json" required style="margin-bottom:15px; width:100%;">
                    <button type="submit" style="background:#25D366; color:white; border:none; padding:10px 15px; border-radius:4px; font-weight:bold; width:100%; cursor:pointer;">Connect Sheets</button>
                </form>
            </div>
        </body>
        </html>
        """
    
    try:
        sh_bulk = active_gc.open("Saina_Bulk_Campaigns").sheet1
        records = sh_bulk.get_all_records()
    except Exception as e:
        return f"<h3>Error loading sheet data: {e}</h3><br><a href='/logout'>Reset Connection</a>"

    rows_html = ""
    for idx, row in enumerate(records):
        row_num = idx + 2
        name = row.get("Customer_Name", "Customer")
        phone = str(row.get("Phone_Number", ""))
        status = row.get("Status", "Pending")
        
        clean_phone = phone.strip().replace("+", "").replace(" ", "").replace("-", "")
        msg = f"🪡 *[ SAINA LADIES TAILOR ]* 🪡\n\nHi {name}! We have exciting new festive designs in store. Drop by or message us early!"
        wa_link = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
        
        status_badge = "🟢 Sent" if status == "Sent" else "🟡 Pending"
        
        rows_html += f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding:10px;"><b>{name}</b></td>
            <td style="padding:10px;">{phone}</td>
            <td style="padding:10px;">{status_badge}</td>
            <td style="padding:10px;">
                <a href="{wa_link}" target="_blank" style="background:#25D366; color:white; padding:6px 12px; text-decoration:none; border-radius:4px; font-size:12px; font-weight:bold; margin-right:5px;">💬 Open WA</a>
                <form action="/mark-sent" method="post" style="display:inline;">
                    <input type="hidden" name="row_num" value="{row_num}">
                    <button type="submit" style="background:#007bff; color:white; border:none; padding:6px 10px; border-radius:4px; font-size:12px; cursor:pointer;">Mark Sent</button>
                </form>
            </td>
        </tr>
        """

    return f"""
    <html>
    <head><title>Saina Bulk Campaign Hub</title></head>
    <body style="font-family:sans-serif; background:#f4f7f6; padding:30px;">
        <div style="max-width:800px; margin:0 auto; background:white; padding:30px; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="margin:0; color:#333;">📢 Saina Bulk Campaign Hub</h2>
                <a href="/logout" style="color:#d9534f; text-decoration:none; font-size:14px; font-weight:bold;">Disconnect</a>
            </div>
            {err_html}
            <table style="width:100%; border-collapse:collapse; text-align:left;">
                <thead>
                    <tr style="background:#f8f9fa; border-bottom:2px solid #ddd;">
                        <th style="padding:10px;">Name</th>
                        <th style="padding:10px;">Phone</th>
                        <th style="padding:10px;">Status</th>
                        <th style="padding:10px;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else "<tr><td colspan='4' style='padding:20px; text-align:center;'>No customers found in Saina_Bulk_Campaigns sheet.</td></tr>"}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

@app.post("/connect")
async def connect_sheets(file: UploadFile = File(...)):
    global active_gc
    try:
        content = await file.read()
        creds_data = json.loads(content)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        active_gc = gspread.authorize(creds)
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?error=Connection failed: {str(e)}", status_code=303)

@app.post("/mark-sent")
async def mark_sent(row_num: int = Form(...)):
    global active_gc
    if active_gc:
        try:
            sh_bulk = active_gc.open("Saina_Bulk_Campaigns").sheet1
            headers = sh_bulk.row_values(1)
            status_col_idx = headers.index("Status") + 1
            sh_bulk.update_cell(row_num, status_col_idx, "Sent")
        except Exception:
            pass
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout():
    global active_gc
    active_gc = None
    return RedirectResponse(url="/", status_code=303)
