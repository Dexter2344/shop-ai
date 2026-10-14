import os
import io
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
from PIL import Image
import google.generativeai as genai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shop-ai")

# ---------- Init ----------
app = FastAPI(title="Shop-AI", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase credentials missing")

if not GEMINI_API_KEY:
    logger.warning("Gemini API key missing")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")


# ---------- Schemas ----------
class ProductCreate(BaseModel):
    name: str
    quantity: int = 0
    price: Optional[float] = None
    floor_price: Optional[float] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    floor_price: Optional[float] = None


class SaleCreate(BaseModel):
    product_id: int
    quantity: int
    price_sold: Optional[float] = None


# ---------- Health ----------
@app.get("/")
async def health():
    return {
        "status": "alive",
        "service": "Shop-AI",
        "version": "0.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------- Products ----------
@app.get("/api/products")
async def list_products():
    try:
        res = supabase.table("products").select("*").order("name").execute()
        return {"count": len(res.data), "products": res.data}
    except Exception as e:
        logger.error(f"List products error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/product")
async def create_product(product: ProductCreate):
    try:
        res = supabase.table("products").insert({
            "name": product.name,
            "quantity": product.quantity,
            "price": product.price,
            "floor_price": product.floor_price,
        }).execute()
        return {"product": res.data[0]}
    except Exception as e:
        logger.error(f"Create product error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/product/{product_id}")
async def update_product(product_id: int, update: ProductUpdate):
    try:
        data = {k: v for k, v in update.dict().items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = supabase.table("products").update(data).eq("id", product_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"product": res.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update product error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/product/{product_id}")
async def delete_product(product_id: int):
    try:
        res = supabase.table("products").delete().eq("id", product_id).execute()
        return {"deleted": True, "id": product_id}
    except Exception as e:
        logger.error(f"Delete product error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Sales ----------
@app.post("/api/sale")
async def record_sale(sale: SaleCreate):
    try:
        # Fetch product
        res = supabase.table("products").select("*").eq("id", sale.product_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Product not found")

        product = res.data[0]
        if product["quantity"] < sale.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock. Available: {product['quantity']}",
            )

        new_qty = product["quantity"] - sale.quantity

        # Record sale
        supabase.table("sales").insert({
            "product_id": sale.product_id,
            "quantity": sale.quantity,
            "price_sold": sale.price_sold,
        }).execute()

        # Update product quantity
        supabase.table("products").update({
            "quantity": new_qty,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", sale.product_id).execute()

        return {
            "success": True,
            "product": product["name"],
            "sold": sale.quantity,
            "remaining": new_qty,
            "low_stock": new_qty <= 5,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sale error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Alerts ----------
@app.get("/api/alerts")
async def low_stock_alerts():
    try:
        res = supabase.table("products").select("*").lte("quantity", 5).order("quantity").execute()
        return {"count": len(res.data), "alerts": res.data}
    except Exception as e:
        logger.error(f"Alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Photo Scan (Gemini Vision) ----------
@app.post("/api/scan")
async def scan_photo(file: UploadFile = File(...)):
    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Prompt for Gemini
        prompt = """You are an inventory counting assistant.

Look at this image of shop products. Identify each distinct product and count how many units are visible.

Return ONLY valid JSON in this exact format, no explanation, no markdown:
{
  "products": [
    {"name": "Product name", "quantity": 5, "confidence": "high"},
    {"name": "Another product", "quantity": 3, "confidence": "medium"}
  ]
}

Rules:
- Use simple, clear product names
- If you cannot determine quantity, put your best estimate
- confidence: "high" if clear, "medium" if uncertain, "low" if guessing
"""

        response = gemini_model.generate_content([prompt, image])
        text = response.text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Gemini returned invalid JSON: {text}")
            raise HTTPException(status_code=500, detail="AI returned invalid format. Try again.")

        return {
            "success": True,
            "products": parsed.get("products", []),
            "raw_response": text,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Stats ----------
@app.get("/api/stats")
async def stats():
    try:
        products = supabase.table("products").select("*").execute().data
        sales = supabase.table("sales").select("*").execute().data

        total_products = len(products)
        total_stock = sum(p["quantity"] for p in products)
        low_stock = len([p for p in products if p["quantity"] <= 5])
        total_sales = len(sales)
        revenue = sum(float(s["price_sold"] or 0) * s["quantity"] for s in sales)

        return {
            "total_products": total_products,
            "total_stock_units": total_stock,
            "low_stock_items": low_stock,
            "total_sales": total_sales,
            "revenue": round(revenue, 2),
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
