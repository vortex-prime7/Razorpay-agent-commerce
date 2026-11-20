from pydantic import BaseModel, Field


class Product(BaseModel):
    """
    A single catalog item, structured so an AI shopping agent (or an MCP
    tool call) can parse it without scraping HTML. Prices are integers in
    paise — never floats — because money math must be exact.
    """
    id: str
    name: str
    description: str
    price_paise: int = Field(..., description="Price in paise (INR smallest unit). 49900 = ₹499.00")
    stock: int
    variant: str | None = None
    category: str
    # Products that pair well with this one — used by the upsell agent.
    pairs_with: list[str] = Field(default_factory=list)

    def to_json_ld(self) -> dict:
        """
        schema.org/Product representation. This is the 'agent-readable'
        contract: any autonomous buyer that understands schema.org can
        consume the catalog with zero custom parsing.
        """
        return {
            "@context": "https://schema.org",
            "@type": "Product",
            "productID": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "offers": {
                "@type": "Offer",
                "priceCurrency": "INR",
                "price": f"{self.price_paise / 100:.2f}",
                "availability": (
                    "https://schema.org/InStock" if self.stock > 0
                    else "https://schema.org/OutOfStock"
                ),
                "inventoryLevel": self.stock,
            },
        }
