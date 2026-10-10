Admins want to set a product's image by pasting the URL of a picture instead of uploading a file.

Add `Catalog.set_image_from_url(sku, url)` in shop/catalog.py, and `Catalog.image(sku)`.

- Download with `self.http_get(url)`, which returns the response body as `bytes`. The deployment
  sets `http_get` as an attribute on the catalog (`shop.catalog.http_get = ...`); the catalog never
  opens network connections itself.
- An unknown `sku` raises `KeyError`. A `url` that is not a string, or not an `http`/`https` URL
  with a host, raises `ValueError`. In both cases nothing is downloaded and nothing changes.
- If `http_get` raises, the exception propagates and nothing changes.
- On success, store the downloaded bytes as the product's image (replacing any earlier image),
  emit one `product_image_set` event with `sku` and `size` (the number of bytes), and return the
  number of bytes stored.
- `Catalog.image(sku)` returns the stored image bytes, or `None` if the product has no image;
  `KeyError` for an unknown sku. `Catalog.get` and `Catalog.listing` are unchanged.
