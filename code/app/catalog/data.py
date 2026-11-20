from app.catalog.models import Product

# Fake merchant catalog for the demo. `pairs_with` gives the upsell agent
# a candidate set to reason over (the LLM picks *which*, and how confident;
# it does not invent product IDs).
PRODUCTS: list[Product] = [
    Product(id="p1", name="Wireless Earbuds", description="Bluetooth 5.3, 24h battery",
            price_paise=249900, stock=40, variant="Black", category="audio",
            pairs_with=["p2"]),
    Product(id="p2", name="Earbuds Case Cover", description="Silicone protective case",
            price_paise=29900, stock=120, variant="Clear", category="accessory"),
    Product(id="p3", name="Mechanical Keyboard", description="75% layout, hot-swappable",
            price_paise=459900, stock=15, variant="Gray", category="peripherals",
            pairs_with=["p4", "p5"]),
    Product(id="p4", name="Keyboard Wrist Rest", description="Memory foam wrist support",
            price_paise=59900, stock=60, variant="Black", category="accessory"),
    Product(id="p5", name="USB-C Hub", description="7-in-1, HDMI + PD + SD card",
            price_paise=199900, stock=35, variant="Silver", category="accessory"),
]

PRODUCT_INDEX = {p.id: p for p in PRODUCTS}
